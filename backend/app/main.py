"""
The web server entry point.

This creates the FastAPI application and defines its "routes" — the addresses
the outside world can call. For Part 1 there is just one route: a health check
so we can confirm the server is alive.
"""

import asyncio
import contextlib
import datetime
import logging
import zoneinfo

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app import chat_core, db, digest_service, import_service, security
from app.businesses import SEED_BUSINESSES
from app.config import get_settings
import secrets

from app.dashboard_html import DASHBOARD_HTML
from app.landing_html import LANDING_HTML
from app.whatsapp import router as whatsapp_router
from app.widget_html import WIDGET_HTML

# Load our settings once at startup.
settings = get_settings()

# Without this, the root logger sits at WARNING with a last-resort handler, so
# every logger.info() breadcrumb (notify sent, digest counts, distilled, empty-
# reply recovery) is silently DROPPED in production — Render logs show only
# warnings and tracebacks. One line turns the whole info-level story back on.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# Create the database tables if they don't exist yet (safe to run every start).
db.init_db()

# Seed the demo businesses ONLY if they don't exist yet. (An unconditional upsert
# here silently reverted every dashboard edit to the demo tenants on each deploy.)
for _b in SEED_BUSINESSES:
    if db.get_business(_b["id"]) is None:
        db.upsert_business(_b)

logger = logging.getLogger("agent-platform")

_DUBAI_TZ = zoneinfo.ZoneInfo("Asia/Dubai")


async def _digest_scheduler() -> None:
    """Hourly check for 'is it Monday morning in Dubai?' — the whole scheduler.

    An hourly wake-up + the 6-day last_digest_at rule inside send_weekly_digests
    is what makes this safe with zero infrastructure: no cron, no queue, and a
    restart mid-window can't double-send. Sleep FIRST so a boot during the
    window doesn't fire before the app has finished settling.
    """
    while True:
        await asyncio.sleep(3600)
        now = datetime.datetime.now(_DUBAI_TZ)
        if now.weekday() == 0 and 8 <= now.hour < 12:  # Monday, 8am–12pm Dubai
            try:
                await asyncio.to_thread(digest_service.send_weekly_digests)
            except Exception:  # noqa: BLE001 — the loop must outlive any one bad pass
                logger.exception("weekly digest pass failed")


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Start the digest scheduler with the server, stop it with the server.
    DIGEST_ENABLED=false switches the whole feature off from the environment."""
    task = asyncio.create_task(_digest_scheduler()) if settings.digest_enabled else None
    yield
    if task:
        task.cancel()


# `app` is THE application object. When we run `uvicorn app.main:app`, that
# command literally means: "find the variable `app` inside app/main.py and run
# it." FastAPI also uses `title` to label the auto-generated docs page.
# In production the interactive /docs page is off — the full API schema
# (including admin routes) is a map we don't hand to strangers.
_dev = settings.environment == "development"
app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if _dev else None,
    redoc_url="/redoc" if _dev else None,
    openapi_url="/openapi.json" if _dev else None,
    lifespan=_lifespan,
)

# The WhatsApp channel (webhook verify + inbound messages). Plays dead (404)
# until the WHATSAPP_* env vars are configured.
app.include_router(whatsapp_router)


@app.middleware("http")
async def _hardening(request: Request, call_next):
    """Last-resort error net + baseline security headers on every response.

    Any exception that escapes a route (a DB hiccup, a bug) becomes a clean,
    generic 500 with the real traceback in the LOGS — never a raw stack trace
    in the caller's browser."""
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001 — the whole point is catching everything
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        response = JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    # Always-HTTPS (Render terminates TLS); browsers remember for a year.
    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    # The dashboard (where keys are typed) must never be framed — clickjacking
    # protection. The widget MUST stay frameable (clinics embed it via iframe).
    if request.url.path == "/dashboard":
        response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
    return response


@app.get("/", response_class=HTMLResponse)
def landing():
    """The public landing page — the product's front door (was a bare 404)."""
    return LANDING_HTML


@app.get("/health")
def health():
    """A simple 'is the server alive?' check.

    The decorator `@app.get("/health")` wires this function to handle GET
    requests at the URL /health. Whatever we `return` is automatically turned
    into a JSON response for the caller.
    """
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.environment,
    }


