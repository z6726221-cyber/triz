"""矛盾求解 Tool：根据矛盾类型查询发明原理（替代 M4 Skill）。"""

from triz_agent.tools.core.query_parameters import map_to_parameters
from triz_agent.tools.core.query_matrix import query_matrix
from triz_agent.tools.core.query_separation import query_separation


def solve_contradiction(ctx=None, **kwargs) -> dict:
    """根据矛盾类型查询发明原理。

    技术矛盾: map_to_parameters → query_matrix
    物理矛盾: 判断分离类型 → query_separation

    返回: {
        "principles": list[int],
        "problem_type": "tech" | "phys",
        "improve_param_id": int | None,
        "worsen_param_id": int | None,
        "parameter": str,        # 物理矛盾的矛盾参数
        "state1": str,           # 物理矛盾的状态1
        "state2": str,           # 物理矛盾的状态2
        "sep_type": str | None,   # 物理矛盾的分离类型
    }
    """
    # 从 ctx 或 kwargs 提取参数
    if ctx is not None and hasattr(ctx, "problem_type"):
        problem_type = getattr(ctx, "problem_type", "tech")
        improve_aspect = getattr(ctx, "improve_aspect", "") or ""
        worsen_aspect = getattr(ctx, "worsen_aspect", "") or ""
        contradiction_desc = getattr(ctx, "contradiction_desc", "") or ""
        parameter = getattr(ctx, "parameter", "") or ""
        state1 = getattr(ctx, "state1", "") or ""
        state2 = getattr(ctx, "state2", "") or ""
        sep_type = getattr(ctx, "sep_type", "") or ""
    else:
        problem_type = kwargs.get("problem_type", "tech")
        improve_aspect = kwargs.get("improve_aspect", "")
        worsen_aspect = kwargs.get("worsen_aspect", "")
        contradiction_desc = kwargs.get("contradiction_desc", "")
        parameter = kwargs.get("parameter", "")
        state1 = kwargs.get("state1", "")
        state2 = kwargs.get("state2", "")
        sep_type = kwargs.get("sep_type", "")

    if problem_type == "phys":
        return _solve_physical(
            parameter=parameter,
            state1=state1,
            state2=state2,
            sep_type=sep_type,
            contradiction_desc=contradiction_desc,
        )

    # 技术矛盾：优先用 improve/worsen_aspect，否则从 candidate_attributes 推断
    return _solve_technical(improve_aspect, worsen_aspect, kwargs)


def _solve_physical(
    parameter: str,
    state1: str,
    state2: str,
    sep_type: str,
    contradiction_desc: str,
) -> dict:
    """处理物理矛盾：根据分离类型查询分离原理。"""
    # 如果有明确的分离类型，直接使用
    if sep_type:
        principles = query_separation(sep_type=sep_type)
    else:
        # 否则根据矛盾描述自动判断
        principles = query_separation(contradiction_desc=contradiction_desc)

    # 再尝试从 contradiction_desc 或 keywords 兜底
    if not principles:
        principles = query_separation(contradiction_desc=contradiction_desc)

    return {
        "problem_type": "phys",
        "principles": principles,
        "parameter": parameter,
        "state1": state1,
        "state2": state2,
        "sep_type": sep_type or "时间",
        "improve_param_id": None,
        "worsen_param_id": None,
    }


def _solve_technical(improve_aspect: str, worsen_aspect: str, kwargs: dict) -> dict:
    """处理技术矛盾：映射到39参数 → 查矛盾矩阵。"""
    imp = improve_aspect
    wors = worsen_aspect

    candidate_attributes = kwargs.get("candidate_attributes", []) or []
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
                "problem_type": "tech",
                "principles": principles,
                "improve_param_id": imp_id,
                "worsen_param_id": wors_id,
                "match_conf": round(avg_score, 3),
                "sep_type": None,
                "parameter": "",
                "state1": "",
                "state2": "",
            }

    # 兜底：从 contradiction_desc 或 candidate_attributes 关键词查询
    from triz_agent.tools.core.query_parameters import query_parameters

    keywords = candidate_attributes or []
    if "contradiction_desc" in kwargs:
        keywords.append(kwargs["contradiction_desc"][:20])

    params = query_parameters(keywords)
    if len(params) >= 2:
        principles = query_matrix(params[0]["id"], params[1]["id"])
        return {
            "problem_type": "tech",
            "principles": principles,
            "improve_param_id": params[0]["id"],
            "worsen_param_id": params[1]["id"],
            "match_conf": 0.5,
            "sep_type": None,
            "parameter": "",
            "state1": "",
            "state2": "",
        }
    elif len(params) == 1:
        principles = query_matrix(params[0]["id"], 39)
        return {
            "problem_type": "tech",
            "principles": principles,
            "improve_param_id": params[0]["id"],
            "worsen_param_id": 39,
            "match_conf": 0.5,
            "sep_type": None,
            "parameter": "",
            "state1": "",
            "state2": "",
        }

    return {
        "problem_type": "tech",
        "principles": [],
        "improve_param_id": None,
        "worsen_param_id": None,
        "match_conf": 0.0,
        "sep_type": None,
        "parameter": "",
        "state1": "",
        "state2": "",
    }
