"""M6 方案评估 Agent Skill：独立评审方案草案，给出量化评分和理想度，输出 Markdown。"""
from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M6EvaluationSkill(AgentSkill):
    """M6 方案评估 Agent Skill。

    独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m6_evaluation"
    description = "当需要评估方案质量、筛选最优解、决定是否需要迭代改进时使用"
    temperature = 0.3

    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行方案评估，返回 Markdown。"""
        system_prompt = self._load_prompt()

        # 渐进式披露：加载详细评分标准
        rubric = self._load_reference("scoring_rubric.md")
        if rubric:
            system_prompt += "\n\n" + rubric

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
        if "评分" not in output and "score" not in output.lower():
            warnings.append("输出中未发现评分内容")
        if "理想度" not in output and "ideality" not in output.lower():
            warnings.append("输出中未发现理想度相关内容")
        return warnings
