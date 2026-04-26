"""TrizAgent：ReAct 风格的自主 Agent，通过方法论文档约束行为。

Agent 模式特点：
- Agent 自主决定下一步调用哪个 Skill/Tool
- Skill 输出 Markdown，Agent 阅读理解后决定下一步
- Agent 负责上下文传递：将上游 Markdown 输出传给下游 Skill
- 方法论约束通过 AGENT.md 提供
"""
import json
from pathlib import Path

from triz.context import WorkflowContext
from triz.agent.skills.registry import AgentSkillRegistry
from triz.tools.input_classifier import classify_input
from triz.utils.api_client import OpenAIClient
from triz.config import AGENT_API_KEY, AGENT_BASE_URL, AGENT_MODEL_NAME


class TrizAgent:
    """ReAct 风格 TRIZ Agent。

    Agent 维护一个记忆列表（已完成步骤 + 结果），每次调用 LLM 时：
    - system prompt = AGENT.md（方法论约束）
    - user prompt = 当前记忆 + 上下文 + 可用 Skills

    LLM 输出 thought + action，Agent 执行 action，结果加入记忆，循环继续。
    """

    def __init__(self, skill_registry: AgentSkillRegistry | None = None,
                 tool_registry=None, callback=None):
        self.skill_registry = skill_registry or AgentSkillRegistry()
        self.tool_registry = tool_registry
        self.callback = callback
        # Agent 独立 client：优先用 AGENT_* 配置，否则回退到默认
        agent_key = AGENT_API_KEY or None
        agent_url = AGENT_BASE_URL or None
        agent_model = AGENT_MODEL_NAME or None
        if agent_key or agent_url or agent_model:
            self.client = OpenAIClient(
                api_key=agent_key,
                base_url=agent_url,
                model=agent_model,
            )
        else:
            self.client = OpenAIClient()
        self.memory: list[dict] = []  # ReAct 记忆
        self.ctx: WorkflowContext | None = None

    def _load_methodology(self) -> str:
        """加载 AGENT.md 方法论文档。"""
        agent_md = Path(__file__).parent / "AGENT.md"
        if agent_md.exists():
            return agent_md.read_text(encoding="utf-8")
        return "你是 TRIZ 分析专家。"

    def _notify(self, event_type: str, data: dict):
        if self.callback:
            self.callback(event_type, data)

    def run(self, question: str, history: list = None) -> str:
        """执行完整 TRIZ workflow。"""
        self.ctx = WorkflowContext(question=question, history=history or [])
        self.memory = []

        # 输入分类
        classification = classify_input(question)
        if not classification["proceed"]:
            msg = classification["response"]
            self._notify("report", {"content": msg})
            return msg

        # ReAct 主循环
        max_steps = 20
        consecutive_errors = {}  # name -> count
        for step in range(max_steps):
            # 1. Agent 思考并决策
            decision = self._think_and_act()

            # 2. 执行 action
            action = decision["action"]

            if action["type"] == "clarify":
                msg = self._generate_clarification(action.get("message", "需要补充信息"))
                self._notify("report", {"content": msg})
                return msg

            elif action["type"] == "report":
                return self._generate_report()

            elif action["type"] in ("skill", "tool"):
                name = action.get("name", "")
                if not name:
                    self.memory.append({
                        "role": "system",
                        "content": "错误：名称不能为空，请重新决策。",
                    })
                    continue

                # 判断是 Skill 还是 Tool
                is_tool = action["type"] == "tool" or (self.tool_registry and self.tool_registry.get(name))
                step_type = "Tool" if is_tool else "Skill"

                self._notify("step_start", {
                    "step_name": name,
                    "step_type": step_type,
                    "agent_thought": decision.get("thought", ""),
                })

                try:
                    if is_tool:
                        result = self._execute_tool(name)
                        # Tool 结果以可读文本加入记忆
                        tool_text = self._format_tool_result(name, result)
                        self.memory.append({
                            "role": "assistant",
                            "skill": name,
                            "thought": decision.get("thought", ""),
                        })
                        self.memory.append({
                            "role": "system",
                            "tool_result": name,
                            "content": tool_text,
                        })
                    else:
                        markdown = self._execute_skill(name)
                        # Skill 的 Markdown 输出加入记忆
                        self.memory.append({
                            "role": "assistant",
                            "skill": name,
                            "thought": decision.get("thought", ""),
                        })
                        self.memory.append({
                            "role": "system",
                            "skill_result": name,
                            "content": markdown,
                        })

                    self._notify("step_complete", {
                        "step_name": name,
                        "step_type": step_type,
                        "result": result if is_tool else markdown,
                    })

                except Exception as e:
                    consecutive_errors[name] = consecutive_errors.get(name, 0) + 1
                    err_msg = f"执行 {name} 出错 ({consecutive_errors[name]}/3): {str(e)}"
                    self.memory.append({
                        "role": "system",
                        "content": err_msg,
                    })
                    self._notify("step_error", {
                        "step_name": name,
                        "error": str(e),
                    })
                    if consecutive_errors[name] >= 3:
                        self.memory.append({
                            "role": "system",
                            "content": f"{name} 连续失败 3 次，跳过此步骤。",
                        })
                        consecutive_errors[name] = 0

            else:
                self.memory.append({
                    "role": "system",
                    "content": f"未知的 action 类型: {action.get('type')}",
                })

        return self._generate_report()

    def _think_and_act(self) -> dict:
        """调用 LLM 思考当前状态并决策下一步行动。"""
        system_prompt = self._load_methodology()
        user_prompt = self._build_react_prompt()

        response = self.client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            json_mode=True,
        )

        try:
            data = json.loads(response)
            return {
                "thought": data.get("thought", ""),
                "action": data.get("action", {"type": "skill", "name": ""}),
            }
        except json.JSONDecodeError:
            return {
                "thought": "解析失败",
                "action": {"type": "skill", "name": "m1_modeling"},
            }

    def _build_react_prompt(self) -> str:
        """构建 ReAct 风格的 prompt。"""
        ctx = self.ctx

        lines = [
            f"用户问题: {ctx.question}",
            f"当前迭代次数: {ctx.iteration}",
            f"当前反馈（如有）: {ctx.feedback or '无'}",
            "",
            "=== 已完成的分析 ===",
        ]

        # 展示完整的 Skill Markdown 输出
        for mem in self.memory:
            if mem.get("role") == "assistant":
                lines.append(f"\n### 执行了 {mem.get('skill', 'unknown')}")
                lines.append(f"思考: {mem.get('thought', '')}")
            elif mem.get("role") == "system" and "skill_result" in mem:
                lines.append(f"\n#### {mem['skill_result']} 输出：")
                lines.append(mem["content"])
            elif mem.get("role") == "system" and "tool_result" in mem:
                lines.append(f"\n#### {mem['tool_result']} 输出：")
                lines.append(mem["content"])
            elif mem.get("role") == "system" and "content" in mem:
                lines.append(f"\n> {mem['content']}")

        lines.append("")
        lines.append("=== 可用 Skills ===")
        for skill_meta in self.skill_registry.list_skills():
            lines.append(f"- {skill_meta['name']}: {skill_meta['description']}")
            if skill_meta.get("gotchas"):
                for g in skill_meta["gotchas"][:2]:
                    lines.append(f"  ! {g}")
        if self.tool_registry:
            lines.append("")
            lines.append("=== 可用 Tools ===")
            for schema in self.tool_registry.get_schemas():
                func = schema.get("function", {})
                name = func.get("name", "unknown")
                desc = func.get("description", "无描述")
                params = func.get("parameters", {}).get("properties", {})
                required = func.get("parameters", {}).get("required", [])
                lines.append(f"- `{name}`: {desc}")
                if params:
                    param_parts = []
                    for p_name, p_info in params.items():
                        req = "*" if p_name in required else ""
                        param_parts.append(f"{p_name}{req}: {p_info.get('description', '')}")
                    lines.append(f"  参数: {', '.join(param_parts)}")

        lines.append("")
        lines.append("请思考当前状态，决定下一步行动。")
        lines.append('输出 JSON: {"thought": "...", "action": {"type": "...", "name": "..."}}')

        return "\n".join(lines)

    def _execute_skill(self, name: str) -> str:
        """执行 Agent Skill，返回 Markdown。"""
        skill = self.skill_registry.get(name)
        if skill is None:
            raise ValueError(f"Skill not found: {name}")

        # 构建上下文：累积之前 Skill 的 Markdown 输出
        context_markdown = self._build_context_markdown()

        # 执行 Skill
        markdown = skill.execute(self.ctx, context_markdown)

        # post_validate（保留业务逻辑校验）
        warnings = skill.post_validate(markdown, self.ctx)
        if warnings and len(warnings) >= 2:
            skill._retry_hints = warnings
            markdown = skill.execute(self.ctx, context_markdown)
            retry_warnings = skill.post_validate(markdown, self.ctx)
            if retry_warnings:
                self.memory.append({
                    "role": "system",
                    "content": f"{name} 重试后仍有警告: {'; '.join(retry_warnings)}",
                })
        elif warnings:
            self.memory.append({
                "role": "system",
                "content": f"{name} 校验警告: {'; '.join(warnings)}",
            })

        return markdown

    def _execute_tool(self, name: str) -> dict:
        """执行 Tool，返回 dict。"""
        tool_func = self.tool_registry.get(name)
        if tool_func is None:
            raise ValueError(f"Tool not found: {name}")
        if name == "search_patents":
            return self._execute_fos(tool_func)
        return tool_func(self.ctx)

    def _execute_fos(self, search_patents_func) -> dict:
        """执行 FOS 跨界检索。"""
        queries = self._generate_fos_queries()
        report = search_patents_func(
            queries=queries,
            principles=self.ctx.principles,
            limit_per_query=5,
        )
        self.ctx.fos_report = report
        self.ctx.search_queries = queries
        return {
            "cases": report.cases,
            "fos_report": report.model_dump(),
            "search_queries": queries,
        }

    def _generate_fos_queries(self) -> list[str]:
        """Agent 模式下为 FOS 生成搜索词。"""
        queries = []
        principles = self.ctx.principles[:3]

        if self.ctx.sao_list:
            function = ""
            for sao in self.ctx.sao_list:
                if sao.function_type == "useful":
                    function = sao.action
                    break
            if function:
                p_str = " ".join([f"principle {p}" for p in principles])
                queries.append(f"{p_str} {function}")

        if self.ctx.contradiction_desc:
            queries.append(self.ctx.contradiction_desc)

        if not queries:
            queries.append(self.ctx.question)

        return queries[:3]

    def _format_tool_result(self, name: str, result: dict) -> str:
        """将 Tool 结果格式化为可读文本。"""
        if name == "search_patents":
            return self._format_fos_result(result)
        elif name == "solve_contradiction":
            return self._format_contradiction_result(result)
        else:
            return json.dumps(result, ensure_ascii=False, default=str)

    def _format_fos_result(self, result: dict) -> str:
        """格式化 FOS 搜索结果为 Markdown。"""
        lines = ["## 跨界检索结果"]

        queries = result.get("search_queries", [])
        if queries:
            lines.append(f"搜索词：{', '.join(queries)}")

        cases = result.get("cases", [])
        if cases:
            lines.append(f"\n检索到 {len(cases)} 条案例：")
            for i, c in enumerate(cases, 1):
                if isinstance(c, dict):
                    lines.append(f"{i}. **{c.get('title', '')}** (原理 {c.get('principle_id', '')})")
                    lines.append(f"   来源: {c.get('source', '')} | 功能: {c.get('function', '')}")
                    lines.append(f"   描述: {c.get('description', '')}")
                else:
                    lines.append(f"{i}. {c}")

        fos_report = result.get("fos_report")
        if fos_report and isinstance(fos_report, dict):
            raw = fos_report.get("raw_results", [])
            if raw and not cases:
                lines.append(f"\n检索到 {len(raw)} 条原始结果：")
                for i, r in enumerate(raw[:10], 1):
                    if isinstance(r, dict):
                        lines.append(f"{i}. **{r.get('title', '')}**")
                        lines.append(f"   摘要: {r.get('snippet', '')}")

        if not cases and not (fos_report and isinstance(fos_report, dict) and fos_report.get("raw_results")):
            lines.append("（未检索到相关案例）")

        return "\n".join(lines)

    def _format_contradiction_result(self, result: dict) -> str:
        """格式化矛盾求解结果为 Markdown。"""
        lines = ["## 矛盾求解结果"]

        principles = result.get("principles", [])
        if principles:
            lines.append(f"推荐发明原理：{', '.join(str(p) for p in principles)}")

        desc = result.get("contradiction_desc", "")
        if desc:
            lines.append(f"矛盾描述：{desc}")

        return "\n".join(lines)

    def _build_context_markdown(self) -> str:
        """累积之前 Skill/Tool 的 Markdown 输出，作为下游 Skill 的背景信息。"""
        parts = []
        for mem in self.memory:
            if "skill_result" in mem:
                parts.append(f"## {mem['skill_result']} 输出\n{mem['content']}")
            elif "tool_result" in mem:
                parts.append(f"## {mem['tool_result']} 输出\n{mem['content']}")
        return "\n\n".join(parts)

    def _generate_report(self) -> str:
        """基于 memory 中的所有 Markdown 输出，用 LLM 生成最终报告。"""
        # 收集所有 Skill/Tool 的输出
        analysis_parts = []
        for mem in self.memory:
            if "skill_result" in mem:
                analysis_parts.append(f"### {mem['skill_result']}\n{mem['content']}")
            elif "tool_result" in mem:
                analysis_parts.append(f"### {mem['tool_result']}\n{mem['content']}")

        analysis_text = "\n\n".join(analysis_parts) if analysis_parts else "（无分析结果）"

        system_prompt = (
            "你是 TRIZ 报告撰写专家。基于以下分析过程和结果，生成一份结构化的 TRIZ 解决方案报告。\n\n"
            "报告格式要求：\n"
            "# TRIZ 解决方案报告\n\n"
            "## 问题概述\n（简述用户问题）\n\n"
            "## 功能分析\n（SAO 三元组、资源、IFR）\n\n"
            "## 根因分析\n（因果链、根因参数）\n\n"
            "## 矛盾定义\n（矛盾类型、矛盾对）\n\n"
            "## 解决方案\n（基于发明原理的具体方案，包含应用原理、方案描述、资源映射）\n\n"
            "## 方案评估\n（评分、排序、推荐）\n\n"
            "要求：\n"
            "- 保留分析中的关键数据和结论\n"
            "- 方案部分要具体、可执行\n"
            "- 如果某个步骤没有执行或结果为空，跳过该章节\n"
            "- 使用中文输出"
        )

        user_prompt = (
            f"用户问题: {self.ctx.question}\n\n"
            f"=== 分析过程和结果 ===\n\n{analysis_text}\n\n"
            "请基于以上内容生成最终报告。"
        )

        report = self._call_llm(system_prompt, user_prompt)
        self._notify("report", {"content": report})
        return report

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM，返回文本。"""
        return self.client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
        )

    def _generate_clarification(self, reason: str) -> str:
        return f"**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"
