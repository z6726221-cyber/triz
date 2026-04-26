"""Agent Skill 基类：极简设计，输出 Markdown，保留 gotchas/post_validate/渐进式披露。"""
import inspect
import re
from abc import ABC, abstractmethod
from pathlib import Path

from triz_agent.utils.api_client import OpenAIClient
from triz_agent.context import WorkflowContext

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class AgentSkill(ABC):
    """Agent 模式 Skill 基类。

    与 Orchestrator Skill 的区别：
    - execute() 返回 Markdown 字符串（而非 Pydantic 模型）
    - 不需要 JSON 解析、Pydantic 校验
    - Agent 负责数据流转，Skill 只管输出内容
    - 保留 gotchas、post_validate、渐进式披露
    """

    name: str = ""
    description: str = ""
    temperature: float = 0.3

    def __init__(self, client: OpenAIClient):
        self.client = client
        self._gotchas_cache: list[str] | None = None
        self._retry_hints: list[str] | None = None

    @abstractmethod
    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行 Skill，返回 Markdown。

        Args:
            ctx: 工作流上下文（含 question 等基本信息）
            context_markdown: Agent 传入的上游分析结果（Markdown）
        """
        pass

    def post_validate(self, output: str, ctx: WorkflowContext) -> list[str]:
        """业务逻辑校验，返回警告列表。子类可覆盖。"""
        return []

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM，返回文本。"""
        return self.client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=self.temperature,
        )

    def _load_prompt(self) -> str:
        """从 SKILL.md 加载 prompt，跳过 YAML frontmatter。"""
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
        prompt = content[match.end():].strip() if match else content

        if self._retry_hints:
            prompt += "\n\n## 校验警告（上次执行的问题，请特别注意）\n"
            for hint in self._retry_hints:
                prompt += f"- {hint}\n"
            self._retry_hints = None

        return prompt

    def _load_reference(self, filename: str) -> str:
        """加载 references/ 目录下的参考文件（渐进式披露）。"""
        try:
            handler_file = inspect.getfile(type(self))
        except TypeError:
            handler_file = __file__

        skill_dir = Path(handler_file).parent
        ref_file = skill_dir / "references" / filename

        if not ref_file.exists():
            return ""

        return ref_file.read_text(encoding="utf-8")

    @property
    def gotchas(self) -> list[str]:
        """从 SKILL.md frontmatter 解析 gotchas 摘要。"""
        if self._gotchas_cache is None:
            self._gotchas_cache = self._parse_gotchas()
        return self._gotchas_cache

    def _parse_gotchas(self) -> list[str]:
        """解析 SKILL.md frontmatter 中的 gotchas 列表。"""
        try:
            handler_file = inspect.getfile(type(self))
        except TypeError:
            handler_file = __file__

        skill_dir = Path(handler_file).parent
        skill_md = skill_dir / "SKILL.md"

        if not skill_md.exists():
            return []

        content = skill_md.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(content)
        if not match:
            return []

        frontmatter = match.group(1)
        in_gotchas = False
        gotchas = []
        for line in frontmatter.split("\n"):
            stripped = line.strip()
            if stripped.startswith("gotchas:"):
                in_gotchas = True
                continue
            if in_gotchas:
                if stripped.startswith("- "):
                    gotchas.append(stripped[2:].strip())
                elif stripped and not stripped.startswith("#"):
                    break
        return gotchas
