"""M3 问题定型 Skill：提取标准化的 TRIZ 矛盾对。"""
from typing import Literal

from pydantic import BaseModel

from triz_pipeline.skills.base import Skill
from triz_pipeline.context import WorkflowContext


class M3Input(BaseModel):
    """M3 Skill 输入。"""
    root_param: str
    key_problem: str
    candidate_attributes: list[str]


class M3Output(BaseModel):
    """M3 Skill 输出。"""
    problem_type: Literal["tech", "phys"]
    improve_aspect: str
    worsen_aspect: str
    contradiction_desc: str = ""
    evidence: list[str] = []


class M3FormulationSkill(Skill[M3Input, M3Output]):
    """M3 问题定型 Skill。

    基于根因分析结果，提取标准化的 TRIZ 矛盾对（技术矛盾或物理矛盾）。
    """

    name = "m3_formulation"
    description = "当需要将根因分析结果转化为标准化矛盾表述（技术矛盾/物理矛盾）时使用"
    temperature = 0.1
    input_schema = M3Input
    output_schema = M3Output

    def execute(self, input_data: M3Input, ctx: WorkflowContext) -> M3Output:
        """执行问题定型。"""
        system_prompt = self._load_prompt()
        user_prompt = self._build_prompt(input_data)

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        raw = self._parse_json(response)

        # 自动构建 contradiction_desc 和 evidence
        if not raw.get("contradiction_desc"):
            raw["contradiction_desc"] = (
                f"改善{raw.get('improve_aspect', '')}导致{raw.get('worsen_aspect', '')}恶化"
            )
        if not raw.get("evidence"):
            raw["evidence"] = [input_data.root_param, input_data.key_problem]

        return self.validate_output(raw)

    def post_validate(self, output: M3Output, ctx: WorkflowContext) -> list[str]:
        warnings = []
        if output.problem_type not in ("tech", "phys"):
            warnings.append(f"problem_type 非法: {output.problem_type}，应为 tech 或 phys")
        if len(output.improve_aspect) < 2 or len(output.improve_aspect) > 20:
            warnings.append(f"improve_aspect 长度异常: {len(output.improve_aspect)} 字符")
        if len(output.worsen_aspect) < 2 or len(output.worsen_aspect) > 20:
            warnings.append(f"worsen_aspect 长度异常: {len(output.worsen_aspect)} 字符")
        return warnings

    def _build_prompt(self, data: M3Input) -> str:
        """构建 M3 user prompt。"""
        lines = [
            f"根因参数：{data.root_param}",
            f"关键问题：{data.key_problem}",
        ]
        if data.candidate_attributes:
            lines.append(f"候选属性：{', '.join(data.candidate_attributes)}")
        return "\n".join(lines)
