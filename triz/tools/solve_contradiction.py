"""矛盾求解 Tool：根据矛盾类型查询发明原理（替代 M4 Skill）。"""
from triz.tools.query_parameters import map_to_parameters
from triz.tools.query_matrix import query_matrix
from triz.tools.query_separation import query_separation


def solve_contradiction(ctx=None, **kwargs) -> dict:
    """根据矛盾类型查询发明原理。

    可接收 WorkflowContext 对象或关键字参数。

    技术矛盾: map_to_parameters → query_matrix
    物理矛盾: query_separation

    返回: {
        "principles": list[int],
        "improve_param_id": int | None,
        "worsen_param_id": int | None,
        "match_conf": float,
        "sep_type": str | None,
    }
    """
    # 从 ctx 或 kwargs 提取参数
    if ctx is not None and hasattr(ctx, "problem_type"):
        problem_type = getattr(ctx, "problem_type", "tech")
        improve_aspect = getattr(ctx, "improve_aspect", "") or ""
        worsen_aspect = getattr(ctx, "worsen_aspect", "") or ""
        contradiction_desc = getattr(ctx, "contradiction_desc", "") or ""
        candidate_attributes = getattr(ctx, "candidate_attributes", []) or []
    else:
        problem_type = kwargs.get("problem_type", "tech")
        improve_aspect = kwargs.get("improve_aspect", "")
        worsen_aspect = kwargs.get("worsen_aspect", "")
        contradiction_desc = kwargs.get("contradiction_desc", "")
        candidate_attributes = kwargs.get("candidate_attributes", []) or []

    candidate_attributes = candidate_attributes or []

    if problem_type == "phys":
        result = query_separation(contradiction_desc)
        return {
            "principles": result["principles"],
            "improve_param_id": None,
            "worsen_param_id": None,
            "match_conf": 0.5,
            "sep_type": result["sep_type"],
        }

    # 技术矛盾：优先用 improve/worsen_aspect，否则从 candidate_attributes 推断
    imp = improve_aspect
    wors = worsen_aspect

    if not imp and candidate_attributes:
        imp = candidate_attributes[0]
    if not wors and len(candidate_attributes) > 1:
        wors = candidate_attributes[1]

    if imp and wors:
        mapping = map_to_parameters(imp, wors)
        imp_id = mapping["improve_param_id"]
        wors_id = mapping["worsen_param_id"]

        if imp_id and wors_id:
            principles = query_matrix(imp_id, wors_id)
            avg_score = (mapping["improve_score"] + mapping["worsen_score"]) / 2
            return {
                "principles": principles,
                "improve_param_id": imp_id,
                "worsen_param_id": wors_id,
                "match_conf": round(avg_score, 3),
                "sep_type": None,
            }

    # 兜底：从 contradiction_desc 或 candidate_attributes 关键词查询
    from triz.tools.query_parameters import query_parameters
    keywords = candidate_attributes or []
    if contradiction_desc:
        keywords.append(contradiction_desc[:20])

    params = query_parameters(keywords)
    if len(params) >= 2:
        principles = query_matrix(params[0]["id"], params[1]["id"])
        return {
            "principles": principles,
            "improve_param_id": params[0]["id"],
            "worsen_param_id": params[1]["id"],
            "match_conf": 0.5,
            "sep_type": None,
        }
    elif len(params) == 1:
        principles = query_matrix(params[0]["id"], 39)
        return {
            "principles": principles,
            "improve_param_id": params[0]["id"],
            "worsen_param_id": 39,
            "match_conf": 0.5,
            "sep_type": None,
        }

    return {
        "principles": [],
        "improve_param_id": None,
        "worsen_param_id": None,
        "match_conf": 0.0,
        "sep_type": None,
    }
