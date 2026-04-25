import pytest
from triz.tools.registry import ToolRegistry


def test_register_and_execute():
    registry = ToolRegistry()

    def add(a: int, b: int) -> int:
        return a + b

    registry.register(
        name="add",
        func=add,
        schema={
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        }
    )

    schemas = registry.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "add"

    result = registry.execute("add", {"a": 2, "b": 3})
    assert result == 5


def test_execute_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="未知 Tool"):
        registry.execute("unknown", {})
