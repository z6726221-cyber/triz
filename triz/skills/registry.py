"""SkillRegistry：自动发现和管理 Agent Skills。"""
import importlib
from pathlib import Path

from triz.skills.base import Skill
from triz.utils.api_client import OpenAIClient


class SkillRegistry:
    """Skill 注册表。

    自动发现 triz/skills/ 下的子文件夹，导入 handler.py 并实例化 Skill。
    """

    def __init__(self, client: OpenAIClient | None = None, tool_registry=None):
        self._skills: dict[str, Skill] = {}
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
