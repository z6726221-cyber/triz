"""参数查询 Tool：将中文描述映射到 39 工程参数 ID。

策略：
1. 精确关键词匹配（KEYWORD_PARAM_MAP）— 快速路径
2. 语义相似度匹配（预计算 embedding + 余弦相似度）
"""

from typing import Optional
from triz_pipeline.config import SIMILARITY_THRESHOLD
from triz_pipeline.database.queries import get_all_parameters
from triz_pipeline.utils.vector_math import cosine_similarity, embed_text

# 精简关键词映射：只覆盖最常见的工程属性词
KEYWORD_PARAM_MAP = {
    # 运动/静止物体属性
    "速度": 9,
    "speed": 9,
    "快": 9,
    "慢": 9,
    "重量": 1,
    "质量": 1,
    "weight": 1,
    "mass": 1,
    "长度": 3,
    "length": 3,
    "尺寸": 3,
    "大小": 3,
    "面积": 5,
    "area": 5,
    "空间": 5,
    "体积": 7,
    "volume": 7,
    "容量": 7,
    "容积": 7,
    "形状": 12,
    "shape": 12,
    "形态": 12,
    "结构": 12,
    # 力学属性
    "力": 10,
    "force": 10,
    "作用力": 10,
    "压力": 11,
    "应力": 11,
    "压强": 11,
    "stress": 11,
    "pressure": 11,
    "波动": 11,
    "震荡": 11,
    "振荡": 11,
    "振动": 31,
    "强度": 14,
    "strength": 14,
    "硬度": 14,
    "刚性": 14,
    "韧性": 14,
    "脆性": 14,
    "坚固": 14,
    "抗震": 14,
    "防震": 14,
    "抗冲击": 14,
    "承载": 14,
    # 耐久/磨损
    "耐久": 16,
    "耐用": 16,
    "耐磨": 16,
    "磨损": 16,
    "durability": 16,
    "wear": 16,
    "fatigue": 16,
    "寿命": 16,
    "老化": 16,
    "退化": 16,
    # 稳定性与可靠性
    "稳定": 13,
    "稳定性": 13,
    "稳固": 13,
    "可靠": 27,
    "可靠性": 27,
    "reliability": 27,
    "安全": 27,
    "安全性": 27,
    "safety": 27,
    "地震": 27,
    "灾害": 27,
    "风险": 27,
    # 能量与功率
    "温度": 17,
    "temperature": 17,
    "热": 17,
    "冷": 17,
    "保温": 17,
    "能量": 19,
    "energy": 19,
    "能耗": 19,
    "消耗": 19,
    "油耗": 22,
    "耗油": 22,
    "燃油": 19,
    "耗能": 22,
    "燃料": 19,
    "功率": 21,
    "power": 21,
    "效率": 21,
    "效能": 21,
    "损失": 22,
    "损耗": 22,
    "浪费": 22,
    "loss": 22,
    # 时间
    "时间": 25,
    "time": 25,
    "周期": 25,
    "延迟": 25,
    # 精度与制造
    "精度": 28,
    "accuracy": 28,
    "精确": 28,
    "误差": 28,
    "制造": 32,
    "工艺": 29,
    "加工": 29,
    " manufacturability": 32,
    "可制造": 32,
    "使用": 33,
    "便利": 33,
    "方便": 33,
    "操作": 33,
    "维修": 34,
    "维护": 34,
    "修复": 34,
    "保养": 34,
    # 有害因素
    "有害": 30,
    "危害": 30,
    "损伤": 30,
    "破坏": 30,
    "harm": 30,
    "副作用": 31,
    "负面": 31,
    "不良": 31,
    "side effect": 31,
    "噪音": 31,
    "噪声": 31,
    "声": 31,
    "响": 31,
    "异响": 31,
    "物质损失": 23,
    "材料损失": 23,
    "消耗材料": 23,
    # 成本与经济
    "成本": 32,
    "费用": 32,
    "造价": 32,
    "经济": 32,
    "预算": 32,
    "投资": 32,
    "花费": 32,
    "开支": 32,
    "价格": 32,
    # 复杂性与适应性
    "复杂": 36,
    "复杂性": 36,
    "complicated": 36,
    "complexity": 36,
    "简单": 36,
    "简化": 36,
    "适应性": 35,
    "通用": 35,
    "灵活": 35,
    "adaptability": 35,
    "检测": 37,
    "测量": 37,
    "监控": 37,
    "自动化": 38,
    "自动": 38,
    "智能": 38,
    "无人": 38,
    "生产率": 39,
    "产能": 39,
    "productivity": 39,
    "output": 39,
    # 信息
    "信息": 24,
    "数据": 24,
    "信号": 24,
    "information": 24,
    "物质的量": 26,
    "数量": 26,
    "amount": 26,
    "quantity": 26,
    # 照度
    "照度": 18,
    "亮度": 18,
    "光照": 18,
    "illumination": 18,
    "light": 18,
    # 燃烧相关
    "燃烧": 21,
    "燃烧效率": 21,
    "燃烧性能": 21,
    "排放": 31,
    "尾气": 31,
    "废气": 31,
    "污染": 31,
}

