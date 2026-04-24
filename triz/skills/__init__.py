"""TRIZ Agent Skills 包。

每个 Skill 是一个自包含的能力单元，包含：
- SKILL.md: Skill 定义 / system prompt
- handler.py: Python 执行器（输入验证、LLM 调用、输出解析、fallback）
"""
from triz.skills.base import Skill
from triz.skills.registry import SkillRegistry

__all__ = ["Skill", "SkillRegistry"]
