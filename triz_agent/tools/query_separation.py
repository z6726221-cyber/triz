"""分离原理查询 Tool：查询物理矛盾的分离原理。"""
from triz_agent.database.queries import get_separation_principles_by_type, get_all_separation_types


def query_separation(contradiction_desc: str) -> dict:
    """查询分离原理。

    参数:
        contradiction_desc: 物理矛盾描述

    返回: {"sep_type": str, "principles": list[int]}
    """
    sep_type = _classify_separation(contradiction_desc)
    principles = get_separation_principles_by_type(sep_type)

    if not principles:
        all_types = get_all_separation_types()
        all_prins = set()
        for t in all_types:
            all_prins.update(t.get("principles", []))
        principles = sorted(list(all_prins))

    return {"sep_type": sep_type, "principles": principles}


def _classify_separation(desc: str) -> str:
    """判定分离类型（空间/时间/条件/系统）。"""
    if any(kw in desc for kw in ["位置", "空间", "区域", "地方", "上面", "下面", "内部", "外部"]):
        return "空间"
    if any(kw in desc for kw in ["时间", "之前", "之后", "同时", "顺序", "阶段", "周期"]):
        return "时间"
    if any(kw in desc for kw in ["条件", "温度", "压力", "速度", "状态", "高", "低", "大", "小"]):
        return "条件"
    return "条件"
