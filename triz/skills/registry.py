"""SkillRegistry：自动发现和管理 Agent Skills。"""
import importlib
from pathlib import Path

from triz.skills.base import Skill
from triz.utils.api_client import OpenAIClient


class SkillRegistry:
    """Skill 注册表。

    自动发现 triz/skills/ 下的子文件夹，导入 handler.py 并实例化 Skill。
    支持按节点（node）注册路由规则，Orchestrator 通过节点名动态解析应执行的 Skills。
    """

    def __init__(self, client: OpenAIClient | None = None, tool_registry=None):
        self._skills: dict[str, Skill] = {}
        self._node_routes: dict[str, list[dict]] = {}
        self.client = client
        self.tool_registry = tool_registry
        self._discover()

    def _discover(self):
        """遍历 triz/skills/ 子文件夹，自动发现并注册 Skill。"""
        skills_path = Path(__file__).parent

        for item in skills_path.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            handler_file = item / "handler.py"
            if not handler_file.exists():
                continue

            module_name = f"triz.skills.{item.name}.handler"
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                # 可能是缺少 __init__.py，跳过
                continue

            # 查找模块中的 Skill 子类（非抽象基类本身）
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Skill)
                    and attr is not Skill
                    and getattr(attr, "name", None)
                ):
                    try:
                        skill_instance = attr(client=self.client, tool_registry=self.tool_registry)
                    except TypeError:
                        skill_instance = attr(client=self.client)
                    self._skills[attr.name] = skill_instance

    def register(self, skill: Skill) -> None:
        """手动注册一个 Skill。"""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        """获取指定名称的 Skill。"""
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """列出所有已注册的 Skill 元数据。"""
        return [
            {
                "name": s.name,
                "description": s.description,
                "version": s.version,
            }
            for s in self._skills.values()
        ]

    # ------------------------------------------------------------------
    # 节点路由（Node Routing）
    # ------------------------------------------------------------------

    def register_node_route(
        self,
        node_name: str,
        steps: list,
        condition=None,
        priority: int = 1,
    ) -> None:
        """注册节点路由规则。

        Args:
            node_name: 节点名称（如 "modeling", "solver", "generation"）
            steps: 该节点执行的步骤列表，格式同 Orchestrator._execute_node 的 steps 参数
            condition: 触发条件函数 (ctx) -> bool，None 表示无条件匹配
            priority: 优先级，越高越先匹配（默认 1）
        """
        if node_name not in self._node_routes:
            self._node_routes[node_name] = []
        self._node_routes[node_name].append(
            {
                "steps": steps,
                "condition": condition,
                "priority": priority,
            }
        )

    def resolve_node(self, node_name: str, ctx) -> list:
        """根据上下文解析节点应执行的步骤列表。

        按优先级降序遍历路由规则，返回第一个条件匹配（或无条件）的 steps。
        如果没有匹配的路由，返回空列表。

        Returns:
            steps 列表，格式同 _execute_node 的 steps 参数
        """
        routes = self._node_routes.get(node_name, [])
        if not routes:
            return []

        # 按优先级降序排列
        for route in sorted(routes, key=lambda r: r["priority"], reverse=True):
            cond = route["condition"]
            if cond is None or cond(ctx):
                return route["steps"]

        return []

    def list_node_routes(self, node_name: str | None = None) -> list[dict]:
        """列出节点路由规则。"""
        if node_name:
            return [
                {
                    "node": node_name,
                    "steps": r["steps"],
                    "priority": r["priority"],
                    "has_condition": r["condition"] is not None,
                }
                for r in self._node_routes.get(node_name, [])
            ]
        result = []
        for n, routes in self._node_routes.items():
            for r in routes:
                result.append(
                    {
                        "node": n,
                        "steps": r["steps"],
                        "priority": r["priority"],
                        "has_condition": r["condition"] is not None,
                    }
                )
        return result
