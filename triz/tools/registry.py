"""Tool Registry：注册和管理可供 Skill 调用的 Tools。"""
from typing import Callable, Any


class ToolRegistry:
    """Tool 注册表。

    每个 Tool 包含：
    - func: 实际执行函数
    - schema: OpenAI function calling 格式的 schema
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, func: Callable, schema: dict = None) -> None:
        """注册一个 Tool。"""
        self._tools[name] = {"func": func, "schema": schema}

    def get(self, name: str) -> Callable | None:
        """按名称获取 Tool 函数。"""
        tool = self._tools.get(name)
        return tool["func"] if tool else None

    def get_schemas(self) -> list[dict]:
        """获取所有注册 Tool 的 OpenAI function schemas。"""
        return [
            {"type": "function", "function": tool["schema"]}
            for tool in self._tools.values()
            if tool["schema"]
        ]

    def execute(self, name: str, arguments: dict) -> Any:
        """执行指定 Tool，传入参数 dict。"""
        if name not in self._tools:
            raise ValueError(f"未知 Tool: {name}")
        return self._tools[name]["func"](**arguments)

    def list_tools(self) -> list[str]:
        """返回所有已注册 Tool 的名称列表。"""
        return list(self._tools.keys())
