"""分离原理查询 Tool：查询物理矛盾的分离原理。

优先从数据库查询，数据库为空时用内置经典 TRIZ 分离规则兜底。
"""

import json
from triz_agent.database.queries import (
    get_separation_principles_by_type,
    get_all_separation_types,
)

# 经典 TRIZ 分离规则（代码级兜底）
SEPARATION_RULES = {
    "空间": [1, 2, 3, 4, 7, 14, 17, 24, 26, 30],
    "时间": [9, 10, 11, 15, 16, 19, 20, 21, 34, 35],
    "条件": [13, 25, 27, 28, 29, 31, 32, 35, 36, 39],
    "系统": [5, 6, 8, 12, 13, 18, 22, 25, 27, 33],
}

# 分离类型判断关键词
SEP_KEYWORDS = {
    "空间": ["位置", "空间", "区域", "地方", "上面", "下面", "内部", "外部", "局部", "整体"],
    "时间": ["时间", "之前", "之后", "同时", "顺序", "阶段", "周期", "书写", "停笔", "工作", "闲置", "白天", "夜晚"],
    "条件": ["条件", "温度", "压力", "速度", "状态", "高", "低", "大", "小", "热", "冷", "膨胀", "收缩", "快", "慢"],
    "系统": ["组件", "系统", "子系统", "超系统", "层级", "整体", "部分"],
}


def query_separation(
    contradiction_desc: str = "",
    sep_type: str = "",
) -> list[int]:
    """查询分离原理。

    参数:
        contradiction_desc: 物理矛盾描述（用于自动判断分离类型）
        sep_type: 分离类型（空间/时间/条件/系统），直接指定时优先使用

    返回: 发明原理编号列表
    """
    # 优先使用直接指定的分离类型
    if sep_type and sep_type in SEPARATION_RULES:
        return SEPARATION_RULES[sep_type]

    # 从数据库查询
    if sep_type:
        principles = get_separation_principles_by_type(sep_type)
        if principles:
            return principles

    # 根据矛盾描述自动推断分离类型
    inferred = _classify_separation(contradiction_desc) if contradiction_desc else "时间"

    # 先试数据库
    principles = get_separation_principles_by_type(inferred)
    if principles:
        return principles

    # 数据库无数据，用代码规则兜底
    return SEPARATION_RULES.get(inferred, SEPARATION_RULES["时间"])


def _classify_separation(desc: str) -> str:
    """根据矛盾描述判定分离类型。"""
    if not desc:
        return "时间"

    for sep_type, keywords in SEP_KEYWORDS.items():
        if any(kw in desc for kw in keywords):
            return sep_type

    return "时间"  # 默认时间分离（最常见）
