"""参数查询 Tool：将自然语言属性匹配到 39 工程参数。"""
from triz.config import SIMILARITY_THRESHOLD
from triz.database.queries import get_all_parameters
from triz.utils.vector_math import cosine_similarity, embed_text


KEYWORD_PARAM_MAP = {
    "速度": 9, "speed": 9, "快": 9, "慢": 9,
    "力": 10, "force": 10, "压力": 11, "强度": 14, "strength": 14,
    "形状": 12, "shape": 12, "形态": 12,
    "稳定": 13, "稳定性": 13, "可靠": 27, "可靠性": 27,
    "重量": 1, "质量": 1, "weight": 1,
    "面积": 5, "area": 5, "体积": 7, "volume": 7,
    "温度": 17, "temperature": 17, "热": 17,
    "能量": 19, "energy": 19, "功率": 21, "power": 21,
    "时间": 25, "time": 25, "损耗": 22,
    "精度": 28, "accuracy": 28, "制造": 32,
    "复杂": 36, "complexity": 36, "生产率": 39, "productivity": 39,
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