# --- Chat ---------------------------------------------------------------------
# The shape of the data /chat EXPECTS to receive. FastAPI reads the request's
# JSON body, checks it matches this model, and hands us a tidy `req` object.
# If a caller sends the wrong shape, FastAPI auto-replies with a clear error.
class ChatRequest(BaseModel):
    # Bounded so one request can't carry megabytes into Gemini (cost guard).
    message: str = Field(min_length=1, max_length=4000)
    # Ties messages into ONE ongoing conversation so the agent remembers context.
    # Send the same id across a back-and-forth; defaults to "default" for easy testing.
    conversation_id: str = Field(default="default", max_length=100)
    # Which business this request is for. Defaults to the dental demo so testing
    # is easy; in real use every caller's request carries their business's id.
    business_id: str = Field(default="bright-smile", max_length=60)


# The shape of what /chat SENDS BACK. Declaring it documents the API and keeps
# our responses consistent.
class ChatResponse(BaseModel):
    reply: str


class BusinessSettings(BaseModel):
    """Editable business fields (all optional — only the ones sent get updated)."""

    name: str | None = Field(default=None, max_length=120)
    type: str | None = Field(default=None, max_length=60)
    hours: str | None = Field(default=None, max_length=500)
    services: str | None = Field(default=None, max_length=2000)
    tone: str | None = Field(default=None, max_length=200)
    faq: str | None = Field(default=None, max_length=8000)
    # Bounded hours/slot so a bad value can't hang slot generation (an infinite
    # loop when slot_minutes <= 0) or produce a nonsense calendar.
    open_hour: int | None = Field(default=None, ge=0, le=23)
    close_hour: int | None = Field(default=None, ge=1, le=24)
    slot_minutes: int | None = Field(default=None, ge=5, le=240)
    vertical: str | None = Field(default=None, max_length=40)
    staff: str | None = Field(default=None, max_length=1000)
    location: str | None = Field(default=None, max_length=500)
    policies: str | None = Field(default=None, max_length=2000)
    # Booking hygiene: notice window, how far ahead the calendar opens, and
    # breathing room between appointments.
    min_notice_hours: int | None = Field(default=None, ge=0, le=72)
    max_advance_days: int | None = Field(default=None, ge=1, le=365)
    buffer_min: int | None = Field(default=None, ge=0, le=120)
    # Owner alert inbox — empty string switches notifications off.
    notify_email: str | None = Field(default=None, max_length=200)
    # Escalation + after-hours: a number to hand a caller who needs a human
    # (empty = take a message), and what to do outside opening hours.
    transfer_number: str | None = Field(default=None, max_length=40)
    after_hours_mode: str | None = Field(
        default=None, pattern=r"^(take_message|book_only|info_only)$"
    )
    # WhatsApp Cloud API phone_number_id owning this tenant's webhooks
    # (empty string disconnects the channel for this business).
    whatsapp_phone_id: str | None = Field(default=None, max_length=40)


class NewBusiness(BaseModel):
    """Payload to onboard a new business (admin only)."""

    # URL-safe slug (it lands in widget links and JS) — lowercase, digits, dashes.
    id: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=60)
    hours: str = Field(default="", max_length=500)
    services: str = Field(default="", max_length=2000)
    tone: str = Field(default="warm and professional", max_length=200)
    faq: str = Field(default="", max_length=8000)
    open_hour: int = Field(default=9, ge=0, le=23)
    close_hour: int = Field(default=17, ge=1, le=24)
    slot_minutes: int = Field(default=30, ge=5, le=240)
    vertical: str = Field(default="general", max_length=40)
    # Personalization trio: the team ("Marwan — fades"), where/how to find you,
    # and the house rules — first-class fields, not buried in the FAQ blob.
    staff: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=500)
    policies: str = Field(default="", max_length=2000)
    min_notice_hours: int = Field(default=1, ge=0, le=72)
    max_advance_days: int = Field(default=60, ge=1, le=365)
    buffer_min: int = Field(default=0, ge=0, le=120)
    transfer_number: str = Field(default="", max_length=40)
    after_hours_mode: str = Field(
        default="take_message", pattern=r"^(take_message|book_only|info_only)$"
    )
    # Was silently dropped before (form sent it, model ignored it) — the owner
    # had to re-enter their alert email in Settings after onboarding.
    notify_email: str = Field(default="", max_length=200)


