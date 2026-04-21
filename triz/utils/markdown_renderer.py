"""Markdown 渲染工具：将节点输出和最终结果渲染为 Markdown"""
from triz.context import WorkflowContext, Solution


def render_node_start(node_name: str, current: int, total: int) -> str:
    return f"\n## [节点 {current}/{total}] {node_name}\n"


def render_step_complete(step_name: str, step_type: str, result: dict) -> str:
    type_icon = "Skill" if step_type == "Skill" else "Tool"
    return f"- {type_icon}: {step_name}...\n"


def render_node_complete(node_name: str, ctx: WorkflowContext) -> str:
    """根据节点类型渲染具体输出内容。"""
    output = ""
    if node_name == "问题建模":
        output += _render_problem_modeling(ctx)
    elif node_name == "矛盾求解":
        output += _render_contradiction_solver(ctx)
    elif node_name == "跨界检索":
        output += _render_fos_results(ctx)
    elif node_name == "方案生成":
        output += _render_solution_generation(ctx)
    elif node_name == "方案评估":
        output += _render_solution_evaluation(ctx)
    output += "\n---\n"
    return output


def _render_problem_modeling(ctx: WorkflowContext) -> str:
    lines = []
    if ctx.sao_list:
        lines.append("### 功能建模")
        for sao in ctx.sao_list:
            lines.append(f"- [{sao.subject}] -> [{sao.action}] -> [{sao.object}] ({sao.function_type})")
    if ctx.ifr:
        lines.append(f"- **IFR**: {ctx.ifr}")
    if ctx.resources:
        lines.append(f"- **资源**: {ctx.resources}")

    if ctx.root_param:
        lines.append("\n### 根因分析")
        lines.append(f"- **根因**: {ctx.root_param}")
        if ctx.candidate_attributes:
            lines.append(f"- **候选属性**: {ctx.candidate_attributes}")

    if ctx.contradiction_desc:
        lines.append(f"\n### 矛盾定型")
        lines.append(f"- **类型**: {ctx.problem_type}")
        lines.append(f"- **描述**: {ctx.contradiction_desc}")

    return "\n".join(lines)


def _render_contradiction_solver(ctx: WorkflowContext) -> str:
    lines = ["### 矛盾求解"]
    if ctx.improve_param_id:
        lines.append(f"- **改善参数**: #{ctx.improve_param_id}")
    if ctx.worsen_param_id:
        lines.append(f"- **恶化参数**: #{ctx.worsen_param_id}")
    if ctx.sep_type:
        lines.append(f"- **分离类型**: {ctx.sep_type}")
    if ctx.principles:
        lines.append(f"- **发明原理**: {ctx.principles}")
    return "\n".join(lines)


def _render_fos_results(ctx: WorkflowContext) -> str:
    lines = ["### 跨界检索"]
    if ctx.cases:
        for case in ctx.cases[:5]:
            lines.append(f"- [{case.source}] {case.title}: {case.description}")
    else:
        lines.append("- 未召回跨界案例")
    return "\n".join(lines)


def _render_solution_generation(ctx: WorkflowContext) -> str:
    lines = ["### 方案生成"]
    if ctx.solution_drafts:
        lines.append(f"- 生成方案草稿 x{len(ctx.solution_drafts)}")
        for draft in ctx.solution_drafts:
            lines.append(f"  - {draft.title}: {draft.description[:50]}...")
    return "\n".join(lines)


def _render_solution_evaluation(ctx: WorkflowContext) -> str:
    lines = ["### 方案评估"]
    if ctx.ranked_solutions:
        top = ctx.ranked_solutions[0]
        lines.append(f"- 最高理想度: {top.ideality_score:.2f}")
        lines.append(f"- 最佳方案: {top.draft.title}")
    return "\n".join(lines)


def render_final_report(question: str, contradiction: str, solutions: list[Solution], reason: str) -> str:
    lines = [
        "# TRIZ 解决方案报告",
        "",
        f"## 问题",
        question,
        "",
        f"## 核心矛盾",
        contradiction,
        "",
        "## 推荐方案（按理想度排序）",
        "",
    ]

    for i, sol in enumerate(solutions[:3], 1):
        lines.extend([
            f"### 方案 {i} [理想度: {sol.ideality_score:.2f}]",
            f"**原理**: {sol.draft.applied_principles}",
            f"**标题**: {sol.draft.title}",
            f"**描述**: {sol.draft.description}",
            f"**可行性**: {sol.tags.feasibility_score}/5 | 风险: {sol.tags.risk_level}",
            "",
        ])

    lines.extend([
        "## 评估依据",
        reason,
    ])

    return "\n".join(lines)
