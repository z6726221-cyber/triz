"""M1 功能建模 Agent Skill：将用户问题拆解为功能模型，输出 Markdown。"""
from triz.agent.skills.base import AgentSkill
from triz.context import WorkflowContext


class M1ModelingSkill(AgentSkill):
    """M1 功能建模 Agent Skill。

    将用户问题拆解为功能模型：
    - SAO 三元组（Subject-Action-Object）
    - 可用资源盘点
    - 理想最终结果（IFR）

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m1_modeling"
    description = "当用户提出工程问题，需要提取功能模型（SAO三元组、资源、IFR）时使用"
    temperature = 0.1

    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行功能建模，返回 Markdown。"""
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
        if "sao" not in output_lower and "三元组" not in output:
            warnings.append("输出中未发现 SAO 三元组相关内容")
        if "ifr" not in output_lower and "理想最终结果" not in output:
            warnings.append("输出中未发现 IFR 相关内容")
        if "资源" not in output:
            warnings.append("输出中未发现资源盘点内容")
        return warnings
