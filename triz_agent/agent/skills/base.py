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

    def execute(self, ctx: WorkflowContext, context_markdown: str = "") -> str:
        """执行 Skill，返回 Markdown。

        Args:
            ctx: 工作流上下文（含 question 等基本信息）
            context_markdown: Agent 传入的上游分析结果（Markdown）

        基类提供默认实现，子类一般无需覆盖。
        如需自定义，可覆盖 _build_user_prompt() 或整个 execute()。
        """
        system_prompt = self._load_prompt()

        # 允许子类注入额外的 reference 内容
        extra = self._load_extra_references()
        if extra:
            system_prompt += "\n\n" + extra

        user_prompt = self._build_user_prompt(ctx, context_markdown)
        return self._call_llm(system_prompt=system_prompt, user_prompt=user_prompt)

    def _build_user_prompt(self, ctx: WorkflowContext, context_markdown: str) -> str:
        """构建 user prompt。子类可覆盖以自定义。"""
        parts = [f"用户问题：{ctx.question}"]
        if context_markdown:
            parts.append(f"\n之前的分析结果：\n{context_markdown}")
        return "\n".join(parts)

    def _load_extra_references(self) -> str:
        """加载额外的参考文档，拼接到 system_prompt。子类可覆盖。

        默认返回空字符串，references/ 内容由 SKILL.md 指示 LLM 按需用 Read 工具读取，
        符合渐进式披露原则，避免无条件加载增加 token 开销。
        """
        return ""

    def post_validate(self, output: str, ctx: WorkflowContext) -> list[str]:
        """业务逻辑校验，返回警告列表。

        优先调用 scripts/validate_output.py 脚本（如果存在），
        以确定性代码校验输出；子类也可覆盖此方法。
        """
        # 优先尝试脚本化校验
        script_warnings = self._call_validate_script(output, ctx)
        if script_warnings is not None:
            return script_warnings
        # 子类覆盖
        return []

    def _call_validate_script(self, output: str, ctx: WorkflowContext) -> list[str] | None:
        """调用 scripts/validate_output.py，返回警告列表或 None。"""
        try:
            import sys
            from pathlib import Path
            handler_file = None
            try:
                handler_file = inspect.getfile(type(self))
            except TypeError:
                handler_file = __file__
            script_dir = Path(handler_file).parent / "scripts"
            validate_script = script_dir / "validate_output.py"
            if not validate_script.exists():
                return None
            sys.path.insert(0, str(script_dir))
            from validate_output import validate
            return validate(output, ctx)
        except Exception:
            return None

    def post_process(self, output: str) -> dict | None:
        """Skill 输出后自动解析，返回结构化数据。子类可覆盖。

        基类默认返回 None，表示不做结构化解析。
        """
        return None

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
        prompt = content[match.end() :].strip() if match else content

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

    @property
    def allowed_tools(self) -> list[str]:
        """从 SKILL.md frontmatter 解析 allowed-tools 列表。"""
        return self._parse_allowed_tools()

    def _parse_allowed_tools(self) -> list[str]:
        """解析 SKILL.md frontmatter 中的 allowed-tools 列表。"""
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
        in_allowed = False
        tools = []
        for line in frontmatter.split("\n"):
            stripped = line.strip()
            if stripped.startswith("allowed-tools:"):
                in_allowed = True
                # 同行格式：allowed-tools: ["Bash", "Read"]
                rest = stripped[len("allowed-tools:"):].strip()
                if rest and rest != "[]":
                    # 简单解析
                    import ast
                    try:
                        val = ast.literal_eval(rest)
                        if isinstance(val, list):
                            tools.extend(val)
                    except Exception:
                        pass
                continue
            if in_allowed:
                if stripped.startswith("- "):
                    tools.append(stripped[2:].strip().strip('"').strip("'"))
                elif stripped and not stripped.startswith("#"):
                    break
        return tools

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
