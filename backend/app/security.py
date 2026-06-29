"""
Security: API-key auth + rate limiting.

Access model:
  • /chat, /widget, /business/{id}  -> PUBLIC (patients use them) but /chat is
    rate-limited so it can't be spammed into a huge Gemini bill.
  • /bookings?business_id=X          -> needs THAT business's api_key (or the
    admin key). This is patient data; it must never be open.
  • /businesses (list all clients)   -> admin key only.

Secure by default: if no key matches, access is denied.
"""

import time

from fastapi import Header, HTTPException, Request

from app import db
from app.config import get_settings

# ── rate limiting (in-memory, per process) ──────────────────────────────────
# Fine for a single instance (our case). At multi-instance scale this moves to
# a shared store like Redis — noted, not needed yet.
_hits: dict[str, list[float]] = {}


def rate_limit(request: Request, limit: int = 30, window: int = 60) -> None:
    """Allow at most `limit` requests per `window` seconds per client IP."""
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    now = time.time()
    arr = _hits.setdefault(ip, [])
    cutoff = now - window
    arr[:] = [t for t in arr if t > cutoff]  # drop old hits
    if len(arr) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests — please slow down.")
    arr.append(now)


# ── api-key auth ─────────────────────────────────────────────────────────────
def _admin_key() -> str:
    return (getattr(get_settings(), "admin_api_key", "") or "").strip()


def check_admin(x_api_key: str | None) -> None:
    """Require the admin key. 503 if the server has no admin key configured."""
    admin = _admin_key()
    if not admin:
        raise HTTPException(status_code=503, detail="Admin API key not configured on the server.")
    if x_api_key != admin:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key.")


def check_business_access(business_id: str, x_api_key: str | None) -> None:
    """Require this business's api_key — or the admin key (which opens any)."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key.")
    admin = _admin_key()
    if admin and x_api_key == admin:
        return  # admin can read any business
    biz = db.get_business(business_id)
    if biz is None:
        raise HTTPException(status_code=404, detail="Unknown business.")
    if not biz.get("api_key") or x_api_key != biz["api_key"]:
        raise HTTPException(status_code=403, detail="API key does not match this business.")


# FastAPI reads the "X-API-Key" header into this dependency parameter.
def api_key_header(x_api_key: str | None = Header(default=None)) -> str | None:
    return x_api_key
