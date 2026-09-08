"""Per-IP rate limiting for the public /ask endpoint."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def _retry_after(detail: str) -> str:
    """slowapi puts the wait in a sentence like '... Retry after 30 second(s)'."""
    if "Retry after " in detail:
        return detail.split("Retry after ")[1].split(" ")[0]
    return "60"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    seconds = _retry_after(exc.detail)
    return JSONResponse(
        status_code=429,
        # Every error in this API uses `detail`, matching FastAPI's own shape.
        content={"detail": f"Rate limit exceeded. Try again in {seconds} seconds."},
        headers={"Retry-After": seconds},
    )
