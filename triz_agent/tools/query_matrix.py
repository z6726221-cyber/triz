"""矩阵查询 Tool：查询阿奇舒勒矛盾矩阵。"""
from triz_agent.database.queries import get_matrix_principles


# 通用推荐原理：当矩阵中无直接匹配时返回的最常用原理
FALLBACK_PRINCIPLES = [1, 15, 28, 35, 3, 27, 40, 2]


def query_matrix(improve_param_id: int, worsen_param_id: int) -> list[int]:
    """查询矛盾矩阵，返回发明原理列表。

    如果直接查询无结果，会尝试交换参数查询。
    如果仍然没有结果，返回通用推荐原理。

    参数:
        improve_param_id: 改善参数 ID (1-39)
        worsen_param_id: 恶化参数 ID (1-39)

    返回: 发明原理编号列表
    """
    # 直接查询
    result = get_matrix_principles(improve_param_id, worsen_param_id)
    if result:
        return result

    # 尝试交换参数查询（矩阵不完全对称）
    result = get_matrix_principles(worsen_param_id, improve_param_id)
    if result:
        return result

    # 返回通用推荐原理
    return FALLBACK_PRINCIPLES
