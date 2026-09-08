"""FastAPI entrypoint: /health and /ask.

/ask delegates to generation.ask, which grounds its answer in the drink corpus
by calling the MCP server's tools. The MCP server runs as a subprocess started
here at startup and shut down with the app.
"""

import logging
from contextlib import asynccontextmanager

import anthropic
import groq
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded

from app import generation
from app.config import settings
from app.mcp_client import mcp_connection
from app.rate_limit import limiter, rate_limit_exceeded_handler

VERSION = "0.1.0"
UNAVAILABLE = "The bartender is unreachable right now. Try again in a moment."

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    provider = settings.LLM_PROVIDER
    key_var = "GROQ_API_KEY" if provider == "groq" else "ANTHROPIC_API_KEY"
    if not getattr(settings, key_var):
        logger.warning("%s is not set — /ask will return 503 until it is.", key_var)
    logger.info("Answering with %s", provider)

    await mcp_connection.connect()
    yield
    await mcp_connection.close()


app = FastAPI(
    title="Goji & Gin API",
    description="RAG + MCP tool calling drink recommender",
    version=VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(generation.GenerationError)
async def handle_generation_error(request: Request, exc: generation.GenerationError):
    """Misconfiguration we detected ourselves, e.g. a missing API key."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def handle_llm_error(request: Request, exc: Exception):
    """
    A 4xx from the provider means the deployment is misconfigured (bad key, no
    credit, unknown model) and the upstream message says exactly how to fix it,
    so it's worth passing through. Anything else is transient.

    Both SDKs are generated from the same toolchain, so APIStatusError carries
    `status_code` and `body` in either one.
    """
    logger.exception("%s call failed", settings.LLM_PROVIDER)

    detail = UNAVAILABLE
    status_errors = (anthropic.APIStatusError, groq.APIStatusError)
    if isinstance(exc, status_errors) and 400 <= exc.status_code < 500:
        body = exc.body if isinstance(exc.body, dict) else {}
        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        detail = error.get("message") or "The bartender is misconfigured. Check the server logs."

    return JSONResponse(status_code=503, content={"detail": detail})


# Neither SDK's base error shares a parent with the other, so register both.
app.add_exception_handler(anthropic.AnthropicError, handle_llm_error)
app.add_exception_handler(groq.GroqError, handle_llm_error)


class AskRequest(BaseModel):
    question: str


class DrinkRef(BaseModel):
    id: str
    name: str


class AskResponse(BaseModel):
    answer: str
    drink: DrinkRef | None = None


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": VERSION,
        "provider": settings.LLM_PROVIDER,
        "mcp_connected": mcp_connection.session is not None,
    }


@app.post("/ask", response_model=AskResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def ask_question(request: Request, ask_request: AskRequest):
    """Recommend a drink, grounded in the corpus via the MCP search tools."""
    return await generation.ask(ask_request.question)
