"""编排器核心：持有 WorkflowContext，按序调用 Skill/Tool，支持回调通知。"""
from triz.context import WorkflowContext, ConvergenceDecision, SAO, SolutionDraft, Solution, Case, QualitativeTags
from triz.core.skill_runner import SkillRunner
from triz.core.tool_registry import ToolRegistry
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m7_convergence import check_convergence
from triz.tools.fos_search import search_cases
from triz.tools.query_parameters import query_parameters
from triz.tools.query_matrix import query_matrix
from triz.tools.query_separation import query_separation
from triz.utils.markdown_renderer import render_final_report


def _register_m4_tools() -> ToolRegistry:
    """注册 M4 Skill 可调用的 sub-tools。"""
    registry = ToolRegistry()
    registry.register(
        name="query_parameters",
        func=query_parameters,
        schema={
            "name": "query_parameters",
            "description": "根据关键词查询 39 个 TRIZ 工程参数",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["keywords"],
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
        self.skill_runner = SkillRunner(self.tool_registry)
        self.callback = callback

    def _notify(self, event_type: str, data: dict):
        if self.callback:
            self.callback(event_type, data)

    def run_workflow(self, question: str, history: list = None):
        """执行完整 TRIZ workflow，通过回调通知 UI 更新。

        返回最终的 Markdown 报告字符串（供 /save 使用）。
        """
        ctx = WorkflowContext(question=question, history=history or [])
        self.output_buffer = []

        # ===== 问题建模 =====
        ctx = self._execute_node("问题建模", 1, 5, ctx, [
            ("m1_modeling", "Skill"),
            ("m2_causal", "Skill"),
            ("M3", "Tool", formulate_problem),
        ])

        if not ctx.sao_list:
            msg = self._generate_clarification("无法从问题中提取功能模型，请补充描述")
            self._notify("report", {"content": msg})
            return msg

        # ===== 迭代主循环 =====
        while True:
            # 矛盾求解
            ctx = self._execute_node("矛盾求解", 2, 5, ctx, [
                ("m4_solver", "Skill"),
            ])

            if not ctx.principles:
                msg = self._generate_fallback("无法从矛盾定义中匹配到发明原理")
                self._notify("report", {"content": msg})
                return msg

            # 跨界检索
            ctx = self._execute_node("跨界检索", 3, 5, ctx, [
                ("FOS", "Tool", search_cases),
            ])

            # 方案生成
            ctx = self._execute_node("方案生成", 4, 5, ctx, [
                ("m5_generation", "Skill"),
            ])

            if not ctx.solution_drafts:
                msg = self._generate_fallback("未能生成有效方案")
                self._notify("report", {"content": msg})
                return msg

            # 方案评估
            ctx = self._execute_node("方案评估", 5, 5, ctx, [
                ("m6_evaluation", "Skill"),
            ])

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
                ctx.solution_drafts = []
                ctx.ranked_solutions = []
                ctx.max_ideality = 0.0
                ctx.unresolved_signals = []

    def _execute_node(self, node_name: str, current: int, total: int,
                      ctx: WorkflowContext, steps: list) -> WorkflowContext:
        """执行一个用户可见节点，通过回调通知 UI。"""
        self._notify("node_start", {"node_name": node_name, "current": current, "total": total})
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
                    result = self.skill_runner.run(step_name, ctx)
                else:
                    result = step_func(ctx)
            except Exception as e:
                self._notify("step_error", {
                    "step_name": step_name, "step_type": step_type, "error": str(e)
                })
                # 降级：返回空结果继续
                result = {}

            # FOS search_cases 返回 list[Case]，包装为 dict
            if isinstance(result, list):
                result = {"cases": result}

            ctx = self._merge_result(ctx, result)
            self._notify("step_complete", {
                "step_name": step_name, "step_type": step_type, "result": result
            })
            node_outputs.append({"step_name": step_name, "step_type": step_type, "result": result})

        self._notify("node_complete", {"node_name": node_name, "ctx": ctx, "outputs": node_outputs})
        return ctx

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
