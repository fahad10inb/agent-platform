"""
The web server entry point.

This creates the FastAPI application and defines its "routes" — the addresses
the outside world can call. For Part 1 there is just one route: a health check
so we can confirm the server is alive.
"""

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import db, security
from app.businesses import SEED_BUSINESSES
from app.config import get_settings
from app.llm_service import generate_reply
from app.prompt_service import build_system_prompt
import secrets

from app.dashboard_html import DASHBOARD_HTML
from app.tools.calendar_tools import make_calendar_tools
from app.tools.leads_tools import make_lead_tools
from app.tools.memory_tools import make_memory_tools
from app.widget_html import WIDGET_HTML

# Load our settings once at startup.
settings = get_settings()

# Create the database tables if they don't exist yet (safe to run every start).
db.init_db()

# Seed the demo businesses so there's data to test with. upsert = safe to re-run.
for _b in SEED_BUSINESSES:
    db.upsert_business(_b)

# `app` is THE application object. When we run `uvicorn app.main:app`, that
# command literally means: "find the variable `app` inside app/main.py and run
# it." FastAPI also uses `title` to label the auto-generated docs page.
app = FastAPI(title=settings.app_name)


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
    message: str
    # Ties messages into ONE ongoing conversation so the agent remembers context.
    # Send the same id across a back-and-forth; defaults to "default" for easy testing.
    conversation_id: str = "default"
    # Which business this request is for. Defaults to the dental demo so testing
    # is easy; in real use every caller's request carries their business's id.
    business_id: str = "bright-smile"


# The shape of what /chat SENDS BACK. Declaring it documents the API and keeps
# our responses consistent.
class ChatResponse(BaseModel):
    reply: str


class BusinessSettings(BaseModel):
    """Editable business fields (all optional — only the ones sent get updated)."""

    name: str | None = None
    type: str | None = None
    hours: str | None = None
    services: str | None = None
    tone: str | None = None
    faq: str | None = None
    open_hour: int | None = None
    close_hour: int | None = None
    slot_minutes: int | None = None
    vertical: str | None = None


class NewBusiness(BaseModel):
    """Payload to onboard a new business (admin only)."""

    id: str
    name: str
    type: str
    hours: str = ""
    services: str = ""
    tone: str = "warm and professional"
    faq: str = ""
    open_hour: int = 9
    close_hour: int = 17
    slot_minutes: int = 30
    vertical: str = "general"


# Tools are now built PER REQUEST (scoped to the caller's business) inside the
# /chat handler, so each business only ever touches its own data.

# Super-simple conversation memory: conversation_id -> list of {role, text} turns.
# It lives in RAM, so it resets when the server restarts. That's fine for now;
# in a later lesson this becomes a real database table that survives restarts.
_conversations: dict[str, list[dict]] = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
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

    # 2. Find (or start) this conversation's history, then add the new message.
    history = _conversations.setdefault(req.conversation_id, [])
    history.append({"role": "user", "text": req.message})

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
        # Surface the real cause in the response instead of a blank 500 — very
        # handy while learning. (In production you'd log it and return a generic
        # message so you don't leak internals.) `from e` keeps the original
        # error chained for cleaner tracebacks.
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e

    # 4. Remember the AI's reply too, so the next turn has the full context.
    history.append({"role": "model", "text": reply})
    return ChatResponse(reply=reply)


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
def manage_get(business_id: str, x_api_key: str | None = Header(default=None)):
    """Return a business's EDITABLE config (no secrets). Requires that business's
    key or the admin key — used to pre-fill the settings form."""
    security.check_business_access(business_id, x_api_key)
    biz = db.get_business(business_id)
    if biz is None:
        raise HTTPException(status_code=404, detail="Unknown business.")
    fields = ["id", "name", "type", "hours", "services", "tone", "faq",
              "open_hour", "close_hour", "slot_minutes", "vertical"]
    return {k: biz.get(k) for k in fields}


@app.post("/manage/{business_id}")
def manage_update(business_id: str, settings_in: BusinessSettings, x_api_key: str | None = Header(default=None)):
    """Update a business's settings. Requires that business's key or admin key."""
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
def bookings(business_id: str = "bright-smile", x_api_key: str | None = Header(default=None)):
    """List ONE business's bookings (pass ?business_id=...), newest first.

    PROTECTED: requires that business's api_key (or the admin key) in the
    X-API-Key header. This is patient data — never open.
    """
    security.check_business_access(business_id, x_api_key)
    return db.list_bookings(business_id)


@app.get("/leads")
def leads(business_id: str = "bright-smile", x_api_key: str | None = Header(default=None)):
    """List ONE business's captured leads/enquiries. PROTECTED (business or admin key)."""
    security.check_business_access(business_id, x_api_key)
    return db.list_leads(business_id)
