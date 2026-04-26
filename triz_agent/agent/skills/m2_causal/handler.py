"""M2 根因分析 Agent Skill：从负面功能出发执行 RCA+因果链分析，输出 Markdown。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M2CausalSkill(AgentSkill):
    """M2 根因分析 Agent Skill。

    从负面功能出发，执行 RCA+因果链分析，找到根因节点和候选物理属性。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m2_causal"
    description = "当存在负面功能（harmful/excessive/insufficient）需要追溯根因时使用"
    temperature = 0.3

    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行根因分析，返回 Markdown。"""
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
        if "因果链" not in output and "causal" not in output.lower():
            warnings.append("输出中未发现因果链内容")
        if "根因" not in output and "root" not in output.lower():
            warnings.append("输出中未发现根因分析内容")
        return warnings
