"""编排器核心：持有 WorkflowContext，按序调用 Skill/Tool，支持回调通知。"""
import time

from triz.context import WorkflowContext, ConvergenceDecision, SAO, SolutionDraft, Solution, Case, QualitativeTags
from triz.core.tool_registry import ToolRegistry
from triz.skills.registry import SkillRegistry
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m7_convergence import check_convergence
from triz.tools.fos_search import search_patents
from triz.tools.solve_contradiction import solve_contradiction
from triz.tools.query_parameters import map_to_parameters, query_parameters
from triz.tools.query_matrix import query_matrix
from triz.tools.query_separation import query_separation
from triz.utils.markdown_renderer import render_final_report
from triz.config import MODEL_M1, MODEL_M2, MODEL_M3, MODEL_M4, MODEL_M5, MODEL_M6
from triz.tools.input_classifier import classify_input


def _register_m4_tools() -> ToolRegistry:
    """注册 M4 Skill 可调用的 sub-tools。"""
    registry = ToolRegistry()
    registry.register(
        name="map_to_parameters",
        func=map_to_parameters,
        schema={
            "name": "map_to_parameters",
            "description": "将中文描述映射到 39 个 TRIZ 工程参数 ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "improve_aspect": {"type": "string", "description": "需要改善的方面（2-6个中文词）"},
                    "worsen_aspect": {"type": "string", "description": "随之恶化的方面（2-6个中文词）"},
                },
                "required": ["improve_aspect", "worsen_aspect"],
            },
        }
    )
    registry.register(
        name="query_matrix",
        func=query_matrix,
        schema={
            "name": "query_matrix",
            "description": "查询阿奇舒勒矛盾矩阵",
            "parameters": {
                "type": "object",
                "properties": {
                    "improve_param_id": {"type": "integer"},
                    "worsen_param_id": {"type": "integer"},
                },
                "required": ["improve_param_id", "worsen_param_id"],
            },
        }
    )
    registry.register(
        name="query_separation",
        func=query_separation,
        schema={
            "name": "query_separation",
            "description": "查询物理矛盾的分离原理",
            "parameters": {
                "type": "object",
                "properties": {
                    "contradiction_desc": {"type": "string"}
                },
                "required": ["contradiction_desc"],
            },
        }
    )
    registry.register(
        name="search_patents",
        func=search_patents,
        schema={
            "name": "search_patents",
            "description": "接收搜索词列表，执行 Google Patents 搜索，返回结构化报告",
            "parameters": {
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索词列表（英文，3-8个关键词）",
                    },
                    "principles": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "发明原理编号列表",
                    },
                    "limit_per_query": {
                        "type": "integer",
                        "description": "每个 query 最多返回的结果数",
                        "default": 5,
                    },
                },
                "required": ["queries", "principles"],
            },
        }
    )
    return registry


