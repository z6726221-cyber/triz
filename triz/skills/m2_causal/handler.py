"""M2 根因分析 Skill：从负面功能出发执行 RCA+因果链分析。"""
from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext, SAO


class M2Input(BaseModel):
    """M2 Skill 输入。"""
    sao_list: list[SAO]


class M2Output(BaseModel):
    """M2 Skill 输出。"""
    root_param: str
    key_problem: str
    candidate_attributes: list[str]
    causal_chain: list[str]


class M2CausalSkill(Skill[M2Input, M2Output]):
    """M2 根因分析 Skill。

    从负面功能出发，执行 RCA+因果链分析，找到根因节点和候选物理属性。
    """

    name = "m2_causal"
    description = "从负面功能出发执行 RCA+因果链分析，找到根因节点和候选物理属性"
    temperature = 0.3
    input_schema = M2Input
    output_schema = M2Output

    def execute(self, input_data: M2Input, ctx: WorkflowContext) -> M2Output:
        """执行根因分析。"""
        system_prompt = self._load_prompt()
        user_prompt = self._build_prompt(input_data)

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        raw = self._parse_json(response)
        return self.validate_output(raw)

    def fallback(self, input_data: M2Input, error: Exception, ctx: WorkflowContext) -> M2Output:
        """降级策略：基于第一个负面 SAO 构造简化结果。"""
        harmful_saos = [s for s in input_data.sao_list if s.function_type in ("harmful", "insufficient")]
        if not harmful_saos:
            harmful_saos = input_data.sao_list

        first = harmful_saos[0]
        root = f"{first.action}导致{first.object}性能下降"
        return M2Output(
            root_param=root,
            key_problem=f"{first.subject}的{first.action}对{first.object}产生负面影响",
            candidate_attributes=["温度", "应力", "磨损"],
            causal_chain=[
                f"Level 0: {first.subject} {first.action} {first.object}",
                f"Level 1: {first.action}造成局部损伤",
                f"Level 2: 损伤累积导致性能下降",
                f"Level 3: {root}",
            ],
        )

    def _build_prompt(self, data: M2Input) -> str:
        """构建 M2 user prompt。"""
        lines = ["功能模型（SAO）："]
        for sao in data.sao_list:
            lines.append(f"  - [{sao.function_type}] {sao.subject} {sao.action} {sao.object}")
        return "\n".join(lines)
