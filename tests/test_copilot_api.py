"""Unit tests for the FastAPI copilot endpoint (C3.2) — the agent is faked.

Verifies the HTTP contract only: a well-formed question reaches the agent and its result
is returned as JSON; malformed requests are rejected before any model call.
"""
from fastapi.testclient import TestClient

from copilot import api


client = TestClient(api.app)


def test_health_ok():
    assert client.get("/health").status_code == 200


def test_ask_returns_the_agent_answer(monkeypatch):
    monkeypatch.setattr(
        api, "answer",
        lambda q: {"answer": f"echo: {q}", "tool_calls": []},
    )
    resp = client.post("/ask", json={"question": "what is the default rate?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "echo: what is the default rate?"
    assert body["tool_calls"] == []


def test_ask_rejects_missing_question():
    assert client.post("/ask", json={}).status_code == 422


def test_ask_rejects_blank_question():
    assert client.post("/ask", json={"question": "   "}).status_code == 422