class Orchestrator:
    """TRIZ Workflow 编排器。

    callback(event_type, data) 事件:
    - node_start:  {node_name, current, total}
    - step_start:  {step_name, step_type}
    - step_complete: {step_name, step_type, result}
    - step_error:  {step_name, step_type, error}
    - node_complete: {node_name, ctx, outputs}
    - decision:    {action, reason, feedback}
    - report:      {content} (最终报告或中断消息)
    """

    def __init__(self, callback=None):
        self.output_buffer = []
        self.tool_registry = _register_m4_tools()
        self.skill_registry = SkillRegistry(tool_registry=self.tool_registry)
        self.callback = callback
        self._setup_routes()

    def _setup_routes(self):
        """配置默认的节点路由规则。

        每个节点可以有多个候选路由，按优先级降序匹配第一个满足条件的。
        后续新增模块（物场分析、剪裁等）只需在此注册新路由即可。
        """
        registry = self.skill_registry

        # 节点 1: 问题建模
        registry.register_node_route(
            "modeling",
            [
                ("m1_modeling", "Skill"),
                ("m2_causal", "Skill"),
                ("m3_formulation", "Skill"),
            ],
            priority=1,
        )

        # 节点 2: 矛盾求解（纯 Tool，不调 LLM）
        registry.register_node_route(
            "solver",
            [("solve_contradiction", "Tool")],
            priority=1,
        )

        # 节点 3: 搜索与方案生成（合并原 Node 3+4）
        registry.register_node_route(
            "search_generation",
            [("m5_generation", "Skill")],
            priority=1,
        )

        # 节点 4: 方案评估
        registry.register_node_route(
            "evaluation",
            [("m6_evaluation", "Skill")],
            priority=1,
        )

    def _notify(self, event_type: str, data: dict):
        if self.callback:
            self.callback(event_type, data)

    def run_workflow(self, question: str, history: list = None):
        """执行完整 TRIZ workflow，通过回调通知 UI 更新。

        返回最终的 Markdown 报告字符串（供 /save 使用）。
        """
        ctx = WorkflowContext(question=question, history=history or [])
        self.output_buffer = []

        # ===== 输入分类（M1 之前）=====
        classification = classify_input(question)
        if not classification["proceed"]:
            msg = classification["response"]
            self._notify("report", {"content": msg})
            return msg

        # ===== 问题建模 =====
        steps = self.skill_registry.resolve_node("modeling", ctx)
        if not steps:
            raise RuntimeError("未找到 'modeling' 节点的路由配置")
        ctx = self._execute_node("问题建模", 1, 4, ctx, steps)

        if not ctx.sao_list:
            msg = self._generate_clarification("无法从问题中提取功能模型，请补充描述")
            self._notify("report", {"content": msg})
            return msg

        # ===== 迭代主循环 =====
        while True:
            # 矛盾求解
            steps = self.skill_registry.resolve_node("solver", ctx)
            if not steps:
                raise RuntimeError("未找到 'solver' 节点的路由配置")
            ctx = self._execute_node("矛盾求解", 2, 4, ctx, steps)

            if not ctx.principles:
                msg = self._generate_fallback("无法从矛盾定义中匹配到发明原理")
                self._notify("report", {"content": msg})
                return msg

            # 搜索与方案生成（M5 内部调用 FOS）
            steps = self.skill_registry.resolve_node("search_generation", ctx)
            if not steps:
                raise RuntimeError("未找到 'search_generation' 节点的路由配置")
            ctx = self._execute_node("搜索与方案生成", 3, 4, ctx, steps)

            if not ctx.solution_drafts:
                # Fallback: 基于已获取的原理和案例构造默认方案
                fallback_output = self._try_fallback("m5_generation", Exception("empty solution_drafts"), ctx)
                if fallback_output and fallback_output.get("solution_drafts"):
                    from triz.context import SolutionDraft
                    drafts = [SolutionDraft.model_validate(d) for d in fallback_output["solution_drafts"]]
                    ctx = ctx.model_copy(update={"solution_drafts": drafts})
                    self._notify("step_complete", {
                        "step_name": "m5_generation", "step_type": "Skill",
                        "result": {"solution_drafts": fallback_output["solution_drafts"], "fallback": True}
                    })
                else:
                    msg = self._generate_fallback("未能生成有效方案")
                    self._notify("report", {"content": msg})
                    return msg

            # 方案评估
            steps = self.skill_registry.resolve_node("evaluation", ctx)
            if not steps:
                raise RuntimeError("未找到 'evaluation' 节点的路由配置")
            ctx = self._execute_node("方案评估", 4, 4, ctx, steps)

            # 收敛控制
            decision = check_convergence(ctx)
            self._notify("decision", {
                "action": decision.action,
                "reason": decision.reason,
                "feedback": decision.feedback,
            })

            if decision.action == "TERMINATE":
                contradiction = ctx.contradiction_desc or "未识别矛盾"
                report = render_final_report(
                    ctx.question, contradiction, ctx.ranked_solutions, decision.reason
                )
                self._notify("report", {"content": report})
                return report

            elif decision.action == "CLARIFY":
                msg = self._generate_clarification(decision.reason)
                self._notify("report", {"content": msg})
                return msg

            elif decision.action == "CONTINUE":
                ctx.iteration += 1
                ctx.feedback = decision.feedback
                ctx.history_log.append({"max_ideality": ctx.max_ideality})
                ctx.principles = []
                ctx.cases = []
                ctx.search_queries = []
                ctx.fos_report = None
                ctx.solution_drafts = []
                ctx.ranked_solutions = []
                ctx.max_ideality = 0.0
                ctx.unresolved_signals = []

    def _execute_node(self, node_name: str, current: int, total: int,
                      ctx: WorkflowContext, steps: list) -> WorkflowContext:
        """执行一个用户可见节点，通过回调通知 UI。"""
        self._notify("node_start", {"node_name": node_name, "current": current, "total": total})
        node_start_time = time.time()
        node_outputs = []

        for step in steps:
            if len(step) == 2:
                step_name, step_type = step
                step_func = None
            else:
                step_name, step_type, step_func = step

            # M2 门控
            if step_name == "m2_causal":
                if not should_trigger_m2(ctx):
                    node_outputs.append({"type": "gate_skip", "reason": "无负面功能"})
                    self._notify("step_complete", {
                        "step_name": step_name, "step_type": "Gate",
                        "result": {"skipped": True, "reason": "无负面功能"}
                    })
                    continue

            self._notify("step_start", {"step_name": step_name, "step_type": step_type})

            try:
                if step_type == "Skill":
                    result = self._run_skill(step_name, ctx)
                else:
                    # Tool: 如果有 step_func 就用，否则按名称查找
                    func = step_func
                    if func is None:
                        func = self._resolve_tool(step_name)
                    result = func(ctx)
            except Exception as e:
                self._notify("step_error", {
                    "step_name": step_name, "step_type": step_type, "error": str(e)
                })
                # 尝试 Skill fallback
                result = self._try_fallback(step_name, e, ctx) or {}

            # FOS search_cases 返回 list[Case]，包装为 dict
            if isinstance(result, list):
                result = {"cases": result}

            ctx = self._merge_result(ctx, result)
            self._notify("step_complete", {
                "step_name": step_name, "step_type": step_type, "result": result
            })
            node_outputs.append({"step_name": step_name, "step_type": step_type, "result": result})

        elapsed = time.time() - node_start_time
        self._notify("node_complete", {"node_name": node_name, "ctx": ctx, "outputs": node_outputs, "elapsed_seconds": elapsed})
        return ctx

    def _run_skill(self, step_name: str, ctx: WorkflowContext) -> dict:
        """通过 SkillRegistry 运行指定 Skill。"""
        skill = self.skill_registry.get(step_name)
        if skill is None:
            raise ValueError(f"Skill not found: {step_name}")

        # 从 WorkflowContext 构建 Skill 输入
        input_data = self._build_skill_input(skill, ctx)

        # 执行 Skill
        output = skill.execute(input_data, ctx)

        # Pydantic 模型 → dict
        return output.model_dump() if hasattr(output, "model_dump") else output

    def _resolve_tool(self, name: str):
        """按名称查找 Tool 函数（运行时导入，支持 mock）。"""
        if name == "solve_contradiction":
            from triz.tools.solve_contradiction import solve_contradiction
            return solve_contradiction
        return lambda ctx: {}

    def _build_skill_input(self, skill, ctx: WorkflowContext):
        """从 WorkflowContext 提取 Skill 输入模型所需的字段。"""
        from pydantic import BaseModel

        input_data = {}
        for field_name in skill.input_schema.model_fields:
            if hasattr(ctx, field_name):
                input_data[field_name] = getattr(ctx, field_name)
        return skill.input_schema(**input_data)

    def _try_fallback(self, step_name: str, error: Exception, ctx: WorkflowContext) -> dict | None:
        """尝试调用 Skill 的 fallback 方法。"""
        skill = self.skill_registry.get(step_name)
        if skill is None:
            return None

        try:
            input_data = self._build_skill_input(skill, ctx)
            fallback_output = skill.fallback(input_data, error, ctx)
            if fallback_output is not None:
                return fallback_output.model_dump() if hasattr(fallback_output, "model_dump") else fallback_output
        except Exception:
            pass
        return None

    def _merge_result(self, ctx: WorkflowContext, result: dict) -> WorkflowContext:
        """将模块输出合并到 WorkflowContext，自动将 dict 反序列化为 Pydantic 模型。"""
        for key, value in result.items():
            if not hasattr(ctx, key):
                continue

            if key == "sao_list" and isinstance(value, list):
                value = [
                    SAO.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "cases" and isinstance(value, list):
                value = [
                    Case.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "fos_report" and isinstance(value, dict):
                from triz.context import FOSReport
                value = FOSReport.model_validate(value)
            elif key == "solution_drafts" and isinstance(value, list):
                value = [
                    SolutionDraft.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "ranked_solutions" and isinstance(value, list):
                converted = []
                for item in value:
                    if isinstance(item, dict):
                        if "draft" in item and isinstance(item["draft"], dict):
                            converted.append(Solution.model_validate(item))
                        else:
                            draft = SolutionDraft(
                                title=item.get("title", ""),
                                description=item.get("description", ""),
                                applied_principles=item.get("applied_principles", []),
                                resource_mapping=item.get("resource_mapping", ""),
                            )
                            tags = QualitativeTags(
                                feasibility_score=item.get("feasibility_score", 3),
                                resource_fit_score=item.get("resource_fit_score", 3),
                                innovation_score=item.get("innovation_score", 3),
                                uniqueness_score=item.get("uniqueness_score", 3),
                                risk_level=item.get("risk_level", "medium"),
                                ifr_deviation_reason=item.get("ifr_deviation_reason", ""),
                                problem_relevance_score=item.get("problem_relevance_score", 3),
                                logical_consistency_score=item.get("logical_consistency_score", 3),
                            )
                            converted.append(Solution(
                                draft=draft, tags=tags,
                                ideality_score=item.get("ideality_score", 0.5),
                                evaluation_rationale=item.get("evaluation_rationale", ""),
                            ))
                    else:
                        converted.append(item)
                value = converted

            setattr(ctx, key, value)
        return ctx

    def _generate_clarification(self, reason: str) -> str:
        return f"**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"

    def _generate_fallback(self, reason: str) -> str:
        return f"**流程中断**：{reason}\n\n建议：尝试用更具体的工程语言描述问题，或提供更多技术细节。"

