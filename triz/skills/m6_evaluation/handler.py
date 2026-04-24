"""M6 方案评估 Skill：独立评审方案草案，给出量化评分和理想度。"""
from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext, SolutionDraft


class M6Input(BaseModel):
    """M6 Skill 输入。"""
    question: str
    solution_drafts: list[SolutionDraft]
    ifr: str
    contradiction_desc: str


class M6Output(BaseModel):
    """M6 Skill 输出。"""
    ranked_solutions: list[dict]
    max_ideality: float
    unresolved_signals: list[str]


class M6EvaluationSkill(Skill[M6Input, M6Output]):
    """M6 方案评估 Skill。

    独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序。
    """

    name = "m6_evaluation"
    description = "独立评审方案草案，给出 8 维度量化评分和理想度"
    temperature = 0.3
    input_schema = M6Input
    output_schema = M6Output

    def execute(self, input_data: M6Input, ctx: WorkflowContext) -> M6Output:
        """执行方案评估。"""
        system_prompt = self._load_prompt()
        user_prompt = self._build_prompt(input_data)

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        raw = self._parse_json(response)
        return self.validate_output(raw)

    def _build_prompt(self, data: M6Input) -> str:
        """构建 M6 user prompt。"""
        lines = [
            f"用户原始问题：{data.question}",
            f"矛盾描述：{data.contradiction_desc}",
            f"理想最终结果：{data.ifr}",
            "",
            "待评估方案：",
        ]
        for i, draft in enumerate(data.solution_drafts, 1):
            lines.append(f"\n方案 {i}:")
            lines.append(f"  标题：{draft.title}")
            lines.append(f"  描述：{draft.description}")
            lines.append(f"  应用原理：{draft.applied_principles}")
            lines.append(f"  资源映射：{draft.resource_mapping}")
        return "\n".join(lines)
