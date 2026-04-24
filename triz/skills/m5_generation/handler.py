"""M5 方案生成 Skill：基于发明原理生成解决方案草案。"""
from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext, SolutionDraft, Case


class M5Input(BaseModel):
    """M5 Skill 输入。"""
    question: str
    principles: list[int]
    cases: list[Case]
    contradiction_desc: str
    ifr: str
    resources: dict[str, list[str]]
    feedback: str = ""


class M5Output(BaseModel):
    """M5 Skill 输出。"""
    solution_drafts: list[SolutionDraft]


class M5GenerationSkill(Skill[M5Input, M5Output]):
    """M5 方案生成 Skill。

    将抽象的发明原理和跨界案例迁移到用户具体场景，生成可执行的方案草稿。
    """

    name = "m5_generation"
    description = "基于发明原理和跨界案例生成具体可执行的解决方案草案"
    temperature = 0.4
    input_schema = M5Input
    output_schema = M5Output

    def execute(self, input_data: M5Input, ctx: WorkflowContext) -> M5Output:
        """执行方案生成。"""
        system_prompt = self._load_prompt()
        user_prompt = self._build_prompt(input_data)

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
        )

        raw = self._parse_json(response)

        # M5 特有格式校验：必须包含 solution_drafts
        if "solution_drafts" not in raw:
            raw = self._retry_for_format(system_prompt, user_prompt)

        return self.validate_output(raw)

    def fallback(self, input_data: M5Input, error: Exception, ctx: WorkflowContext) -> M5Output:
        """降级策略：基于 principles 生成简化方案。"""
        if not input_data.principles:
            return M5Output(solution_drafts=[])

        drafts = []
        for principle_id in input_data.principles[:3]:
            related_cases = [c for c in input_data.cases if c.principle_id == principle_id]
            case_desc = related_cases[0].description if related_cases else "参考类似工程问题的解决方案"

            draft = SolutionDraft(
                title=f"基于原理{principle_id}的改进方案",
                description=(
                    f"针对用户问题「{input_data.question}」，应用发明原理{principle_id}进行改进。"
                    f"参考案例：{case_desc}。建议将该原理的核心思想迁移到当前场景："
                    f"分析现有系统的组件和资源，寻找可以引入该原理作用机制的切入点。"
                    f"预期通过此改进，可以在保持原有功能的前提下，缓解或消除当前矛盾。"
                ),
                applied_principles=[principle_id],
                resource_mapping="利用现有系统组件和资源",
            )
            drafts.append(draft)

        return M5Output(solution_drafts=drafts)

    def _build_prompt(self, data: M5Input) -> str:
        """构建 M5 user prompt。"""
        lines = [
            f"问题：{data.question}",
            f"矛盾描述：{data.contradiction_desc}",
            f"理想最终结果：{data.ifr}",
            f"发明原理：{data.principles}",
        ]

        if data.cases:
            lines.append("跨界案例：")
            for case in data.cases:
                lines.append(f"  - [{case.source}] {case.title}: {case.description}")

        if data.resources:
            lines.append(f"可用资源：{data.resources}")

        if data.feedback:
            lines.append(f"上一轮反馈：{data.feedback}")

        return "\n".join(lines)

    def _retry_for_format(self, system_prompt: str, user_prompt: str) -> dict:
        """格式错误时重试一次，追加格式纠正提示。"""
        retry_prompt = (
            user_prompt + "\n\n"
            "【格式纠正】你的输出格式不正确。请输出一个包含 'solution_drafts' 字段的 JSON 对象，"
            '如：{"solution_drafts": [{"title": "...", "description": "..."}]}。'
            "不要输出数组或其他格式。只输出纯 JSON。"
        )

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=retry_prompt,
            json_mode=True,
        )

        return self._parse_json(response)
