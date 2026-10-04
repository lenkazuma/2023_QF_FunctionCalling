import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import run_conversation  # noqa: E402
from tools import build_registry, calculate, delivery_inquiry, delivery_order, dispatch  # noqa: E402


def test_calculate_handles_the_demo_prompt():
    assert calculate("114514+973580")["result"] == 1088094


@pytest.mark.parametrize("expression", ["__import__('os').system('echo hi')", "a+1", "2**999999", "1/0"])
def test_calculate_rejects_unsafe_or_invalid_input(expression):
    assert "error" in calculate(expression)


def test_delivery_inquiry_filters_by_price():
    items = delivery_inquiry("南京路", 20)["items"]
    assert items and all(item["price"] <= 20 for item in items)


def test_delivery_order_validates_id():
    assert delivery_order("20")["result"] is True
    assert delivery_order("999")["result"] is False


def test_dispatch_passes_arguments_by_name_in_any_order():
    records = []
    registry = build_registry(records)
    result = dispatch(
        {"name": "extract_employee_info", "arguments": json.dumps({"id": "918604", "department": "HR", "name": "李红"})},
        registry,
    )
    assert result["result"] is True
    assert records == [{"姓名": "李红", "部门": "HR", "学历": "", "工号": "918604"}]


@pytest.mark.parametrize(
    "call",
    [
        {"name": "nope", "arguments": "{}"},
        {"name": "calculate", "arguments": "not json"},
        {"name": "calculate", "arguments": json.dumps({"wrong": 1})},
    ],
)
def test_dispatch_reports_errors_instead_of_raising(call):
    assert "error" in dispatch(call, build_registry([]))


def test_run_conversation_executes_function_then_returns_answer():
    replies = iter(
        [
            {"function_call": {"name": "calculate", "arguments": json.dumps({"expression": "1+2"})}},
            {"result": "结果是 3"},
        ]
    )
    seen = []

    def fake_model(messages):
        seen.append(list(messages))
        return next(replies)

    messages = [{"role": "user", "content": "1+2?"}]
    answer, trace = run_conversation(fake_model, messages, build_registry([]))
    assert answer == "结果是 3"
    assert trace[0]["result"]["result"] == 3
    assert [m["role"] for m in seen[1]] == ["user", "assistant", "function"]


def test_run_conversation_stops_after_limit():
    def looping_model(messages):
        return {"function_call": {"name": "calculate", "arguments": json.dumps({"expression": "1"})}}

    answer, trace = run_conversation(looping_model, [{"role": "user", "content": "x"}], build_registry([]), max_function_calls=2)
    assert len(trace) == 2
    assert "上限" in answer


def test_run_conversation_raises_on_api_error():
    with pytest.raises(RuntimeError):
        run_conversation(lambda m: {"error_code": 110, "error_msg": "Access token invalid"}, [], build_registry([]))
