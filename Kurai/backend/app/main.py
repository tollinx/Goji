from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from Kurai.backend.app.config import settings
from Kurai.backend.app.rate_limit import limiter, rate_limit_exceeded_handler


app = FastAPI(
    title="Kurai RAG API",
    description="Compliance-focused RAG retrieval API",
    version="0.1.0"
)

# Add rate limiting state
app.state.limiter = limiter

# Register rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0"
    }


@app.post("/ask", response_model=AskResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def ask_question(request: Request, ask_request: AskRequest):
    """
    Stub endpoint for asking questions.
    Phase 1: returns hardcoded response.
    Phase 2+: will implement retrieval and generation.
    """
    # Phase 1 stub response
    return AskResponse(
        answer="hello",
        citations=[]
    )
