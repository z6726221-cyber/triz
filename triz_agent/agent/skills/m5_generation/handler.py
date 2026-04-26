"""M5 方案生成 Agent Skill：搜索跨领域案例并生成具体方案，输出 Markdown。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M5GenerationSkill(AgentSkill):
    """M5 方案生成 Agent Skill。

    将抽象的发明原理和跨界案例迁移到用户的具体场景，生成具体可执行的方案草稿。
    负责：生成搜索词 → 过滤结果 → 提取模式 → 生成方案。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m5_generation"
    description = "当已获得发明原理，需要搜索跨领域案例并生成具体方案时使用"
    temperature = 0.4

    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行方案生成，返回 Markdown。"""
        system_prompt = self._load_prompt()

        # 渐进式披露：加载详细生成指南
        guide = self._load_reference("generation_guide.md")
        if guide:
            system_prompt += "\n\n" + guide

        user_parts = [f"用户问题：{ctx.question}"]
        if context_markdown:
            user_parts.append(f"\n之前的分析结果：\n{context_markdown}")
        user_prompt = "\n".join(user_parts)

        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    def post_validate(self, output: str, ctx: WorkflowContext) -> list[str]:
        warnings = []
        if "方案" not in output and "solution" not in output.lower():
            warnings.append("输出中未发现方案内容")
        if "原理" not in output and "principle" not in output.lower():
            warnings.append("输出中未引用发明原理")
        return warnings
