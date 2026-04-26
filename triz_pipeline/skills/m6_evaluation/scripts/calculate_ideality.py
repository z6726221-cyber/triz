"""理想度计算：确定性函数，不调 LLM。"""

from typing import Any


def calculate_ideality(solution: dict[str, Any]) -> float:
    """计算单个方案的理想度分数。

    公式：加权平均 → 归一化到 0.0-1.0

    权重：
    - feasibility_score: 20%
    - resource_fit_score: 15%
    - innovation_score: 15%
    - uniqueness_score: 10%
    - risk_level: 10%（反向计算）
    - problem_relevance_score: 20%
    - logical_consistency_score: 10%
    """
    # 基础分数（直接取值）
    feasibility = solution.get("feasibility_score", 3)
    resource_fit = solution.get("resource_fit_score", 3)
    innovation = solution.get("innovation_score", 3)
    uniqueness = solution.get("uniqueness_score", 3)
    relevance = solution.get("problem_relevance_score", 3)
    consistency = solution.get("logical_consistency_score", 3)

    # risk_level 反向计算
    risk_map = {"low": 5, "medium": 3, "high": 1, "critical": 0}
    risk = risk_map.get(solution.get("risk_level", "medium"), 3)

    # 加权平均（满分 5 分）
    weighted = (
        feasibility * 0.20
        + resource_fit * 0.15
        + innovation * 0.15
        + uniqueness * 0.10
        + risk * 0.10
        + relevance * 0.20
        + consistency * 0.10
    )

    # 归一化到 0.0-1.0
    ideality = weighted / 5.0

    # 硬约束
    if relevance < 3:
        ideality = min(ideality, 0.5)
    if consistency < 3:
        ideality = min(ideality, 0.6)

    return round(ideality, 2)


def recalculate_all(solutions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """重新计算所有方案的理想度并排序。"""
    for s in solutions:
        s["ideality_score"] = calculate_ideality(s)

    # 按理想度降序排序
    solutions.sort(key=lambda x: x.get("ideality_score", 0), reverse=True)

    return solutions
