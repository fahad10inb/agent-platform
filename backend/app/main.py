"""
The web server entry point.

This creates the FastAPI application and defines its "routes" — the addresses
the outside world can call. For Part 1 there is just one route: a health check
so we can confirm the server is alive.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import db
from app.businesses import SEED_BUSINESSES
from app.config import get_settings
from app.llm_service import generate_reply
from app.prompt_service import build_system_prompt
from app.tools.calendar_tools import make_calendar_tools
from app.tools.memory_tools import make_memory_tools

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


# Tools are now built PER REQUEST (scoped to the caller's business) inside the
# /chat handler, so each business only ever touches its own data.

# Super-simple conversation memory: conversation_id -> list of {role, text} turns.
# It lives in RAM, so it resets when the server restarts. That's fine for now;
# in a later lesson this becomes a real database table that survives restarts.
_conversations: dict[str, list[dict]] = {}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Take the caller's message, ask the AI (with memory + tools), return its reply.

    POST (not GET) because the caller sends a body of data. `async` because we
    `await` the (slow) AI call inside.
    """
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
    tools = make_calendar_tools(business) + make_memory_tools(req.business_id)
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


@app.get("/businesses")
def businesses():
    """List the businesses this platform serves (proof multi-tenancy is live)."""
    return db.list_businesses()


@app.get("/bookings")
def bookings(business_id: str = "bright-smile"):
    """List ONE business's bookings (pass ?business_id=...), newest first.

    Scoped by business_id — it never returns another business's rows. This is
    both the persistence proof (survives restart) and the isolation proof.
    """
    return db.list_bookings(business_id)
