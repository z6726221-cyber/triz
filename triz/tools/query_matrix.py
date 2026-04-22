"""矩阵查询 Tool：查询阿奇舒勒矛盾矩阵。"""
from triz.database.queries import get_matrix_principles


def query_matrix(improve_param_id: int, worsen_param_id: int) -> list[int]:
    """查询矛盾矩阵，返回发明原理列表。

    参数:
        improve_param_id: 改善参数 ID (1-39)
        worsen_param_id: 恶化参数 ID (1-39)

    返回: 发明原理编号列表
    """
    return get_matrix_principles(improve_param_id, worsen_param_id)
