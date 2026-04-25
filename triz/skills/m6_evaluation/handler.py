"""M6 方案评估 Skill：独立评审方案草案，给出量化评分和理想度。"""
from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext, SolutionDraft
from triz.skills.m6_evaluation.scripts.calculate_ideality import recalculate_all


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
    description = "当需要评估方案质量、筛选最优解、决定是否需要迭代改进时使用"
    temperature = 0.3
    input_schema = M6Input
    output_schema = M6Output

    def execute(self, input_data: M6Input, ctx: WorkflowContext) -> M6Output:
        """执行方案评估。"""
        system_prompt = self._load_prompt()

        # 渐进式披露：加载详细评分标准
        rubric = self._load_reference("scoring_rubric.md")
        if rubric:
            system_prompt += "\n\n" + rubric

        user_prompt = self._build_prompt(input_data)

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        raw = self._parse_json(response)

        # 脚本后处理：重新计算理想度并排序（确定性计算，不信任 LLM）
        if "ranked_solutions" in raw and raw["ranked_solutions"]:
            raw["ranked_solutions"] = recalculate_all(raw["ranked_solutions"])
            raw["max_ideality"] = raw["ranked_solutions"][0].get("ideality_score", 0)

        return self.validate_output(raw)

    def post_validate(self, output: M6Output, ctx: WorkflowContext) -> list[str]:
        warnings = []
        if not output.ranked_solutions:
            warnings.append("评估结果为空")
            return warnings
        # 检查评分区分度
        ideality_scores = [s.get("ideality_score", 0) for s in output.ranked_solutions]
        if len(set(ideality_scores)) == 1 and len(ideality_scores) > 1:
            warnings.append("所有方案理想度相同，评分缺乏区分度")
        # 检查 relevance 分布
        relevance_scores = [s.get("problem_relevance_score", 3) for s in output.ranked_solutions]
        if all(r >= 4 for r in relevance_scores) and ctx.question:
            # 如果所有方案都高分，检查是否是非工程问题
            non_engineering_keywords = ["天气", "追女", "等于几", "亿万富翁", "怎么样"]
            if any(kw in ctx.question for kw in non_engineering_keywords):
                warnings.append("非工程问题但所有方案 relevance 偏高，应 ≤ 2")
        return warnings

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
