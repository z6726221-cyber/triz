"""M2 根因分析 Agent Skill：从负面功能出发执行 RCA+因果链分析，输出 Markdown。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M2CausalSkill(AgentSkill):
    """M2 根因分析 Agent Skill。

    从负面功能出发，执行 RCA+因果链分析，找到根因节点和候选物理属性。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m2_causal"
    description = """当 M1 功能建模已完成，存在负面功能（harmful/excessive/insufficient）时，需要：
- 执行 RCA 根因分析
- 构建因果链
- 识别根因节点和候选物理属性
适用场景：功能模型已建立，需要追溯问题根源时。"""
    temperature = 0.3

    def post_validate(self, output: str, ctx: WorkflowContext) -> list[str]:
        warnings = []
        if "因果链" not in output and "causal" not in output.lower():
            warnings.append("输出中未发现因果链内容")
        if "根因" not in output and "root" not in output.lower():
            warnings.append("输出中未发现根因分析内容")
        return warnings
