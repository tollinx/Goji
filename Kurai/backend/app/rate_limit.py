from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom handler for rate limit exceeded errors."""
    # Extract retry-after time from the exception
    retry_after = exc.detail.split("Retry after ")[1].split(" ")[0] if "Retry after" in exc.detail else "60"

    return JSONResponse(
        status_code=429,
        content={
            "error": f"Rate limit exceeded. Try again in {retry_after} seconds."
        },
        headers={"Retry-After": retry_after}
    )


# Initialize limiter with per-IP tracking
limiter = Limiter(key_func=get_remote_address)
