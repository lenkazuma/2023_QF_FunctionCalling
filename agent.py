"""Model ↔ function loop for ERNIE function calling."""

from __future__ import annotations

import json
from typing import Any, Callable

from tools import FUNCTIONS, dispatch

ModelCall = Callable[[list[dict]], dict]


def make_qianfan_caller(model: str, ak: str | None = None, sk: str | None = None, temperature: float = 0.01) -> ModelCall:
    import qianfan

    credentials = {"ak": ak, "sk": sk} if ak and sk else {}
    chat_comp = qianfan.ChatCompletion(**credentials)

    def call(messages: list[dict]) -> dict:
        response = chat_comp.do(model=model, messages=messages, functions=FUNCTIONS, temperature=temperature)
        return dict(getattr(response, "body", response))

    return call


def run_conversation(
    call_model: ModelCall,
    messages: list[dict],
    registry: dict[str, Callable[..., dict]],
    max_function_calls: int = 3,
) -> tuple[str, list[dict[str, Any]]]:
    """Ask the model, executing requested functions until it replies with text.

    ``messages`` is extended in place with the function-call exchange.
    Returns the final answer and a trace of the functions that were called.
    """
    trace: list[dict[str, Any]] = []
    for _ in range(max_function_calls + 1):
        body = call_model(messages)
        if body.get("error_code"):
            raise RuntimeError(f"千帆接口错误 {body.get('error_code')}: {body.get('error_msg')}")

        function_call = body.get("function_call")
        if not function_call:
            return body.get("result", ""), trace
        if len(trace) >= max_function_calls:
            break

        result = dispatch(function_call, registry)
        trace.append({"name": function_call.get("name"), "arguments": function_call.get("arguments"), "result": result})
        messages.append({"role": "assistant", "content": None, "function_call": function_call})
        messages.append(
            {"role": "function", "name": function_call.get("name"), "content": json.dumps(result, ensure_ascii=False)}
        )
    return "函数调用次数超过上限，已停止。", trace
