"""测试辅助函数。"""
from triz_pipeline.context import WorkflowContext


def formulate_problem(ctx: WorkflowContext) -> dict:
    """从 M2 的根因输出中提取矛盾类型和矛盾描述。"""
    root_param = ctx.root_param or ""
    key_problem = ctx.key_problem or ""
    evidence = ctx.causal_chain.copy() if ctx.causal_chain else []

    combined_text = f"{root_param} {key_problem}"
    if "既要" in combined_text or "又要" in combined_text or "同时" in combined_text:
        problem_type = "phys"
    else:
        problem_type = "tech"

    contradiction_desc = _extract_contradiction_desc(problem_type, root_param, key_problem)

    return {
        "problem_type": problem_type,
        "contradiction_desc": contradiction_desc,
        "evidence": evidence,
    }


def _extract_contradiction_desc(problem_type: str, root_param: str, key_problem: str) -> str:
    """从根因文本中提取矛盾描述。"""
    combined = f"{root_param} {key_problem}".strip()

    if not combined:
        return "未识别矛盾"

    if problem_type == "phys":
        if "既要" in root_param:
            return root_param
        return f"{root_param}存在物理矛盾"
    else:
        if "导致" in combined or "恶化" in combined or "影响" in combined:
            return combined
        return f"改善{root_param}导致{key_problem}"
