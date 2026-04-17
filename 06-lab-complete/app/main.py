"""
Production AI Agent — Kết hợp tất cả Day 12 concepts

Checklist:
  ✅ Config từ environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication (X-API-Key)
  ✅ Rate limiting (10 req/min/user via Redis)
  ✅ Cost guard ($10/month/user via Redis)
  ✅ Conversation history (Redis — stateless)
  ✅ Input validation (Pydantic)
  ✅ Health check + Readiness probe (checks Redis)
  ✅ Graceful shutdown (SIGTERM)
  ✅ Security headers
  ✅ CORS
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_cost

# Mock LLM (thay bằng OpenAI/Anthropic khi có API key)
from utils.mock_llm import ask as llm_ask

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# ─────────────────────────────────────────────────────────
# Redis connection (for conversation history, readiness)
# ─────────────────────────────────────────────────────────
_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


# ─────────────────────────────────────────────────────────
# Conversation history — stored in Redis (stateless design)
# ─────────────────────────────────────────────────────────
MAX_HISTORY = 20


def get_conversation_history(user_id: str) -> list[dict]:
    """Get conversation history from Redis."""
    r = get_redis()
    raw = r.lrange(f"history:{user_id}", 0, -1)
    return [json.loads(item) for item in raw]


def save_to_history(user_id: str, question: str, answer: str) -> None:
    """Save Q&A pair to conversation history in Redis."""
    r = get_redis()
    key = f"history:{user_id}"
    entry = json.dumps({"role": "user", "content": question})
    r.rpush(key, entry)
    entry = json.dumps({"role": "assistant", "content": answer})
    r.rpush(key, entry)
    # Trim to max history
    r.ltrim(key, -MAX_HISTORY * 2, -1)
    r.expire(key, 3600)  # 1 hour TTL


# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    # Check Redis connectivity at startup
    try:
        get_redis().ping()
        logger.info(json.dumps({"event": "redis_connected"}))
    except Exception as e:
        logger.warning(json.dumps({"event": "redis_unavailable", "error": str(e)}))
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))


# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")
    user_id: str = Field(default="default", min_length=1, max_length=100,
                         description="User ID for conversation tracking")


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    user_id: str
    timestamp: str


# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent.

    **Authentication:** Include header `X-API-Key: <your-key>`
    """
    user_key = body.user_id

    # Rate limit per user (Redis-backed, stateless)
    check_rate_limit(user_key)

    # Budget check per user (Redis-backed, stateless)
    input_tokens = len(body.question.split()) * 2
    estimated_cost = (input_tokens / 1000) * 0.00015
    check_budget(user_key, estimated_cost)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": user_key,
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    # Get conversation history from Redis (stateless)
    history = get_conversation_history(user_key)

    # Call LLM
    answer = llm_ask(body.question)

    # Save to conversation history in Redis
    save_to_history(user_key, body.question, answer)

    # Record cost
    output_tokens = len(answer.split()) * 2
    total_cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    record_cost(user_key, total_cost)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        user_id=user_key,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Checks Redis connection. LB stops routing if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready — app still starting")
    # Check Redis connectivity
    try:
        get_redis().ping()
    except Exception as e:
        raise HTTPException(503, f"Not ready — Redis unavailable: {e}")
    return {"ready": True, "redis": "ok"}


@app.get("/metrics", tags=["Operations"])
def metrics(api_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
    }


# ─────────────────────────────────────────────────────────
# Graceful Shutdown — handle SIGTERM from container orchestrator
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    global _is_ready
    logger.info(json.dumps({"event": "SIGTERM_received", "signum": signum}))
    _is_ready = False  # Stop accepting new traffic via /ready

signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
