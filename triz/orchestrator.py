"""编排器核心：持有 WorkflowContext，按序调用 Skill/Tool，渲染 Markdown 输出"""
from triz.context import WorkflowContext, ConvergenceDecision
from triz.skills.m1_modeling import model_function
from triz.skills.m2_causal import analyze_cause
from triz.skills.m5_generation import generate_solutions
from triz.skills.m6_evaluation import evaluate_solutions
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m4_solver import solve_contradiction
from triz.tools.m7_convergence import check_convergence
from triz.tools.fos_search import search_cases
from triz.utils.markdown_renderer import (
    render_node_start, render_step_complete,
    render_node_complete, render_final_report
)


class Orchestrator:
    """TRIZ Workflow 编排器。"""

    def __init__(self):
        self.output_buffer = []

    def run_workflow(self, question: str, history: list = None) -> str:
        """执行完整 TRIZ workflow，返回 Markdown 格式的最终报告。"""
        ctx = WorkflowContext(question=question, history=history or [])
        self.output_buffer = []

        # ===== 问题建模 =====
        ctx = self._execute_node("问题建模", 1, 5, ctx, [
            ("M1", model_function, "Skill"),
            ("M2", analyze_cause, "Skill"),
            ("M3", formulate_problem, "Tool"),
        ])

        if not ctx.sao_list:
            return self._generate_clarification("无法从问题中提取功能模型，请补充描述")

        # ===== 迭代主循环 =====
        while True:
            # 矛盾求解
            ctx = self._execute_node("矛盾求解", 2, 5, ctx, [
                ("M4", solve_contradiction, "Tool"),
            ])

            if not ctx.principles:
                return self._generate_fallback("无法从矛盾定义中匹配到发明原理")

            # 跨界检索
            ctx = self._execute_node("跨界检索", 3, 5, ctx, [
                ("FOS", search_cases, "Tool"),
            ])

            # 方案生成
            ctx = self._execute_node("方案生成", 4, 5, ctx, [
                ("M5", generate_solutions, "Skill"),
            ])

            if not ctx.solution_drafts:
                return self._generate_fallback("未能生成有效方案")

            # 方案评估
            ctx = self._execute_node("方案评估", 5, 5, ctx, [
                ("M6_LLM", evaluate_solutions, "Skill"),
            ])

            # 收敛控制（内部调用，不渲染为用户可见节点）
            decision = check_convergence(ctx)
            self.output_buffer.append(f"\n[编排器] 决策: {decision.action} - {decision.reason}\n")

            if decision.action == "TERMINATE":
                contradiction = ctx.contradiction_desc or "未识别矛盾"
                report = render_final_report(
                    ctx.question, contradiction, ctx.ranked_solutions, decision.reason
                )
                return "\n".join(self.output_buffer) + "\n" + report

            elif decision.action == "CLARIFY":
                return self._generate_clarification(decision.reason)

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
        """执行一个用户可见节点，渲染 Markdown 输出。"""
        self.output_buffer.append(render_node_start(node_name, current, total))

        for step_name, step_func, step_type in steps:
            if step_name == "M2":
                if not should_trigger_m2(ctx):
                    self.output_buffer.append(f"- Tool: M2 门控 -> 跳过（无负面功能）\n")
                    continue

            result = step_func(ctx)
            # FOS search_cases 返回 list[Case]，需要包装为 dict
            if isinstance(result, list):
                result = {"cases": result}
            ctx = self._merge_result(ctx, result)
            self.output_buffer.append(render_step_complete(step_name, step_type, result))

        self.output_buffer.append(render_node_complete(node_name, ctx))
        return ctx

    def _merge_result(self, ctx: WorkflowContext, result: dict) -> WorkflowContext:
        """将模块输出合并到 WorkflowContext。"""
        for key, value in result.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
        return ctx

    def _generate_clarification(self, reason: str) -> str:
        return "\n".join(self.output_buffer) + f"\n\n**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"

    def _generate_fallback(self, reason: str) -> str:
        return "\n".join(self.output_buffer) + f"\n\n**流程中断**：{reason}\n\n建议：尝试用更具体的工程语言描述问题，或提供更多技术细节。"
