"""Functions exposed to ERNIE function calling, plus their JSON schemas and a dispatcher."""

from __future__ import annotations

import ast
import json
import operator
from typing import Any, Callable

import requests

MENU = [
    {"id": "20", "food": "肯德基疯狂星期四", "price": 50},
    {"id": "21", "food": "麦当劳巨无霸套餐", "price": 38},
    {"id": "22", "food": "沙县小吃蒸饺套餐", "price": 18},
    {"id": "23", "food": "兰州拉面加蛋", "price": 22},
    {"id": "24", "food": "日式鳗鱼饭", "price": 68},
]

_BIN_OPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type, Callable[[Any], Any]] = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指数过大")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("只支持数字和 + - * / // % ** 运算")


def calculate(expression: str) -> dict:
    """Safely evaluate an arithmetic expression (no names, calls or attributes)."""
    normalized = expression.replace("×", "*").replace("÷", "/").replace("（", "(").replace("）", ")")
    try:
        result = _eval_node(ast.parse(normalized, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return {"error": f"无法计算: {exc}"}
    return {"expression": expression, "result": result}


def get_current_temperature(location: str, unit: str = "摄氏度") -> dict:
    """Look up the current temperature via the free Open-Meteo API."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "zh"},
            timeout=10,
        ).json()
        if not geo.get("results"):
            return {"error": f"找不到城市: {location}"}
        place = geo["results"][0]
        weather = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m",
                "temperature_unit": "fahrenheit" if unit == "华氏度" else "celsius",
            },
            timeout=10,
        ).json()
        return {
            "location": place.get("name", location),
            "temperature": weather["current"]["temperature_2m"],
            "unit": unit,
        }
    except (requests.RequestException, KeyError, ValueError) as exc:
        return {"error": f"天气服务暂不可用: {exc}"}


def delivery_inquiry(location: str, expect_price: int | None = None) -> dict:
    items = MENU if expect_price is None else [item for item in MENU if item["price"] <= int(expect_price)]
    return {"location": location, "items": items or MENU[:1]}


def delivery_order(id: str, food: str | None = None) -> dict:
    item = next((entry for entry in MENU if entry["id"] == str(id)), None)
    if item is None:
        return {"result": False, "reason": f"没有编号为 {id} 的商品"}
    return {"result": True, "id": item["id"], "food": item["food"], "price": item["price"]}


def make_employee_recorder(records: list[dict]) -> Callable[..., dict]:
    def extract_employee_info(name: str, department: str = "", certificate: str = "", id: str = "") -> dict:
        record = {"姓名": name, "部门": department, "学历": certificate, "工号": str(id)}
        records.append(record)
        return {"result": True, "record": record, "total": len(records)}

    return extract_employee_info


FUNCTIONS: list[dict] = [
    {
        "name": "calculate",
        "description": "计算数学表达式，例如 114514+973580 或 (3+5)*2",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "只包含数字和运算符的表达式"}},
            "required": ["expression"],
        },
    },
    {
        "name": "delivery_inquiry",
        "description": "查询附近可点的外卖商品",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "地址信息，包括街道、门牌号、城市、省份等信息"},
                "expect_price": {"type": "integer", "description": "期望的最高价格（元）"},
            },
            "required": ["location"],
        },
    },
    {
        "name": "delivery_order",
        "description": "外卖下单",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "商品id"},
                "food": {"type": "string", "description": "商品名称"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "extract_employee_info",
        "description": "将员工信息录入系统",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "姓名"},
                "department": {"type": "string", "description": "部门"},
                "certificate": {"type": "string", "description": "学历文凭"},
                "id": {"type": "string", "description": "工号"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_current_temperature",
        "description": "获取指定城市当前的气温",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "城市名称"},
                "unit": {"type": "string", "enum": ["摄氏度", "华氏度"]},
            },
            "required": ["location"],
        },
    },
]


def build_registry(employee_records: list[dict]) -> dict[str, Callable[..., dict]]:
    return {
        "calculate": calculate,
        "delivery_inquiry": delivery_inquiry,
        "delivery_order": delivery_order,
        "extract_employee_info": make_employee_recorder(employee_records),
        "get_current_temperature": get_current_temperature,
    }


def dispatch(function_call: dict, registry: dict[str, Callable[..., dict]]) -> dict:
    """Run the function the model asked for, passing arguments by name."""
    name = function_call.get("name", "")
    func = registry.get(name)
    if func is None:
        return {"error": f"未知函数: {name}"}
    try:
        args = json.loads(function_call.get("arguments") or "{}")
    except json.JSONDecodeError:
        return {"error": "函数参数不是合法的 JSON"}
    if not isinstance(args, dict):
        return {"error": "函数参数必须是 JSON 对象"}
    try:
        return func(**args)
    except TypeError as exc:
        return {"error": f"参数不匹配: {exc}"}
