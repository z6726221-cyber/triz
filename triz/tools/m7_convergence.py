"""M7 收敛控制 Tool：四重阈值判定"""
from triz.context import WorkflowContext, ConvergenceDecision
from triz.config import MAX_ITERATIONS, MIN_IDEALITY_THRESHOLD


def check_convergence(ctx: WorkflowContext) -> ConvergenceDecision:
    """根据迭代状态做四重阈值判定。"""
    max_ideality = ctx.max_ideality
    iteration = ctx.iteration
    history = ctx.history_log
    signals = ctx.unresolved_signals

    # 1. 信号清空判定
    if not signals:
        return ConvergenceDecision(
            action="TERMINATE",
            reason="信号已清空，矛盾已充分解决"
        )

    # 2. 停滞判定
    if iteration > 0 and history:
        last_ideality = history[-1].get("max_ideality", 0)
        if max_ideality == last_ideality:
            return ConvergenceDecision(
                action="TERMINATE",
                reason=f"理想度停滞在 {max_ideality}，继续迭代无改善"
            )

    # 3. 收益递减判定
    if iteration >= 2 and len(history) >= 2:
        prev_ideality = history[-2].get("max_ideality", 0)
        improvement = max_ideality - prev_ideality
        if improvement < 0.05:
            return ConvergenceDecision(
                action="TERMINATE",
                reason=f"理想度改善率 {improvement:.3f} 低于阈值，收益递减"
            )

    # 4. 触达上限判定
    if iteration >= MAX_ITERATIONS:
        return ConvergenceDecision(
            action="TERMINATE",
            reason=f"达到最大迭代次数 {MAX_ITERATIONS}"
        )

    # 5. 理想度过低 -> CLARIFY
    if max_ideality < MIN_IDEALITY_THRESHOLD:
        return ConvergenceDecision(
            action="CLARIFY",
            reason=f"最高理想度 {max_ideality} 低于阈值 {MIN_IDEALITY_THRESHOLD}，需要用户补充信息"
        )

    # 6. CONTINUE
    feedback = _generate_feedback(signals, max_ideality)
    return ConvergenceDecision(
        action="CONTINUE",
        reason=f"理想度 {max_ideality}，继续迭代优化",
        feedback=feedback
    )


def _generate_feedback(signals: list, max_ideality: float) -> str:
    """生成给下一轮 M5 的反馈信息。"""
    feedback_parts = [f"上一轮最高理想度: {max_ideality}"]
    if signals:
        feedback_parts.append(f"未解决问题: {', '.join(signals[:3])}")
    return "; ".join(feedback_parts)
