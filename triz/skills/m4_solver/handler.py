"""M4 矛盾求解 Skill：查询 TRIZ 矛盾矩阵或分离原理，返回发明原理。"""
import json
from typing import Literal

from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext


class M4Input(BaseModel):
    """M4 Skill 输入。"""
    problem_type: Literal["tech", "phys"]
    improve_aspect: str | None = None
    worsen_aspect: str | None = None
    contradiction_desc: str = ""
    candidate_attributes: list[str] = []


class M4Output(BaseModel):
    """M4 Skill 输出。"""
    principles: list[int]
    improve_param_id: int | None = None
    worsen_param_id: int | None = None
    match_conf: float = 0.0
    sep_type: str | None = None
    need_state: str | None = None
    need_not_state: str | None = None


class M4SolverSkill(Skill[M4Input, M4Output]):
    """M4 矛盾求解 Skill。

    根据矛盾类型调用 Tools 查询：
    - 技术矛盾：map_to_parameters → query_matrix
    - 物理矛盾：query_separation
    """

    name = "m4_solver"
    description = "查询 TRIZ 矛盾矩阵或分离原理，返回发明原理"
    temperature = 0.3
    require_tool_calls = True
    input_schema = M4Input
    output_schema = M4Output

    MAX_ROUNDS = 5

    def execute(self, input_data: M4Input, ctx: WorkflowContext) -> M4Output:
        """执行矛盾求解，内部管理多轮 tool calling。"""
        system_prompt = self._load_prompt()
        user_prompt = self._build_prompt(input_data)

        # 获取可用 tools
        tools = []
        tool_registry = getattr(self, "tool_registry", None)
        if tool_registry:
            tools = tool_registry.get_schemas()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        forced_retry = False
        for _ in range(self.MAX_ROUNDS):
            response = self._call_llm_with_tools(
                messages=messages,
                tools=tools,
            )

            message = response.choices[0].message

            if message.tool_calls:
                # 添加 assistant 的 tool_call 请求
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # 执行每个 tool call
                if tool_registry:
                    for tc in message.tool_calls:
                        name = tc.function.name
                        args = json.loads(tc.function.arguments)
                        result = tool_registry.execute(name, args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        })
            else:
                # LLM 返回最终结果
                # 如果要求必须调用 tools 且尚未调用过，强制重试一次
                if self.require_tool_calls and not forced_retry and tools:
                    forced_retry = True
                    messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                    })

                    has_tool_results = any(m.get("role") == "tool" for m in messages)
                    if has_tool_results:
                        messages.append({
                            "role": "user",
                            "content": (
                                "你已经调用了工具并获取了结果。请直接基于上述工具返回的数据，"
                                "输出最终 JSON 结果，不要再重新调用工具。"
                                "只输出纯 JSON，不要添加任何文字说明。"
                            ),
                        })
                    else:
                        messages.append({
                            "role": "user",
                            "content": (
                                "你还没有调用任何工具来查询数据库。"
                                "请根据工作流程调用必要的 Tools（map_to_parameters、query_matrix、query_separation），"
                                "获取准确的发明原理后再输出最终结果。"
                            ),
                        })
                    continue

                raw = self._parse_json(message.content)
                return self.validate_output(raw)

        raise RuntimeError(f"M4 Solver 执行超过最大轮数 {self.MAX_ROUNDS}")

    def fallback(self, input_data: M4Input, error: Exception, ctx: WorkflowContext) -> M4Output:
        """降级策略：基于候选属性直接查询参数和矩阵。"""
        from triz.tools.query_parameters import query_parameters
        from triz.tools.query_matrix import query_matrix

        keywords = input_data.candidate_attributes or []
        if not keywords and input_data.contradiction_desc:
            keywords = [input_data.contradiction_desc[:20]]
        if not keywords:
            return M4Output(principles=[], match_conf=0.0)

        params = query_parameters(keywords)
        if len(params) >= 2:
            principles = query_matrix(params[0]["id"], params[1]["id"])
            return M4Output(
                principles=principles,
                improve_param_id=params[0]["id"],
                worsen_param_id=params[1]["id"],
                match_conf=0.5,
            )
        elif len(params) == 1:
            principles = query_matrix(params[0]["id"], 39)
            return M4Output(
                principles=principles,
                improve_param_id=params[0]["id"],
                worsen_param_id=39,
                match_conf=0.5,
            )

        return M4Output(principles=[], match_conf=0.0)

    def _build_prompt(self, data: M4Input) -> str:
        """构建 M4 user prompt。"""
        lines = [
            f"矛盾类型：{data.problem_type}",
            f"矛盾描述：{data.contradiction_desc}",
        ]
        if data.improve_aspect:
            lines.append(f"改善方面：{data.improve_aspect}")
        if data.worsen_aspect:
            lines.append(f"恶化方面：{data.worsen_aspect}")
        return "\n".join(lines)
