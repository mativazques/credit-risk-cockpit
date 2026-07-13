"""FastAPI surface for the copilot (C3.2 + C3.3 hardening).

POST /ask over the governed agent, wrapped in defense-in-depth so a public, anonymous
endpoint stays within the AI Studio free-tier $0 ceiling and on-topic:
  L1 input cap   — reject overly long questions before any token is spent (pydantic).
  L4 cache       — identical questions are served from memory, never re-computed.
  L3 router      — off-topic questions get a zero-token canned refusal.
  L2 rate limit  — per-IP token bucket + global daily cap gate the actual model call.
Order is chosen so only novel, on-topic questions ever consume the model budget.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from . import config
from .agent import answer
from .cache import AnswerCache
from .ratelimit import RateLimiter
from .router import is_on_topic

app = FastAPI(title="Credit-Risk Cockpit Copilot", version="0.1.0")

cache = AnswerCache(capacity=config.CACHE_CAPACITY)
limiter = RateLimiter(
    capacity=config.PER_IP_CAPACITY,
    refill_per_sec=config.PER_IP_REFILL_PER_SEC,
    daily_limit=config.GLOBAL_DAILY_LIMIT,
)


class AskRequest(BaseModel):
    question: str = Field(max_length=config.MAX_INPUT_CHARS)

    @field_validator("question")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()


class AskResponse(BaseModel):
    answer: str
    tool_calls: list[dict]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, request: Request) -> dict:
    question = req.question

    cached = cache.get(question)
    if cached is not None:
        return cached

    if not is_on_topic(question):
        return {"answer": config.OFF_TOPIC_MESSAGE, "tool_calls": []}

    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail=config.RATE_LIMIT_MESSAGE)

    result = answer(question)
    cache.set(question, result)
    return result
