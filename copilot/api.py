"""FastAPI surface for the copilot (C3.2).

A single POST /ask endpoint over the governed agent, plus a health check. Abuse
hardening (input caps, on-topic router, rate limiting, cache) is layered on in C3.3.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, field_validator

from .agent import answer

app = FastAPI(title="Credit-Risk Cockpit Copilot", version="0.1.0")


class AskRequest(BaseModel):
    question: str

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
def ask(req: AskRequest) -> dict:
    return answer(req.question)
