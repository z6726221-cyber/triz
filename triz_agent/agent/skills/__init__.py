"""Agent 模式 Skills：输出 Markdown，由 Agent 自主理解并管理数据流转。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.agent.skills.registry import AgentSkillRegistry

__all__ = ["AgentSkill", "AgentSkillRegistry"]
