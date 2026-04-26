"""M1 功能建模 Agent Skill：将用户问题拆解为功能模型，输出 Markdown。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M1ModelingSkill(AgentSkill):
    """M1 功能建模 Agent Skill。

    将用户问题拆解为功能模型：
    - SAO 三元组（Subject-Action-Object）
    - 可用资源盘点
    - 理想最终结果（IFR）

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m1_modeling"
    description = """当用户提出工程问题，需要：
- 拆解功能模型（对象、动作、属性）
- 提取 SAO 三元组
- 盘点可用资源
- 定义理想最终结果（IFR）
适用场景：新工程问题首次分析，或需要重新建模时。"""
    temperature = 0.1

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
