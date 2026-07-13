"""Unit tests for the Gemini function-calling loop (C3.2) — the LLM is faked.

The loop's contract, independent of any real model: send the question + tool
declarations, execute every function call the model returns via the governed `dispatch`,
feed each result back, and stop with the model's final text (or a bounded fallback if it
never stops). No network, no key.
"""
import pytest

from copilot import agent, config


# --- minimal fakes standing in for a google-genai response -------------------------

class FakeFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakePart:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


class FakeContent:
    def __init__(self, parts, role="model"):
        self.parts = parts
        self.role = role


class FakeCandidate:
    def __init__(self, content):
        self.content = content


class FakeResponse:
    def __init__(self, parts, text=None):
        self.candidates = [FakeCandidate(FakeContent(parts))]
        self.text = text


def text_response(text):
    return FakeResponse([FakePart(text=text)], text=text)


def call_response(*calls):
    return FakeResponse([FakePart(function_call=FakeFunctionCall(n, a)) for n, a in calls])


class FakeModels:
    """Returns scripted responses in order; a callable script means 'always this'."""
    def __init__(self, script):
        self._script = script
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(contents)
        if callable(self._script):
            return self._script()
        return self._script.pop(0)


class FakeClient:
    def __init__(self, script):
        self.models = FakeModels(script)


# --- the loop ----------------------------------------------------------------------

def test_direct_text_answer_when_model_calls_no_tool():
    client = FakeClient([text_response("Lifetime default rate is what you'd query.")])
    out = agent.answer("hello", client=client)
    assert out["answer"] == "Lifetime default rate is what you'd query."
    assert out["tool_calls"] == []
    assert len(client.models.calls) == 1


def test_executes_tool_call_then_returns_final_text(monkeypatch):
    monkeypatch.setattr(agent, "dispatch", lambda name, args: {"routed": name, "args": args})
    client = FakeClient([
        call_response(("query_metric", {"metric_id": "default_rate", "window": "lifetime"})),
        text_response("The 2018Q1 cohort defaulted at 12%."),
    ])
    out = agent.answer("why did Q1 move?", client=client)
    assert out["answer"] == "The 2018Q1 cohort defaulted at 12%."
    assert out["tool_calls"] == [{
        "name": "query_metric",
        "args": {"metric_id": "default_rate", "window": "lifetime"},
        "result": {"routed": "query_metric", "args": {"metric_id": "default_rate", "window": "lifetime"}},
    }]
    assert len(client.models.calls) == 2


def test_multiple_tool_calls_in_one_turn_all_dispatched(monkeypatch):
    monkeypatch.setattr(agent, "dispatch", lambda name, args: {"ok": name})
    client = FakeClient([
        call_response(("list_metrics", {}), ("query_metric", {"metric_id": "avg_dti"})),
        text_response("done"),
    ])
    out = agent.answer("compare", client=client)
    assert [c["name"] for c in out["tool_calls"]] == ["list_metrics", "query_metric"]
    assert out["answer"] == "done"


def test_stops_after_max_steps_without_infinite_loop(monkeypatch):
    monkeypatch.setattr(agent, "dispatch", lambda name, args: {"ok": True})
    # A model that never stops calling tools.
    client = FakeClient(lambda: call_response(("list_metrics", {})))
    out = agent.answer("loop forever", client=client, max_steps=3)
    assert len(client.models.calls) == 3
    assert out["answer"] == config.STEP_LIMIT_MESSAGE
    assert len(out["tool_calls"]) == 3


# --- client construction -----------------------------------------------------------

def test_get_client_without_key_raises_a_clear_error(monkeypatch):
    monkeypatch.delenv(config.API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError) as exc:
        config.get_client(api_key=None)
    assert config.API_KEY_ENV in str(exc.value)
