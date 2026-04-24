"""M1 功能建模 Skill：将用户问题拆解为结构化的功能模型。"""
from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext, SAO


class M1Input(BaseModel):
    """M1 Skill 输入。"""
    question: str


class M1Output(BaseModel):
    """M1 Skill 输出。"""
    sao_list: list[SAO]
    resources: dict[str, list[str]]
    ifr: str


class M1ModelingSkill(Skill[M1Input, M1Output]):
    """M1 功能建模 Skill。

    将用户问题拆解为结构化的功能模型：
    - SAO 三元组（Subject-Action-Object）
    - 可用资源盘点
    - 理想最终结果（IFR）
    """

    name = "m1_modeling"
    description = "将用户问题拆解为结构化的功能模型（SAO 三元组、可用资源、理想最终结果）"
    temperature = 0.1
    input_schema = M1Input
    output_schema = M1Output

    def execute(self, input_data: M1Input, ctx: WorkflowContext) -> M1Output:
        """执行功能建模。"""
        system_prompt = self._load_prompt()
        user_prompt = input_data.question

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        raw = self._parse_json(response)
        return self.validate_output(raw)
