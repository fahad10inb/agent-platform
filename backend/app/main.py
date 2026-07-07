"""
The web server entry point.

This creates the FastAPI application and defines its "routes" — the addresses
the outside world can call. For Part 1 there is just one route: a health check
so we can confirm the server is alive.
"""

import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app import db, distill_service, security
from app.businesses import SEED_BUSINESSES
from app.config import get_settings
from app.llm_service import generate_reply
from app.prompt_service import build_system_prompt
import secrets

from app.dashboard_html import DASHBOARD_HTML
from app.landing_html import LANDING_HTML
from app.tools.calendar_tools import make_calendar_tools
from app.tools.leads_tools import make_lead_tools
from app.tools.memory_tools import make_memory_tools
from app.widget_html import WIDGET_HTML

# Load our settings once at startup.
settings = get_settings()

# Create the database tables if they don't exist yet (safe to run every start).
db.init_db()

# Seed the demo businesses ONLY if they don't exist yet. (An unconditional upsert
# here silently reverted every dashboard edit to the demo tenants on each deploy.)
for _b in SEED_BUSINESSES:
    if db.get_business(_b["id"]) is None:
        db.upsert_business(_b)

logger = logging.getLogger("agent-platform")

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
)


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


# Tools are now built PER REQUEST (scoped to the caller's business) inside the
# /chat handler, so each business only ever touches its own data.
# Conversation history lives in the messages TABLE (was a RAM dict — every
# deploy wiped every tenant's live conversations, and it capped us at one server).


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, background_tasks: BackgroundTasks):
    """Take the caller's message, ask the AI (with memory + tools), return its reply.

    POST (not GET) because the caller sends a body of data. `async` because we
    `await` the (slow) AI call inside. Public (patients use it) but rate-limited
    so it can't be spammed into a huge Gemini bill.
    """
    # 0. Abuse / cost guard: cap requests per IP.
    security.rate_limit(request)

    # 1. Look up WHICH business this request is for, and build its persona.
    business = db.get_business(req.business_id)
    if business is None:
        raise HTTPException(status_code=404, detail=f"Unknown business_id: {req.business_id}")
    system_prompt = build_system_prompt(business)

    # 2. Load this conversation's DURABLE history (scoped by business_id — the
    # same conversation_id at two businesses can never share context) and add
    # the new message in memory only. Capped at 40 turns at read time.
    history = db.get_history(req.business_id, req.conversation_id, limit=40)
    history = history + [{"role": "user", "text": req.message}]

    # 3. Build this business's tools (each scoped to its own data via the
    #    business_id closure), then send the whole conversation to the AI.
    tools = (
        make_calendar_tools(business)
        + make_memory_tools(req.business_id)
        + make_lead_tools(req.business_id)
    )
    try:
        reply = await generate_reply(system_prompt, history, tools=tools)
    except Exception as e:
        # Nothing was persisted yet, so a failed turn can't haunt the next
        # request — rollback by construction.
        # Log the real cause; tell the public only in development. Leaking
        # internals (key names, stack details) to an open endpoint is a gift
        # to attackers in production.
        logger.exception("chat failed for business=%s", req.business_id)
        if settings.environment == "development":
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
        raise HTTPException(
            status_code=500, detail="Sorry — something went wrong. Please try again."
        ) from e

    # Guard: the model occasionally acts (calls tools) but returns EMPTY text —
    # the customer would see a blank bubble while things happened invisibly.
    if not reply.strip():
        reply = (
            "Sorry — I lost my words for a second there. Could you say that "
            "again? I'll double-check everything before confirming."
        )

    # 4. Persist BOTH turns only now that the reply succeeded, and meter the
    # turn against the business's daily usage (the future billing/quota data).
    db.save_message(req.business_id, req.conversation_id, "user", req.message)
    db.save_message(req.business_id, req.conversation_id, "model", reply)
    db.bump_usage(req.business_id)

    # 5. Every 6th caller message, distill the conversation into durable caller
    # memory — AFTER the response is sent (BackgroundTasks), so the caller never
    # waits on it. `history` already includes this turn's message, so counting
    # it counts the conversation as it now stands. The service is flag-gated
    # (DISTILL_ENABLED) and swallows its own errors — it can't break /chat.
    every_n = distill_service.DISTILL_EVERY_N_USER_MESSAGES
    user_turns = sum(1 for t in history if t["role"] == "user")
    if user_turns >= every_n and user_turns % every_n == 0:
        background_tasks.add_task(
            distill_service.distill_conversation, req.business_id, req.conversation_id
        )
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
    model), and it's rate-limited against scraping."""
    security.rate_limit(request, limit=30, window=60, bucket="history")
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
              "min_notice_hours", "max_advance_days", "buffer_min"]
    return {k: biz.get(k) for k in fields}


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
