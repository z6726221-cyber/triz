"""Skill 基类：定义真正的 Agent Skill 接口。"""
import inspect
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar, Generic, Type

# 匹配 YAML frontmatter: ---\n...\n---\n
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

from pydantic import BaseModel

from triz.utils.api_client import OpenAIClient
from triz.context import WorkflowContext

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Skill(ABC, Generic[InputT, OutputT]):
    """真正的 Agent Skill：自包含的能力单元。

    每个 Skill 子类需要定义：
    - name: Skill 名称
    - description: Skill 描述
    - input_schema: 输入 Pydantic 模型
    - output_schema: 输出 Pydantic 模型
    - execute(): 核心执行逻辑
    """

    name: str = ""
    description: str = ""
    version: str = "1.0"

    # LLM 配置（子类可覆盖）
    temperature: float = 0.3
    model: str | None = None

    # 执行配置
    max_retries: int = 1
    require_tool_calls: bool = False

    # Schema 定义（子类必须覆盖）
    input_schema: Type[InputT]
    output_schema: Type[OutputT]

    def __init__(self, client: OpenAIClient | None = None, **kwargs):
        self.client = client or OpenAIClient()
        for k, v in kwargs.items():
            setattr(self, k, v)

    @abstractmethod
    def execute(self, input_data: InputT, ctx: WorkflowContext) -> OutputT:
        """执行 Skill，返回结构化输出。

        Args:
            input_data: 经过验证的输入数据
            ctx: 工作流上下文（用于读取历史状态）

        Returns:
            经过验证的输出数据
        """
        pass

    def validate_output(self, raw: dict) -> OutputT:
        """使用 Pydantic 验证并解析输出。"""
        return self.output_schema.model_validate(raw)

    def fallback(self, input_data: InputT, error: Exception, ctx: WorkflowContext) -> OutputT | None:
        """失败时的降级策略。子类可覆盖。

        Returns:
            降级后的输出，或 None（表示无法降级）
        """
        return None

    def _load_prompt(self) -> str:
        """从子类 handler.py 同级目录加载 SKILL.md，自动跳过 YAML frontmatter。"""
        try:
            handler_file = inspect.getfile(type(self))
        except TypeError:
            handler_file = __file__

        skill_dir = Path(handler_file).parent
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            raise FileNotFoundError(f"Skill 定义文件不存在: {skill_md}")

        content = skill_md.read_text(encoding="utf-8")

        match = _FRONTMATTER_RE.match(content)
        if match:
            return content[match.end():].strip()

        return content

    def _call_llm(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """通用 LLM 调用。"""
        return self.client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
            json_mode=json_mode,
        )

    def _call_llm_with_tools(
        self,
        messages: list,
        tools: list,
        temperature: float | None = None,
    ):
        """带 tool calling 的 LLM 调用，返回原始 response 对象。

        调用方需要检查 response.choices[0].message.tool_calls 决定下一步。
        """
        return self.client.chat_with_tools(
            messages=messages,
            tools=tools,
            temperature=temperature or self.temperature,
            model=self.model,
        )

    def _parse_json(self, content: str | None) -> dict:
        """解析 LLM 返回的 JSON。

        支持：
        - 纯 JSON 对象/数组
        - Markdown 代码块包裹的 JSON
        - 文本中嵌套的 JSON
        - 数组会被包装为 {'result': list}
        """
        if not content:
            return {}

        # 尝试直接解析
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return {"result": data}
            return data
        except json.JSONDecodeError:
            pass

        # 从 Markdown 代码块提取
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if code_block_match:
            try:
                data = json.loads(code_block_match.group(1))
                if isinstance(data, list):
                    return {"result": data}
                return data
            except json.JSONDecodeError:
                pass

        # 从文本中扫描 JSON（避免递归）
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

    def _build_context_prompt(self, ctx: WorkflowContext) -> str:
        """将 WorkflowContext 序列化为 JSON prompt（供 Skill 内部使用）。"""
        return json.dumps(ctx.model_dump(), ensure_ascii=False, indent=2)
