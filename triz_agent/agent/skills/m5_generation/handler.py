"""M5 方案生成 Agent Skill：搜索跨领域案例并生成具体方案，输出 Markdown。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M5GenerationSkill(AgentSkill):
    """M5 方案生成 Agent Skill。

    将抽象的发明原理和跨界案例迁移到用户的具体场景，生成具体可执行的方案草稿。

    负责：生成搜索词 → 过滤结果 → 提取模式 → 生成方案。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "generation"
    description = """当 M3/M4 已完成，获得发明原理后，需要：
- 生成跨领域搜索词
- 查询外部案例库（Google Patents 等）
- 将发明原理迁移到用户具体场景
- 生成具体可执行的方案草稿
适用场景：已有矛盾分析和发明原理，需要生成具体解决方案时。"""
    temperature = 0.4

    def _load_extra_references(self) -> str:
        """加载详细生成指南。"""
        return self._load_reference("generation_guide.md") or ""

    # post_validate 由 base.py 自动调用 scripts/validate_output.py
    # 如需额外校验，在此补充或覆盖 post_validate 方法
