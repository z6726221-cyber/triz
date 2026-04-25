"""M3 问题定型 Agent Skill：将根因分析转化为标准化矛盾表述，输出 Markdown。"""
from triz.agent.skills.base import AgentSkill
from triz.context import WorkflowContext


class M3FormulationSkill(AgentSkill):
    """M3 问题定型 Agent Skill。

    基于根因分析结果，提取标准化的 TRIZ 矛盾对（技术矛盾或物理矛盾）。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m3_formulation"
    description = "当需要将根因分析结果转化为标准化矛盾表述（技术矛盾/物理矛盾）时使用"
    temperature = 0.1

    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行问题定型，返回 Markdown。"""
        system_prompt = self._load_prompt()

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
        output_lower = output.lower()
        if "技术矛盾" not in output and "物理矛盾" not in output:
            if "tech" not in output_lower and "phys" not in output_lower:
                warnings.append("输出中未明确矛盾类型（技术矛盾/物理矛盾）")
        if "改善" not in output and "improve" not in output_lower:
            warnings.append("输出中未发现改善方面")
        if "恶化" not in output and "worsen" not in output_lower:
            warnings.append("输出中未发现恶化方面")
        return warnings
