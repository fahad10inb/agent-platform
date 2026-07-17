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

import hashlib
import secrets
import time

from fastapi import Header, HTTPException, Request

from app import db
from app.config import get_settings

# ── api-key hashing ──────────────────────────────────────────────────────────
# We store a HASH of each business key, never the key itself — so a database
# dump doesn't hand an attacker every tenant's live credential. SHA-256 (not
# bcrypt/argon2) is the correct choice HERE: our keys are high-entropy random
# tokens ("bizkey_" + 24 url-safe bytes ≈ 192 bits), so they're not brute-
# forceable and don't need a slow password KDF — a fast cryptographic hash is
# both standard and right for API tokens. The "sha256:" tag lets verify_key tell
# a hashed value from a legacy plaintext one during migration.
_HASH_PREFIX = "sha256:"


def hash_key(plain: str) -> str:
    """The stored form of an API key."""
    return _HASH_PREFIX + hashlib.sha256((plain or "").encode()).hexdigest()


def verify_key(presented: str, stored: str) -> bool:
    """Constant-time check of a presented key against its stored form.

    Handles BOTH shapes so a live migration can't lock anyone out: a hashed
    value ('sha256:…') is compared by hashing the presented key; a legacy
    plaintext value is compared directly (still constant-time). New writes are
    always hashed, and init_db upgrades old plaintext rows, so the legacy branch
    fades away on its own."""
    if not presented or not stored:
        return False
    if stored.startswith(_HASH_PREFIX):
        return secrets.compare_digest(hash_key(presented), stored)
    return secrets.compare_digest(presented, stored)  # legacy plaintext row

# ── rate limiting (in-memory, per process) ──────────────────────────────────
# Fine for a single instance (our case). At multi-instance scale this moves to
# a shared store like Redis — noted, not needed yet.
_hits: dict[str, list[float]] = {}


def rate_limit(request: Request, limit: int = 30, window: int = 60, bucket: str = "chat") -> None:
    """Allow at most `limit` requests per `window` seconds per client IP.

    The client IP is the LAST x-forwarded-for hop — that's the one appended by
    our own proxy (Render), so it can't be spoofed by the caller. The FIRST hop
    is client-supplied: trusting it let anyone reset their own limit per request.
    `bucket` keeps differently-limited endpoints from sharing one counter.
    """
    fwd = request.headers.get("x-forwarded-for", "")
    hops = [h.strip() for h in fwd.split(",") if h.strip()]
    ip = hops[-1] if hops else (request.client.host if request.client else "unknown")
    now = time.time()
    arr = _hits.setdefault(f"{bucket}:{ip}", [])
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
    # compare_digest = constant-time comparison (a plain != leaks key length /
    # prefix timing to an attacker probing the admin endpoint).
    if not secrets.compare_digest(x_api_key or "", admin):
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key.")


def check_business_access(business_id: str, x_api_key: str | None) -> None:
    """Require this business's api_key — or the admin key (which opens any)."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key.")
    admin = _admin_key()
    if admin and secrets.compare_digest(x_api_key, admin):
        return  # admin can read any business
    biz = db.get_business(business_id)
    # Unknown business and wrong key answer IDENTICALLY (403): a distinct 404
    # here let anyone with any key enumerate which business ids exist.
    if biz is None or not verify_key(x_api_key, biz.get("api_key") or ""):
        raise HTTPException(status_code=403, detail="API key does not match this business.")


# FastAPI reads the "X-API-Key" header into this dependency parameter.
def api_key_header(x_api_key: str | None = Header(default=None)) -> str | None:
    return x_api_key
