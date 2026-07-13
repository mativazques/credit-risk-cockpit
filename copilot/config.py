"""Copilot runtime configuration and Gemini client factory.

Everything that governs cost and behavior of the LLM call lives here so it is easy to
audit: the model alias, the output-token cap, temperature, and the manual step budget.
Auth is a single AI Studio API key (no billing attached → the free-tier daily quota is a
hard $0 ceiling). Vertex is the documented production path, selected by env if ever
needed.
"""
from __future__ import annotations

import os

from google import genai

API_KEY_ENV = "GEMINI_API_KEY"

# `-latest` alias avoids retirement breakage; flash-lite is cheapest + free-tier eligible.
MODEL = os.environ.get("COPILOT_MODEL", "gemini-flash-lite-latest")

# L1 cost bound: cap the model's output; deterministic answers over a governed layer.
MAX_OUTPUT_TOKENS = 512
TEMPERATURE = 0.0

# Manual function-calling budget: at most this many model turns per question.
MAX_STEPS = 5
STEP_LIMIT_MESSAGE = (
    "I couldn't complete that within the tool-call budget. Try asking about a single "
    "metric or cohort comparison."
)


def get_client(api_key: str | None = None) -> genai.Client:
    """Build an AI Studio Gemini client, failing clearly if no key is configured."""
    key = api_key or os.environ.get(API_KEY_ENV)
    if not key:
        raise RuntimeError(
            f"no Gemini API key: set {API_KEY_ENV} in .env "
            "(get one at https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=key, vertexai=False)
