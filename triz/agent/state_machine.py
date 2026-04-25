"""TRIZ Agent 状态机：定义合法的状态跳转规则。"""

# 状态 → 允许跳转的下一状态列表
STATE_MACHINE: dict[str, list[str]] = {
    "idle": ["modeling"],
    "modeling": ["causal", "formulation"],
    "causal": ["formulation"],
    "formulation": ["solving"],
    "solving": ["search"],
    "search": ["generation"],
    "generation": ["evaluation"],
    "evaluation": ["convergence"],
    "convergence": ["solving", "report_generation"],
    "report_generation": [],  # 终止状态
}

# 状态 → 该状态下可用的 Skill/Tool 名称
# 注意：convergence 不是 Skill，是内部判断逻辑
STATE_SKILLS: dict[str, list[str]] = {
    "idle": [],
    "modeling": ["m1_modeling", "m2_causal", "m3_formulation"],
    "causal": ["m2_causal"],
    "formulation": ["m3_formulation"],
    "solving": ["m4_solver"],  # 实际是 Tool (solve_contradiction)，Agent 内部路由
    "search": ["FOS"],
    "generation": ["m5_generation"],
    "evaluation": ["m6_evaluation"],
    "convergence": [],  # 由 check_convergence() 处理
    "report_generation": [],  # 由 render_final_report() 处理
}

# 状态的中文名称（用于回调通知）
STATE_NAMES: dict[str, str] = {
    "idle": "等待开始",
    "modeling": "问题建模",
    "causal": "根因分析",
    "formulation": "问题定型",
    "solving": "矛盾求解",
    "search": "跨界检索",
    "generation": "方案生成",
    "evaluation": "方案评估",
    "convergence": "收敛判断",
    "report_generation": "报告生成",
}


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """检查从 from_state 跳转到 to_state 是否合法。"""
    if from_state not in STATE_MACHINE:
        return False
    return to_state in STATE_MACHINE[from_state]


def get_available_skills(state: str) -> list[str]:
    """获取指定状态下可用的 Skill 列表。"""
    return STATE_SKILLS.get(state, [])


def get_state_name(state: str) -> str:
    """获取状态的中文名称。"""
    return STATE_NAMES.get(state, state)