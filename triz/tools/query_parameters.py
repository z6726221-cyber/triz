"""参数查询 Tool：将自然语言属性匹配到 39 工程参数。"""
from triz.config import SIMILARITY_THRESHOLD
from triz.database.queries import get_all_parameters
from triz.utils.vector_math import cosine_similarity, embed_text


KEYWORD_PARAM_MAP = {
    # 运动/静止物体属性
    "速度": 9, "speed": 9, "快": 9, "慢": 9,
    "重量": 1, "质量": 1, "weight": 1, "mass": 1,
    "长度": 3, "length": 3, "尺寸": 3,
    "面积": 5, "area": 5, "空间": 5,
    "体积": 7, "volume": 7, "容量": 7,
    "形状": 12, "shape": 12, "形态": 12, "结构": 12,

    # 力学属性
    "力": 10, "force": 10, "作用力": 10,
    "压力": 11, "应力": 11, "压强": 11, "stress": 11, "pressure": 11,
    "强度": 14, "strength": 14, "硬度": 14, "刚性": 14, "硬性": 14,
    "韧性": 14, "脆性": 14, "易碎": 14, "坚固": 14,

    # 耐久/磨损
    "耐久性": 16, "耐用性": 16, "耐磨性": 16, "磨损": 16,
    "durability": 16, "wear": 16, "abrasion": 16, "fatigue": 16,
    "使用寿命": 16, "寿命": 16, "老化": 16, "退化": 16,
    "耐久": 16, "耐用": 16, "耐磨": 16,

    # 稳定性与可靠性
    "稳定": 13, "稳定性": 13, "稳固": 13,
    "可靠": 27, "可靠性": 27, "reliability": 27, "可信": 27,
    "安全": 27, "安全性": 27, "safety": 27,

    # 能量与功率
    "温度": 17, "temperature": 17, "热": 17, "冷": 17, "保温": 17,
    "能量": 19, "energy": 19, "能耗": 19, "消耗": 19,
    "功率": 21, "power": 21, "效率": 21,
    "能量损失": 22, "损耗": 22, "浪费": 22, "loss": 22,

    # 时间
    "时间": 25, "time": 25, "周期": 25, "延迟": 25, "速度损失": 25,

    # 精度与制造
    "精度": 28, "accuracy": 28, "精确": 28, "误差": 28,
    "制造精度": 29, "工艺": 29, "加工": 29,
    "制造": 32, "可制造": 32, "工艺性": 32, " manufacturability": 32,
    "使用": 33, "便利": 33, "方便": 33, "操作": 33,
    "维修": 34, "维护": 34, "修复": 34, "保养": 34,

    # 有害因素
    "有害": 30, "危害": 30, "损伤": 30, "破坏": 30, "harm": 30,
    "副作用": 31, "负面": 31, "不良": 31, "side effect": 31,
    "物质损失": 23, "材料损失": 23, "消耗": 23, "浪费材料": 23, "崩刃": 23,

    # 复杂性与适应性
    "复杂": 36, "复杂性": 36, "complicated": 36, "complexity": 36,
    "简单": 36, "简化": 36,
    "适应性": 35, "通用": 35, "灵活": 35, "adaptability": 35,
    "检测": 37, "测量": 37, "监控": 37, "检测难度": 37,
    "自动化": 38, "自动": 38, "智能": 38, "无人": 38,
    "生产率": 39, "产能": 39, "效率": 39, "productivity": 39, "output": 39,

    # 信息
    "信息": 24, "数据": 24, "信号": 24, "information": 24,
    "物质的量": 26, "数量": 26, "amount": 26, "quantity": 26,

    # 照度
    "照度": 18, "亮度": 18, "光照": 18, "illumination": 18, "light": 18,
}


def query_parameters(keywords: list[str]) -> list[dict]:
    """根据关键词查询最匹配的 39 工程参数。

    返回: [{"id": int, "name": str, "name_cn": str, "similarity": float, "match_type": str}, ...]
    """
    if not keywords:
        return []

    all_params = get_all_parameters()
    results = []
    seen_ids = set()

    for keyword in keywords:
        if not keyword:
            continue

        # 策略1: 关键词直接匹配
        matched = False
        for kw, param_id in KEYWORD_PARAM_MAP.items():
            if kw in keyword:
                if param_id not in seen_ids:
                    for param in all_params:
                        if param["id"] == param_id:
                            results.append({
                                "id": param_id,
                                "name": param["name"],
                                "name_cn": param["name_cn"],
                                "similarity": 1.0,
                                "match_type": "keyword",
                            })
                            seen_ids.add(param_id)
                            break
                matched = True
                break

        if matched:
            continue

        # 策略2: 余弦相似度匹配
        attr_vec = embed_text(keyword)
        best_match = None
        best_score = -1.0

        for param in all_params:
            desc = param.get("description", "")
            param_vec = embed_text(f"{param['name']} {param['name_cn']} {desc}")
            score = cosine_similarity(attr_vec, param_vec)
            if score > best_score:
                best_score = score
                best_match = param

        if best_match and best_score >= SIMILARITY_THRESHOLD:
            if best_match["id"] not in seen_ids:
                results.append({
                    "id": best_match["id"],
                    "name": best_match["name"],
                    "name_cn": best_match["name_cn"],
                    "similarity": best_score,
                    "match_type": "similarity",
                })
                seen_ids.add(best_match["id"])

    return results
