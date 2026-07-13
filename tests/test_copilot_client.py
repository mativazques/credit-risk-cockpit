"""Unit tests for the copilot HTTP client (C3.4) — no server, requests is faked.

The Streamlit chat panel calls the FastAPI /ask endpoint through this client. It maps
HTTP outcomes to something the UI can always render: a normal answer, a graceful message
for the hardening rejections (429/422), and a clear error when the service is down.
"""
import pytest

from copilot import client


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _fake_post(status_code, payload):
    def _post(url, json=None, timeout=None):
        _post.seen = {"url": url, "json": json, "timeout": timeout}
        return FakeResponse(status_code, payload)
    return _post


def test_successful_answer_is_returned(monkeypatch):
    post = _fake_post(200, {"answer": "12%", "tool_calls": [{"name": "query_metric"}]})
    monkeypatch.setattr(client.requests, "post", post)
    out = client.ask("default rate?", base_url="http://x:8000")
    assert out == {"answer": "12%", "tool_calls": [{"name": "query_metric"}]}
    assert post.seen["url"] == "http://x:8000/ask"
    assert post.seen["json"] == {"question": "default rate?"}


def test_rate_limited_returns_the_graceful_message(monkeypatch):
    monkeypatch.setattr(client.requests, "post", _fake_post(429, {"detail": "slow down"}))
    out = client.ask("q", base_url="http://x:8000")
    assert out["answer"] == "slow down"
    assert out["tool_calls"] == []


def test_rejected_input_returns_a_friendly_message(monkeypatch):
    monkeypatch.setattr(client.requests, "post", _fake_post(422, {"detail": "bad"}))
    out = client.ask("q", base_url="http://x:8000")
    assert out["tool_calls"] == []
    assert "credit-risk" in out["answer"].lower()


def test_server_error_raises(monkeypatch):
    monkeypatch.setattr(client.requests, "post", _fake_post(500, {}))
    with pytest.raises(client.CopilotError):
        client.ask("q", base_url="http://x:8000")


def test_connection_failure_raises_copilot_error(monkeypatch):
    def _boom(*a, **k):
        raise client.requests.RequestException("connection refused")
    monkeypatch.setattr(client.requests, "post", _boom)
    with pytest.raises(client.CopilotError):
        client.ask("q", base_url="http://x:8000")
