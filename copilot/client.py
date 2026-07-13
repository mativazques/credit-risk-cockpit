"""HTTP client for the copilot API (C3.4).

The Streamlit chat panel talks to the FastAPI /ask endpoint through this thin client.
Deliberately depends only on `requests` (no google-genai), so the Streamlit venv can
import it without dragging in the LLM SDK. Maps every HTTP outcome to something the UI
can render: an answer, a graceful message for the hardening rejections, or a clear error
when the service is unreachable.
"""
from __future__ import annotations

import requests

_REJECTED_MESSAGE = (
    "That question was rejected (empty or too long). Try a shorter credit-risk question."
)


class CopilotError(Exception):
    """The copilot service is unreachable or returned an unexpected status."""


def ask(question: str, base_url: str, timeout: int = 30) -> dict:
    """POST a question to the copilot and return {"answer", "tool_calls"}."""
    try:
        resp = requests.post(
            f"{base_url}/ask", json={"question": question}, timeout=timeout
        )
    except requests.RequestException as exc:
        raise CopilotError(f"could not reach the copilot at {base_url}: {exc}") from exc

    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 429:
        return {"answer": resp.json().get("detail", "Rate limit reached."), "tool_calls": []}
    if resp.status_code == 422:
        return {"answer": _REJECTED_MESSAGE, "tool_calls": []}
    raise CopilotError(f"copilot returned HTTP {resp.status_code}")
