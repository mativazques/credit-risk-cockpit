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

# --- Abuse hardening (C3.3) --------------------------------------------------------

# L1 — reject overly long input before spending any tokens.
MAX_INPUT_CHARS = 500

# L2 — per-IP token bucket + a global daily ceiling kept safely under the AI Studio
# free-tier quota (1,500/day), so the whole demo can't exhaust it.
PER_IP_CAPACITY = 5           # burst allowance per visitor
PER_IP_REFILL_PER_SEC = 0.1   # ~6 questions/minute sustained
GLOBAL_DAILY_LIMIT = 1000

# L4 — cache identical questions so repeats never re-spend the budget.
CACHE_CAPACITY = 256

# Canned, zero-token responses.
OFF_TOPIC_MESSAGE = (
    "I only answer questions about this demo's credit-risk metrics — vintage curves, "
    "cohorts, default and loss rates, DTI. Ask me about those."
)
RATE_LIMIT_MESSAGE = (
    "This public demo has hit its request limit for now. Please try again shortly."
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
