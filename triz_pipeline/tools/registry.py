"""Tool Registry：注册和管理可供 Skill 调用的 Tools。"""

from typing import Callable, Any

from triz_pipeline.tools.fos_search import search_patents
from triz_pipeline.tools.solve_contradiction import solve_contradiction
from triz_pipeline.tools.query_parameters import map_to_parameters, query_parameters
from triz_pipeline.tools.query_matrix import query_matrix
from triz_pipeline.tools.query_separation import query_separation


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


def register_default_tools() -> ToolRegistry:
    """注册所有默认 Tools。供 Orchestrator 和 Agent 共用。"""
    registry = ToolRegistry()

    # 高层 Tools（Orchestrator/Agent 直接调用）
    registry.register(
        name="solve_contradiction",
        func=solve_contradiction,
        schema={
            "name": "solve_contradiction",
            "description": "根据矛盾对查询 TRIZ 矛盾矩阵，返回推荐的发明原理编号。当你已经定义了技术矛盾或物理矛盾后，必须调用此工具获取发明原理。",
            "parameters": {
                "type": "object",
                "properties": {
                    "improve": {
                        "type": "string",
                        "description": "需要改善的方面（简短描述）",
                    },
                    "worsen": {
                        "type": "string",
                        "description": "随之恶化的方面（简短描述）",
                    },
                    "problem_type": {
                        "type": "string",
                        "enum": ["tech", "phys"],
                        "description": "矛盾类型：tech=技术矛盾，phys=物理矛盾",
                    },
                },
                "required": ["improve", "worsen", "problem_type"],
            },
        },
    )
    registry.register(
        name="search_patents",
        func=search_patents,
        schema={
            "name": "search_patents",
            "description": "搜索 Google Patents 跨领域专利案例。当你有了发明原理后，调用此工具搜索相关跨领域案例作为方案参考。",
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索词列表（英文，3-8个关键词）",
                    },
                    "principles": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "发明原理编号列表",
                    },
                    "limit_per_query": {
                        "type": "integer",
                        "description": "每个搜索词返回的结果数量",
                        "default": 5,
                    },
                },
                "required": ["queries", "principles"],
            },
        },
    )

    # 底层 Tools（供 Skill 内部调用）
    registry.register(
        name="map_to_parameters",
        func=map_to_parameters,
        schema={
            "name": "map_to_parameters",
            "description": "将中文描述映射到 39 个 TRIZ 工程参数 ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "improve_aspect": {
                        "type": "string",
                        "description": "需要改善的方面（2-6个中文词）",
                    },
                    "worsen_aspect": {
                        "type": "string",
                        "description": "随之恶化的方面（2-6个中文词）",
                    },
                },
                "required": ["improve_aspect", "worsen_aspect"],
            },
        },
    )
    registry.register(
        name="query_matrix",
        func=query_matrix,
        schema={
            "name": "query_matrix",
            "description": "查询阿奇舒勒矛盾矩阵",
            "parameters": {
                "type": "object",
                "properties": {
                    "improve_param_id": {"type": "integer"},
                    "worsen_param_id": {"type": "integer"},
                },
                "required": ["improve_param_id", "worsen_param_id"],
            },
        },
    )
    registry.register(
        name="query_separation",
        func=query_separation,
        schema={
            "name": "query_separation",
            "description": "查询物理矛盾的分离原理",
            "parameters": {
                "type": "object",
                "properties": {"contradiction_desc": {"type": "string"}},
                "required": ["contradiction_desc"],
            },
        },
    )
    return registry
