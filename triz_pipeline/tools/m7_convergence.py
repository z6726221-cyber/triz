"""M7 收敛控制 Tool：七重阈值判定"""
from triz_pipeline.context import WorkflowContext, ConvergenceDecision
from triz_pipeline.config import MAX_ITERATIONS, MIN_IDEALITY_THRESHOLD

# 理想度足够高时提前终止的阈值
HIGH_IDEALITY_THRESHOLD = 0.7


def check_convergence(ctx: WorkflowContext) -> ConvergenceDecision:
    """根据迭代状态做七重阈值判定。"""
    max_ideality = ctx.max_ideality
    iteration = ctx.iteration
    history = ctx.history_log
    signals = ctx.unresolved_signals
    solutions = ctx.ranked_solutions

    if not solutions:
        return ConvergenceDecision(
            action="CLARIFY",
            reason="无可用方案进行评估"
        )

    top = solutions[0]
    top_relevance = top.tags.problem_relevance_score
    top_consistency = top.tags.logical_consistency_score

    # 1. 问题相关性门槛（最重要）
    if top_relevance < 3:
        return ConvergenceDecision(
            action="CONTINUE",
            reason=f"最佳方案与用户问题相关性不足（{top_relevance}/5），需重新生成更贴合的方案",
            feedback=_generate_feedback(signals, max_ideality, top_relevance, top_consistency)
        )

    # 2. 逻辑一致性门槛
    if top_consistency < 3:
        return ConvergenceDecision(
            action="CONTINUE",
            reason=f"最佳方案逻辑不自洽（{top_consistency}/5），需修正方案描述",
            feedback=_generate_feedback(signals, max_ideality, top_relevance, top_consistency)
        )

    # 3. 信号清空判定
    if not signals:
        return ConvergenceDecision(
            action="TERMINATE",
            reason="信号已清空，矛盾已充分解决"
        )

    # 4. 高理想度提前终止
    if max_ideality >= HIGH_IDEALITY_THRESHOLD:
        return ConvergenceDecision(
            action="TERMINATE",
            reason=f"理想度 {max_ideality} 已达到较高水平，方案质量可接受"
        )

    # 5. 停滞判定
    if iteration > 0 and history:
        last_ideality = history[-1].get("max_ideality", 0)
        if max_ideality == last_ideality:
            return ConvergenceDecision(
                action="TERMINATE",
                reason=f"理想度停滞在 {max_ideality}，继续迭代无改善"
            )

    # 6. 收益递减判定
    if iteration >= 2 and len(history) >= 2:
        prev_ideality = history[-2].get("max_ideality", 0)
        improvement = max_ideality - prev_ideality
        if improvement < 0.05:
            return ConvergenceDecision(
                action="TERMINATE",
                reason=f"理想度改善率 {improvement:.3f} 低于阈值，收益递减"
            )

    # 7. 触达上限判定
    if iteration >= MAX_ITERATIONS:
        return ConvergenceDecision(
            action="TERMINATE",
            reason=f"达到最大迭代次数 {MAX_ITERATIONS}"
        )

    # 8. 理想度过低 -> CLARIFY
    if max_ideality < MIN_IDEALITY_THRESHOLD:
        return ConvergenceDecision(
            action="CLARIFY",
            reason=f"最高理想度 {max_ideality} 低于阈值 {MIN_IDEALITY_THRESHOLD}，需要用户补充信息"
        )

    # 9. CONTINUE
    return ConvergenceDecision(
        action="CONTINUE",
        reason=f"理想度 {max_ideality}（相关性 {top_relevance}/5，逻辑一致性 {top_consistency}/5），继续迭代优化",
        feedback=_generate_feedback(signals, max_ideality, top_relevance, top_consistency)
    )


def _generate_feedback(signals: list, max_ideality: float,
                       relevance: int, consistency: int) -> str:
    """生成给下一轮 M5 的反馈信息。"""
    feedback_parts = [
        f"上一轮最高理想度: {max_ideality}",
        f"问题相关性: {relevance}/5",
        f"逻辑一致性: {consistency}/5",
    ]
    if signals:
        feedback_parts.append(f"未解决问题: {', '.join(signals[:3])}")
    return "; ".join(feedback_parts)