# The turn itself lives in app/chat_core.py, shared with the WhatsApp webhook.
# This route adds what's web-specific: the per-IP rate limit and HTTP error
# shapes. Conversation history lives in the messages TABLE.


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """Take the caller's message, ask the AI (with memory + tools), return its reply.

    POST (not GET) because the caller sends a body of data. `async` because we
    `await` the (slow) AI call inside. Public (patients use it) but rate-limited
    so it can't be spammed into a huge Gemini bill.
    """
    # Abuse / cost guard: cap requests per IP.
    security.rate_limit(request)

    try:
        reply = await chat_core.run_turn(
            req.business_id, req.conversation_id, req.message, background_tasks.add_task
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        # Nothing was persisted (the core persists only after success), so a
        # failed turn can't haunt the next request — rollback by construction.
        # Log the real cause; tell the public only in development. Leaking
        # internals (key names, stack details) to an open endpoint is a gift
        # to attackers in production.
        logger.exception("chat failed for business=%s", req.business_id)
        if settings.environment == "development":
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
        raise HTTPException(
            status_code=500, detail="Sorry — something went wrong. Please try again."
        ) from e
    return ChatResponse(reply=reply)


@app.get("/chat/history")
def chat_history(
    request: Request,
    business_id: str = Query(max_length=60),
    conversation_id: str = Query(min_length=8, max_length=100),
):
    """The last turns of ONE conversation, for the widget to restore after a
    page reload. Public like /chat itself: the conversation_id is a random
    unguessable token minted by the widget (the industry-standard chat-widget
    model), and it's rate-limited against scraping.

    The security rests ENTIRELY on the token being unguessable. The widget mints
    `web-<random uuid>`. The WhatsApp channel does NOT: it uses `wa-<the caller's
    phone number>`, which is trivially guessable — so those transcripts must
    never be readable through this public route (anyone with a phone number +
    the public business_id could otherwise pull a customer's whole chat)."""
    security.rate_limit(request, limit=30, window=60, bucket="history")
    if conversation_id.startswith("wa-"):
        raise HTTPException(status_code=404, detail="No such conversation.")
    return db.get_history(business_id, conversation_id, limit=40)


@app.get("/widget", response_class=HTMLResponse)
def widget():
    """The patient-facing chat page. A clinic links to /widget?business_id=<id>;
    the page reads that id and talks to /chat. Served by the backend itself, so
    there's no separate frontend to deploy."""
    return WIDGET_HTML


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """The management dashboard page (clinic + admin). It's just the app shell;
    every data call from it requires an API key entered at login."""
    return DASHBOARD_HTML


@app.get("/manage/{business_id}")
def manage_get(business_id: str, request: Request, x_api_key: str | None = Header(default=None)):
    """Return a business's EDITABLE config (no secrets). Requires that business's
    key or the admin key — used to pre-fill the settings form."""
    # Sign-in attempts hit this first — throttle so keys can't be brute-forced.
    security.rate_limit(request, limit=20, window=60, bucket="manage")
    security.check_business_access(business_id, x_api_key)
    biz = db.get_business(business_id)
    if biz is None:
        raise HTTPException(status_code=404, detail="Unknown business.")
    fields = ["id", "name", "type", "hours", "services", "tone", "faq",
              "open_hour", "close_hour", "slot_minutes", "vertical",
              "staff", "location", "policies",
              "min_notice_hours", "max_advance_days", "buffer_min", "notify_email",
              "transfer_number", "after_hours_mode", "whatsapp_phone_id"]
    out = {k: biz.get(k) for k in fields}
    # The structured service menu rides along so the dashboard can prefill its
    # "name | minutes | price" textarea from what's actually stored.
    out["services_rows"] = db.list_services(business_id)
    # Same for the property listings sheet (real-estate tenants).
    out["listings_rows"] = db.list_listings(business_id)
    return out


@app.post("/manage/{business_id}")
def manage_update(
    business_id: str,
    settings_in: BusinessSettings,
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    """Update a business's settings. Requires that business's key or admin key."""
    security.rate_limit(request, limit=20, window=60, bucket="manage")
    security.check_business_access(business_id, x_api_key)
    fields = {k: v for k, v in settings_in.model_dump().items() if v is not None}
    db.update_business_settings(business_id, fields)
    return {"status": "saved", "business_id": business_id}


class ServiceRow(BaseModel):
    """One structured service: the name is what callers say, the duration is
    what the calendar math reserves, the price is what the agent may quote.
    Price stays TEXT — owners write "80 AED", "from 150", "free consult"."""

    name: str = Field(min_length=1, max_length=120)
    duration_min: int = Field(ge=5, le=480)
    price: str = Field(default="", max_length=60)
    category: str = Field(default="", max_length=60)
    bookable: bool = True


class ServicesPayload(BaseModel):
    """The whole menu at once — replace semantics keep the dashboard's textarea
    and the DB trivially in sync (no per-row diffing)."""

    services: list[ServiceRow] = Field(max_length=50)


@app.post("/manage/{business_id}/services")
def manage_services(
    business_id: str,
    payload: ServicesPayload,
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    """Replace a business's structured service menu (per-service duration +
    price). Same auth as the rest of /manage: that business's key or admin."""
    security.rate_limit(request, limit=20, window=60, bucket="manage")
    security.check_business_access(business_id, x_api_key)
    if db.get_business(business_id) is None:
        # Only reachable with the admin key (a business key already 403s on an
        # unknown id) — refuse rows for a business that doesn't exist.
        raise HTTPException(status_code=404, detail="Unknown business.")
    db.replace_services(business_id, [s.model_dump() for s in payload.services])
    return {"status": "saved", "business_id": business_id, "count": len(payload.services)}


class ListingRow(BaseModel):
    """One live property. Everything except the title is optional and TEXT —
    owners write prices like "1.2M" or "60k/yr" and bedrooms like "studio"."""

    title: str = Field(min_length=1, max_length=120)
    area: str = Field(default="", max_length=80)
    bedrooms: str = Field(default="", max_length=20)
    price: str = Field(default="", max_length=40)
    purpose: str = Field(default="", max_length=20)  # sale / rent / their words
    notes: str = Field(default="", max_length=200)


class ListingsPayload(BaseModel):
    """The whole sheet at once — replace semantics, like the service menu."""

    listings: list[ListingRow] = Field(max_length=100)


@app.post("/manage/{business_id}/listings")
def manage_listings(
    business_id: str,
    payload: ListingsPayload,
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    """Replace a business's property-listings sheet (real estate). Same auth as
    the rest of /manage: that business's key or admin."""
    security.rate_limit(request, limit=20, window=60, bucket="manage")
    security.check_business_access(business_id, x_api_key)
    if db.get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Unknown business.")
    db.replace_listings(business_id, [r.model_dump() for r in payload.listings])
    return {"status": "saved", "business_id": business_id, "count": len(payload.listings)}


@app.post("/admin/businesses")
def admin_create_business(payload: NewBusiness, x_api_key: str | None = Header(default=None)):
    """Onboard a new business (ADMIN ONLY) — generates and returns its api_key."""
    security.check_admin(x_api_key)
    if db.get_business(payload.id) is not None:
        raise HTTPException(status_code=409, detail="A business with that id already exists.")
    api_key = "bizkey_" + secrets.token_urlsafe(24)
    data = payload.model_dump()
    data["api_key"] = api_key
    db.upsert_business(data)
    return {"status": "created", "id": payload.id, "api_key": api_key}


@app.post("/admin/businesses/{business_id}/rotate-key")
def admin_rotate_key(business_id: str, x_api_key: str | None = Header(default=None)):
    """Revoke a business's current api_key and issue a new one (ADMIN ONLY).

    The only way to change an api_key — settings deliberately can't touch it.
    This is the recovery path when a key leaks (e.g. the committed demo keys):
    rotate here, the old key stops working instantly, hand the new one to the
    owner. Shown once, like onboarding."""
    security.check_admin(x_api_key)
    new_key = "bizkey_" + secrets.token_urlsafe(24)
    if not db.rotate_api_key(business_id, new_key):
        raise HTTPException(status_code=404, detail="Unknown business.")
    logger.info("rotated api_key for business=%s", business_id)
    return {"status": "rotated", "id": business_id, "api_key": new_key}


@app.post("/admin/send-digests")
def admin_send_digests(x_api_key: str | None = Header(default=None)):
    """Run the weekly-digest pass RIGHT NOW (ADMIN ONLY) — the manual lever for
    testing delivery and for catch-up runs; the 6-day rule still applies, so
    hammering this can't spam any owner."""
    security.check_admin(x_api_key)
    return {"sent": digest_service.send_weekly_digests()}


class ImportRequest(BaseModel):
    """A website URL and/or a plain-text description to bootstrap onboarding
    from (description covers businesses that have no website at all)."""

    url: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=4000)


@app.post("/onboarding/import")
async def onboarding_import(payload: ImportRequest, request: Request, x_api_key: str | None = Header(default=None)):
    """'Give us your website' — fetch + extract a review-ready onboarding
    prefill (ADMIN ONLY: it spends LLM tokens and fetches arbitrary URLs)."""
    security.check_admin(x_api_key)
    security.rate_limit(request, limit=10, window=60, bucket="import")
    if not payload.url.strip() and not payload.description.strip():
        raise HTTPException(status_code=422, detail="Give me a website URL or a short description of the business.")
    try:
        return await import_service.import_from_website(url=payload.url, description=payload.description)
    except Exception as exc:  # noqa: BLE001 — any failure = one friendly message
        logger.warning("onboarding import failed for %r: %s", payload.url, str(exc)[:150])
        raise HTTPException(
            status_code=422,
            detail="Couldn't read that website — double-check the URL, or fill the form manually.",
        ) from exc


@app.get("/business/{business_id}")
def business_public(business_id: str):
    """PUBLIC display info for one business (name + type only — no secrets).
    The patient widget uses this to show the clinic's name in the header."""
    biz = db.get_business(business_id)
    if biz is None:
        raise HTTPException(status_code=404, detail="Unknown business.")
    return {"id": biz["id"], "name": biz["name"], "type": biz["type"]}


@app.get("/businesses")
def businesses(x_api_key: str | None = Header(default=None)):
    """List all client businesses — ADMIN ONLY (your client list is sensitive)."""
    security.check_admin(x_api_key)
    return db.list_businesses()


@app.get("/bookings")
def bookings(
    business_id: str = "bright-smile",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    x_api_key: str | None = Header(default=None),
):
    """List ONE business's bookings (pass ?business_id=...), newest first,
    paginated (?limit=&offset=).

    PROTECTED: requires that business's api_key (or the admin key) in the
    X-API-Key header. This is patient data — never open.
    """
    security.check_business_access(business_id, x_api_key)
    return db.list_bookings(business_id, limit=limit, offset=offset)


@app.get("/leads")
def leads(
    business_id: str = "bright-smile",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    x_api_key: str | None = Header(default=None),
):
    """List ONE business's captured leads/enquiries, paginated. PROTECTED."""
    security.check_business_access(business_id, x_api_key)
    return db.list_leads(business_id, limit=limit, offset=offset)


@app.get("/metrics")
def metrics(business_id: str = "bright-smile", x_api_key: str | None = Header(default=None)):
    """The owner's dashboard numbers (today + 30 days) incl. an ESTIMATED
    staff-hours-saved figure: each handled conversation ≈ 4 minutes a human
    would have spent on the phone or front desk. Clearly labeled an estimate."""
    security.check_business_access(business_id, x_api_key)
    m = db.get_metrics(business_id)
    m["hours_saved_30d_estimate"] = round(m["conversations_30d"] * 4 / 60, 1)
    return m


@app.get("/usage")
def usage(
    business_id: str = "bright-smile",
    days: int = Query(default=30, ge=1, le=365),
    x_api_key: str | None = Header(default=None),
):
    """Per-day handled-message counts — the billing/quota meter. PROTECTED."""
    security.check_business_access(business_id, x_api_key)
    return db.get_usage(business_id, days=days)
