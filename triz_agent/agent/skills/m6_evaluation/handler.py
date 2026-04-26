"""M6 方案评估 Agent Skill：独立评审方案草案，给出量化评分和理想度，输出 Markdown。"""

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M6EvaluationSkill(AgentSkill):
    """M6 方案评估 Agent Skill。

    独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m6_evaluation"
    description = """当 M5 已生成方案草案后，需要：
- 独立评审每个方案的 8 维度量化评分
- 计算理想度（Ideality）
- 按理想度排序，给出推荐方案
- 决定是否需要迭代改进
适用场景：多个方案需要评估筛选，或判断当前方案是否足够好时。"""
    temperature = 0.3

    def _load_extra_references(self) -> str:
        """加载详细评分标准。"""
        return self._load_reference("scoring_rubric.md") or ""

    def post_validate(self, output: str, ctx: WorkflowContext) -> list[str]:
        warnings = []
        if "评分" not in output and "score" not in output.lower():
            warnings.append("输出中未发现评分内容")
        if "理想度" not in output and "ideality" not in output.lower():
            warnings.append("输出中未发现理想度相关内容")
        return warnings
