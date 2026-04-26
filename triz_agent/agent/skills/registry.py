"""AgentSkillRegistry：自动发现和管理 Agent 模式的 Skills。"""

import importlib
from pathlib import Path

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.utils.api_client import OpenAIClient
from triz_agent.config import (
    MODEL_NAME,
    MODEL_M1,
    MODEL_M2,
    MODEL_M3,
    MODEL_M5,
    MODEL_M6,
)

_SKILL_MODEL_MAP = {
    "m1_modeling": MODEL_M1,
    "m2_causal": MODEL_M2,
    "m3_formulation": MODEL_M3,
    "m5_generation": MODEL_M5,
    "m6_evaluation": MODEL_M6,
}


class AgentSkillRegistry:
    """Agent 模式 Skill 注册表。

    自动发现 triz/agent/skills/ 下的子文件夹，导入 handler.py 并实例化 AgentSkill。
    """

    def __init__(self):
        self._skills: dict[str, AgentSkill] = {}
        self._discover()

    def _discover(self):
        """遍历 agent/skills/ 子文件夹，自动发现并注册 AgentSkill。"""
        skills_path = Path(__file__).parent

        for item in skills_path.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue

            handler_file = item / "handler.py"
            if not handler_file.exists():
                continue

            module_name = f"triz_agent.agent.skills.{item.name}.handler"
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, AgentSkill)
                    and attr is not AgentSkill
                    and getattr(attr, "name", None)
                ):
                    skill_model = _SKILL_MODEL_MAP.get(attr.name)
                    if skill_model and skill_model != MODEL_NAME:
                        client = OpenAIClient(model=skill_model)
                    else:
                        client = OpenAIClient()

                    skill_instance = attr(client=client)
                    self._skills[attr.name] = skill_instance

    def get(self, name: str) -> AgentSkill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "gotchas": s.gotchas,
            }
            for s in self._skills.values()
        ]
