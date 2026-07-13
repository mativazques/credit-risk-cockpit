"""The governed function-calling loop (C3.2).

A question in, a grounded answer out. Automatic function calling is DISABLED on purpose:
we run the loop ourselves so every tool call goes through the governed `dispatch` (which
only ever exposes list_metrics / query_metric / compare_cohorts and returns structured
errors, never raw SQL). The loop is bounded by MAX_STEPS so a misbehaving model can't
spin. No LLM logic leaks into the tools; no SQL leaks into the model.
"""
from __future__ import annotations

from typing import Any

from google.genai import types

from . import config
from .prompt import SYSTEM_PROMPT
from .tools import TOOL_DECLARATIONS, dispatch


def _tool() -> types.Tool:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name=d["name"],
                description=d["description"],
                parameters_json_schema=d["parameters"],
            )
            for d in TOOL_DECLARATIONS
        ]
    )


def _generation_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[_tool()],
        max_output_tokens=config.MAX_OUTPUT_TOKENS,
        temperature=config.TEMPERATURE,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )


def answer(
    question: str,
    *,
    client: Any = None,
    model: str = config.MODEL,
    max_steps: int = config.MAX_STEPS,
) -> dict:
    """Answer a question, running governed tools as the model requests them.

    Returns {"answer": str, "tool_calls": [{"name", "args", "result"}, ...]}.
    """
    client = client or config.get_client()
    cfg = _generation_config()
    contents: list[Any] = [
        types.Content(role="user", parts=[types.Part.from_text(text=question)])
    ]
    trace: list[dict] = []

    for _ in range(max_steps):
        response = client.models.generate_content(
            model=model, contents=contents, config=cfg
        )
        parts = response.candidates[0].content.parts or []
        calls = [p.function_call for p in parts if p.function_call]

        if not calls:
            return {"answer": response.text, "tool_calls": trace}

        contents.append(response.candidates[0].content)
        result_parts = []
        for fc in calls:
            args = dict(fc.args or {})
            result = dispatch(fc.name, args)
            trace.append({"name": fc.name, "args": args, "result": result})
            result_parts.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="user", parts=result_parts))

    return {"answer": config.STEP_LIMIT_MESSAGE, "tool_calls": trace}
