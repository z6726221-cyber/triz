"""M4 矛盾求解 Tool：双步参数映射 + 查表"""
import re
from typing import Optional
from triz.context import WorkflowContext
from triz.config import SIMILARITY_THRESHOLD
from triz.database.queries import (
    get_all_parameters, get_matrix_principles,
    get_separation_principles_by_type, get_all_separation_types
)
from triz.utils.vector_math import cosine_similarity, embed_text


# 关键词到参数ID的映射（fallback用）
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


def solve_contradiction(ctx: WorkflowContext) -> dict:
    """双步参数映射求解矛盾。"""
    if ctx.problem_type == "tech":
        return _solve_tech_contradiction(ctx)
    else:
        return _solve_phys_contradiction(ctx)


def _solve_tech_contradiction(ctx: WorkflowContext) -> dict:
    """技术矛盾：改善参数 -> 恶化参数 -> 查矩阵"""
    desc = ctx.contradiction_desc
    candidate_attrs = ctx.candidate_attributes or []

    # Step 1: 从矛盾描述中解析改善/恶化参数（自然语言）
    improve_attr = _parse_improve_param(desc)
    worsen_attr = _parse_worsen_param(desc)

    # 用 candidate_attributes 辅助消歧
    if not improve_attr and candidate_attrs:
        improve_attr = candidate_attrs[0]
    if not worsen_attr and len(candidate_attrs) > 1:
        worsen_attr = candidate_attrs[1]

    # Step 2: 余弦相似度匹配到 39 参数 ID
    improve_param_id = _match_param_id(improve_attr)
    worsen_param_id = _match_param_id(worsen_attr)

    # Step 3: 查阿奇舒勒矩阵
    principles = get_matrix_principles(improve_param_id, worsen_param_id)

    # 计算匹配置信度
    match_conf = 0.8 if improve_param_id and worsen_param_id else 0.5

    return {
        "principles": principles,
        "sep_type": None,
        "match_conf": match_conf,
        "improve_param_id": improve_param_id,
        "worsen_param_id": worsen_param_id,
        "need_state": None,
        "need_not_state": None,
    }


def _solve_phys_contradiction(ctx: WorkflowContext) -> dict:
    """物理矛盾：提取状态 -> 判定分离类型 -> 查分离规则库"""
    desc = ctx.contradiction_desc

    # 提取需要/不需要的状态
    need_state, need_not_state = _parse_phys_states(desc)

    # 判定分离类型
    sep_type = _classify_separation(need_state, need_not_state)

    # 查分离规则库
    principles = get_separation_principles_by_type(sep_type)

    # fallback: 如果该类型没有原理，返回所有分离类型的原理并集
    if not principles:
        all_types = get_all_separation_types()
        all_prins = set()
        for t in all_types:
            all_prins.update(t["principles"])
        principles = sorted(list(all_prins))

    return {
        "principles": principles,
        "sep_type": sep_type,
        "match_conf": 0.7,
        "improve_param_id": None,
        "worsen_param_id": None,
        "need_state": need_state,
        "need_not_state": need_not_state,
    }


def _parse_improve_param(desc: str) -> str:
    """从矛盾描述中提取改善参数。"""
    patterns = [
        r"改善(.+?)[，,、]",
        r"提升(.+?)[，,、]",
        r"增加(.+?)[，,、]",
        r"优化(.+?)[，,、]",
    ]
    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            return match.group(1).strip()
    if "导致" in desc:
        return desc.split("导致")[0].strip()
    if "，" in desc:
        return desc.split("，")[0].strip()
    return desc.strip()


def _parse_worsen_param(desc: str) -> str:
    """从矛盾描述中提取恶化参数。"""
    patterns = [
        r"恶化(.+)",
        r"损害(.+)",
        r"降低(.+)",
        r"导致(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            return match.group(1).strip()
    if "导致" in desc:
        parts = desc.split("导致")
        if len(parts) > 1:
            return parts[1].strip()
    if "，" in desc:
        parts = desc.split("，")
        if len(parts) > 1:
            return parts[1].strip()
    return ""


def _match_param_id(attribute: str) -> int:
    """将自然语言属性匹配到 39 参数 ID。
    策略：先查关键词映射表，再用余弦相似度匹配。
    """
    if not attribute:
        return 1  # fallback

    # 策略1: 关键词直接匹配
    for keyword, param_id in KEYWORD_PARAM_MAP.items():
        if keyword in attribute:
            return param_id

    # 策略2: 余弦相似度匹配
    all_params = get_all_parameters()
    attr_vec = embed_text(attribute)

    best_match = None
    best_score = -1.0
    for param in all_params:
        param_vec = embed_text(param["name"] + " " + param["name_cn"] + " " + param["description"])
        score = cosine_similarity(attr_vec, param_vec)
        if score > best_score:
            best_score = score
            best_match = param

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        return best_match["id"]

    return 1


def _parse_phys_states(desc: str) -> tuple:
    """从物理矛盾描述中提取需要/不需要的状态。"""
    match = re.search(r"(.+?)既要(.+?)又要(.+)", desc)
    if match:
        return match.group(2).strip(), match.group(3).strip()
    return desc, f"非{desc}"


def _classify_separation(need_state: str, need_not_state: str) -> str:
    """判定分离类型（空间/时间/条件/系统）。"""
    combined = f"{need_state} {need_not_state}"
    if any(kw in combined for kw in ["位置", "空间", "区域", "地方", "上面", "下面", "内部", "外部"]):
        return "空间"
    if any(kw in combined for kw in ["时间", "之前", "之后", "同时", "顺序", "阶段", "周期"]):
        return "时间"
    if any(kw in combined for kw in ["条件", "温度", "压力", "速度", "状态", "高", "低", "大", "小"]):
        return "条件"
    return "条件"
