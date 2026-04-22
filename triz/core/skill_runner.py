"""Skill Runner：读取 .md Skill 文件，调用 LLM 执行，支持 Function Calling。"""
import json
import re
from pathlib import Path
from triz.context import WorkflowContext
from triz.utils.api_client import OpenAIClient
from triz.core.tool_registry import ToolRegistry


class SkillRunner:
    """Skill 执行器。

    执行流程：
    1. 读取 skills/{skill_name}.md 作为 system prompt
    2. 将 WorkflowContext 序列化为 user prompt
    3. 调用 LLM with available tools
    4. 如果 LLM 返回 tool_calls，执行 Tools 并将结果返回给 LLM
    5. 重复直到 LLM 返回最终结果（无 tool_calls）
    6. 解析最终 JSON 输出
    """

    MAX_ROUNDS = 8

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.client = OpenAIClient()

    def _get_skill_path(self, skill_name: str) -> Path:
        """获取 Skill 文件路径。"""
        return Path(__file__).parent.parent / "skills" / f"{skill_name}.md"

    def run(self, skill_name: str, ctx: WorkflowContext,
            require_tool_calls: bool = False, model: str = None) -> dict:
        """执行指定 Skill，返回解析后的 dict。

        Args:
            skill_name: Skill 文件名（不含 .md）
            ctx: WorkflowContext
            require_tool_calls: 如果为 True，当 LLM 未调用任何 tool 直接返回结果时，
                               会自动追加提示要求调用 tool 并重试一次
            model: 临时指定模型名称（如 M5 用 DeepSeek，M6 用 Kimi）
        """
        skill_path = self._get_skill_path(skill_name)
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill 文件不存在: {skill_path}")

        system_prompt = skill_path.read_text(encoding="utf-8")
        user_prompt = self._build_context_prompt(ctx)
        tools = self.tool_registry.get_schemas()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        forced_retry = False
        for round_idx in range(self.MAX_ROUNDS):
            response = self.client.chat_with_tools(
                messages=messages,
                tools=tools,
                temperature=0.3,
                model=model,
            )

            message = response.choices[0].message

            if message.tool_calls:
                # 添加 assistant 的 tool_call 请求到 messages
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content or "",
                }
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
                messages.append(assistant_msg)

                # 执行每个 tool call，添加结果到 messages
                for tc in message.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    result = self.tool_registry.execute(name, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
            else:
                # LLM 返回最终结果
                # 如果要求必须调用 tools 且尚未调用过，强制重试一次
                if require_tool_calls and not forced_retry and tools:
                    forced_retry = True
                    messages.append({
                        "role": "assistant",
                        "content": message.content or "",
                    })
                    messages.append({
                        "role": "user",
                        "content": (
                            "你还没有调用任何工具来查询数据库。"
                            "请根据工作流程调用必要的 Tools（query_parameters、query_matrix、query_separation），"
                            "获取准确的发明原理后再输出最终结果。"
                        ),
                    })
                    continue

                return self._parse_result(message.content)

        raise RuntimeError(f"Skill '{skill_name}' 执行超过最大轮数 {self.MAX_ROUNDS}")

    def _build_context_prompt(self, ctx: WorkflowContext) -> str:
        """将 WorkflowContext 序列化为 JSON prompt。"""
        return json.dumps(ctx.model_dump(), ensure_ascii=False, indent=2)

    def _parse_result(self, content: str | None) -> dict:
        """解析 LLM 返回的 JSON。支持 dict 和 list（list 会被包装为 {'result': list}）。"""
        if not content:
            return {}
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return {"result": data}
            return data
        except json.JSONDecodeError:
            pass

        # 从文本中扫描提取 JSON（避免递归，防止无限循环）
        decoder = json.JSONDecoder()
        for i, char in enumerate(content):
            if char in "{[":
                try:
                    data, _ = decoder.raw_decode(content, i)
                    if isinstance(data, list):
                        return {"result": data}
                    return data
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"无法解析 LLM 输出: {content[:200]}")
