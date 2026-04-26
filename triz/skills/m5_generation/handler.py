"""M5 方案生成 Skill v2：搜索词生成 + 结果过滤 + 方案生成。"""
from pydantic import BaseModel

from triz.skills.base import Skill
from triz.context import WorkflowContext, SolutionDraft, Case, FOSReport


class FilteredCase(Case):
    """带相关性评分的 Case。"""
    relevance_score: int = 3
    relevance_reason: str = ""


class M5Input(BaseModel):
    """M5 Skill 输入。"""
    question: str
    principles: list[int]
    cases: list[Case]
    contradiction_desc: str
    ifr: str
    resources: dict[str, list[str]]
    feedback: str = ""

    # v2 新增
    fos_report: FOSReport | None = None
    search_queries: list[str] = []


class M5Output(BaseModel):
    """M5 Skill 输出。"""
    solution_drafts: list[SolutionDraft]

    # v2 新增
    search_queries: list[str] = []
    filtered_cases: list[FilteredCase] = []
    key_patterns: list[str] = []


class M5GenerationSkill(Skill[M5Input, M5Output]):
    """M5 方案生成 Skill v2。

    职责：
    1. 生成搜索词（search_queries）
    2. 调用 FOS 搜索（通过 tool_registry）
    3. 过滤结果（filtered_cases）
    4. 提取关键模式（key_patterns）
    5. 生成方案（solution_drafts）
    """

    name = "m5_generation"
    description = "当已获得发明原理，需要搜索跨领域案例并生成具体方案时使用"
    temperature = 0.4
    input_schema = M5Input
    output_schema = M5Output

    def execute(self, input_data: M5Input, ctx: WorkflowContext) -> M5Output:
        """执行方案生成（v2 两阶段）。"""

        # === 阶段 1：搜索词生成 + FOS 调用 ===
        if not input_data.fos_report or not input_data.fos_report.raw_results:
            search_result = self._search_phase(input_data, ctx)
        else:
            # FOS 已经执行过了（Agent 模式），直接用现有结果
            search_result = {
                "search_queries": input_data.search_queries,
                "fos_report": input_data.fos_report,
            }

        # === 阶段 2：过滤 + 提取模式 + 生成方案 ===
        system_prompt = self._load_prompt()

        # 渐进式披露：加载详细生成指南
        guide = self._load_reference("generation_guide.md")
        if guide:
            system_prompt += "\n\n" + guide

        user_prompt = self._build_prompt_v2(input_data, search_result)

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=False,
        )

        raw = self._parse_json(response)

        if "solution_drafts" not in raw:
            raw = self._retry_for_format(system_prompt, user_prompt)

        output = self.validate_output(raw)

        # 合并搜索阶段的结果到输出
        output.search_queries = search_result.get("search_queries", [])
        output.key_patterns = raw.get("key_patterns", [])

        # 从 LLM 输出中提取 filtered_cases
        for fc in raw.get("filtered_cases", []):
            if isinstance(fc, dict) and fc.get("relevance_score", 0) >= 3:
                output.filtered_cases.append(FilteredCase(
                    principle_id=input_data.principles[0] if input_data.principles else 0,
                    source=fc.get("source", "Google Patents"),
                    title=fc.get("title", ""),
                    description=fc.get("description", fc.get("snippet", "")),
                    function=fc.get("function", ""),
                    relevance_score=fc.get("relevance_score", 3),
                    relevance_reason=fc.get("relevance_reason", ""),
                ))

        return output

    def post_validate(self, output: M5Output, ctx: WorkflowContext) -> list[str]:
        warnings = []
        if not output.solution_drafts:
            warnings.append("方案列表为空")
        for draft in output.solution_drafts:
            if not draft.applied_principles:
                warnings.append(f"方案 '{draft.title}' 未引用发明原理")
            if len(draft.description) < 50:
                warnings.append(f"方案 '{draft.title}' 描述过短（{len(draft.description)} 字符）")
        return warnings

    def _search_phase(self, data: M5Input, ctx: WorkflowContext) -> dict:
        """阶段1：生成搜索词 → 调用 FOS。"""
        search_prompt = self._build_search_prompt(data)

        search_system = (
            "你是 TRIZ 跨界检索专家。根据用户问题、矛盾描述和发明原理，"
            "生成 3 个不同角度的英文搜索词（用于 Google Patents 搜索）。\n\n"
            "输出 JSON 格式：\n"
            '{"search_queries": ["query1", "query2", "query3"]}\n\n'
            "每个搜索词 3-8 个英文关键词，用空格分隔。不要用中文。"
        )

        response = self._call_llm(
            system_prompt=search_system,
            user_prompt=search_prompt,
            json_mode=False,
        )

        search_data = self._parse_json(response)
        queries = search_data.get("search_queries", [])

        # 调用 FOS 执行搜索
        fos_report = FOSReport()
        if queries:
            tool_registry = getattr(self, "tool_registry", None)
            if tool_registry:
                try:
                    fos_report = tool_registry.execute("search_patents", {
                        "queries": queries,
                        "principles": data.principles,
                        "limit_per_query": 5,
                    })
                except Exception:
                    fos_report = FOSReport()
            else:
                # 直接调用 search_patents（无 tool_registry 时）
                from triz.tools.fos_search import search_patents
                try:
                    fos_report = search_patents(
                        queries=queries,
                        principles=data.principles,
                        limit_per_query=5,
                    )
                except Exception:
                    fos_report = FOSReport()

        return {
            "search_queries": queries,
            "fos_report": fos_report,
        }

    def _build_search_prompt(self, data: M5Input) -> str:
        """构建搜索词生成的 prompt。"""
        lines = [
            f"用户问题：{data.question}",
            f"矛盾描述：{data.contradiction_desc}",
            f"发明原理：{data.principles}",
            f"理想最终结果：{data.ifr}",
            "",
            "请生成 3 个不同角度的英文搜索词：",
            "1. 功能角度（聚焦核心功能的专利）",
            "2. 原理角度（聚焦发明原理的跨领域应用）",
            "3. 问题角度（聚焦用户具体问题的解决方案）",
        ]

        if data.feedback:
            lines.append(f"\n上一轮反馈：{data.feedback}")

        return "\n".join(lines)

    def _build_prompt_v2(self, data: M5Input, search_result: dict) -> str:
        """构建方案生成 prompt（v2，包含 FOS 搜索结果）。"""
        lines = [
            f"问题：{data.question}",
            f"矛盾描述：{data.contradiction_desc}",
            f"理想最终结果：{data.ifr}",
            f"发明原理：{data.principles}",
        ]

        # 使用 FOS 返回的原始结果
        fos_report = search_result.get("fos_report")
        if fos_report and fos_report.raw_results:
            lines.append("跨界案例（来自专利检索）：")
            for r in fos_report.raw_results[:10]:
                lines.append(f"  - [{r.source}] {r.title}")
                lines.append(f"    {r.snippet}")
        elif data.cases:
            # 降级：使用旧的 cases 字段
            lines.append("跨界案例：")
            for case in data.cases:
                lines.append(f"  - [{case.source}] {case.title}: {case.description}")

        if data.resources:
            lines.append(f"可用资源：{data.resources}")

        if data.feedback:
            lines.append(f"上一轮反馈：{data.feedback}")

        return "\n".join(lines)

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

    def _retry_for_format(self, system_prompt: str, user_prompt: str) -> dict:
        """格式错误时重试一次。"""
        retry_prompt = (
            user_prompt + "\n\n"
            "【格式纠正】你的输出格式不正确。请输出一个包含 'solution_drafts' 字段的 JSON 对象。"
            "不要输出数组或其他格式。只输出纯 JSON。"
        )

        response = self._call_llm(
            system_prompt=system_prompt,
            user_prompt=retry_prompt,
            json_mode=False,
        )

        return self._parse_json(response)
