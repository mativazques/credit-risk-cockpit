"""Unit tests for the FastAPI copilot endpoint (C3.2) — the agent is faked.

Verifies the HTTP contract only: a well-formed question reaches the agent and its result
is returned as JSON; malformed requests are rejected before any model call.
"""
import pytest
from fastapi.testclient import TestClient

from copilot import api, config


client = TestClient(api.app)


@pytest.fixture(autouse=True)
def _reset_state():
    """Cache + limiter are process-wide singletons; isolate each test."""
    api.cache.clear()
    api.limiter.reset()
    yield


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


# --- L1: input cap (reject before the model call) ----------------------------------

def test_ask_rejects_overlong_question():
    resp = client.post("/ask", json={"question": "x" * (config.MAX_INPUT_CHARS + 1)})
    assert resp.status_code == 422


# --- L3: on-topic router (off-topic refused, agent never called) -------------------

def test_off_topic_question_is_refused_without_calling_the_agent(monkeypatch):
    called = []
    monkeypatch.setattr(api, "answer", lambda q: called.append(q) or {"answer": "x", "tool_calls": []})
    resp = client.post("/ask", json={"question": "what's the capital of France?"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == config.OFF_TOPIC_MESSAGE
    assert called == []


# --- L4: answer cache (identical question served once) -----------------------------

def test_identical_question_hits_cache_and_calls_agent_once(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "answer", lambda q: (calls.append(q), {"answer": "cached", "tool_calls": []})[1])
    payload = {"question": "default rate for 2018Q1 cohort?"}
    a = client.post("/ask", json=payload)
    b = client.post("/ask", json=payload)
    assert a.json() == b.json()
    assert len(calls) == 1


# --- L2: rate limit (one caller can't burn the shared budget) ----------------------

def test_rate_limit_returns_429_after_the_burst(monkeypatch):
    monkeypatch.setattr(api, "answer", lambda q: {"answer": "ok", "tool_calls": []})
    statuses = [
        client.post("/ask", json={"question": f"default rate cohort 2018Q{i}?"}).status_code
        for i in range(config.PER_IP_CAPACITY + 2)
    ]
    assert statuses[:config.PER_IP_CAPACITY] == [200] * config.PER_IP_CAPACITY
    assert 429 in statuses