# 预加载参数（含 embedding），延迟初始化
_param_cache: list[dict] = []


def _load_params():
    """从 DB 加载参数（含预计算的 embedding）。"""
    global _param_cache
    if _param_cache:
        return
    _param_cache = get_all_parameters()


def _match_aspect(aspect: str) -> tuple[Optional[int], str, float]:
    """将单个中文描述匹配到参数 ID。

    返回: (param_id, match_type, score)
    - match_type: "keyword" | "semantic" | "none"
    """
    if not aspect:
        return None, "none", 0.0

    # 策略1: 精确关键词匹配（快速路径）
    for kw, param_id in KEYWORD_PARAM_MAP.items():
        if kw in aspect:
            return param_id, "keyword", 1.0

    # 策略2: 语义相似度匹配（使用预计算的 embedding）
    _load_params()
    aspect_vec = embed_text(aspect)
    if not aspect_vec:
        return None, "none", 0.0

    best_id = None
    best_score = -1.0
    for param in _param_cache:
        param_vec = param.get("embedding")
        if not param_vec:
            continue
        score = cosine_similarity(aspect_vec, param_vec)
        if score > best_score:
            best_score = score
            best_id = param["id"]

    threshold = SIMILARITY_THRESHOLD * 0.75  # 语义匹配阈值略低
    if best_id and best_score >= threshold:
        return best_id, "semantic", round(best_score, 3)

    return None, "none", 0.0


def map_to_parameters(improve_aspect: str, worsen_aspect: str) -> dict:
    """将矛盾的两个方面映射到 39 个 TRIZ 工程参数 ID。

    参数:
        improve_aspect: 需要改善的方面（2-6个中文词）
        worsen_aspect: 随之恶化的方面（2-6个中文词）

    返回:
        {
            "improve_param_id": int | None,
            "worsen_param_id": int | None,
            "improve_match_type": "keyword" | "semantic" | "none",
            "worsen_match_type": "keyword" | "semantic" | "none",
            "improve_score": float,
            "worsen_score": float,
        }
    """
    imp_id, imp_type, imp_score = _match_aspect(improve_aspect)
    wors_id, wors_type, wors_score = _match_aspect(worsen_aspect)

    return {
        "improve_param_id": imp_id,
        "worsen_param_id": wors_id,
        "improve_match_type": imp_type,
        "worsen_match_type": wors_type,
        "improve_score": imp_score,
        "worsen_score": wors_score,
    }


def query_parameters(keywords: list[str]) -> list[dict]:
    """根据关键词查询最匹配的 39 工程参数。

    返回: [{"id": int, "name": str, "name_cn": str, "similarity": float, "match_type": str}, ...]
    """
    _load_params()
    results = []
    seen_ids = set()

    for keyword in keywords:
        if not keyword:
            continue

        # 尝试关键词匹配
        matched = False
        for kw, param_id in KEYWORD_PARAM_MAP.items():
            if kw in keyword:
                if param_id not in seen_ids:
                    for param in _param_cache:
                        if param["id"] == param_id:
                            results.append(
                                {
                                    "id": param_id,
                                    "name": param["name"],
                                    "name_cn": param["name_cn"],
                                    "similarity": 1.0,
                                    "match_type": "keyword",
                                }
                            )
                            seen_ids.add(param_id)
                            break
                matched = True
                break

        if matched:
            continue

        # 语义相似度匹配（使用预计算的 embedding）
        attr_vec = embed_text(keyword)
        if not attr_vec:
            continue

        best_match = None
        best_score = -1.0
        for param in _param_cache:
            param_vec = param.get("embedding")
            if not param_vec:
                continue
            score = cosine_similarity(attr_vec, param_vec)
            if score > best_score:
                best_score = score
                best_match = param

        if best_match and best_score >= SIMILARITY_THRESHOLD:
            if best_match["id"] not in seen_ids:
                results.append(
                    {
                        "id": best_match["id"],
                        "name": best_match["name"],
                        "name_cn": best_match["name_cn"],
                        "similarity": best_score,
                        "match_type": "similarity",
                    }
                )
                seen_ids.add(best_match["id"])

    return results
