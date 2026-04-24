from pydantic import BaseModel
from typing import List, Dict, Optional, Literal


class SAO(BaseModel):
    subject: str
    action: str
    object: str
    function_type: Literal["useful", "harmful", "excessive", "insufficient"]


class Case(BaseModel):
    principle_id: int
    source: str
    title: str
    description: str
    function: str


class SolutionDraft(BaseModel):
    title: str
    description: str
    applied_principles: List[int]
    resource_mapping: str


class QualitativeTags(BaseModel):
    feasibility_score: int              # 1-5
    resource_fit_score: int             # 1-5
    innovation_score: int               # 1-5
    uniqueness_score: int               # 1-5
    risk_level: Literal["low", "medium", "high", "critical"]
    ifr_deviation_reason: str
    problem_relevance_score: int = 3     # 1-5: 方案与用户问题的匹配度
    logical_consistency_score: int = 3   # 1-5: 方案描述是否自洽


class Solution(BaseModel):
    draft: SolutionDraft
    tags: QualitativeTags
    ideality_score: float       # LLM 综合评分（0-1）
    evaluation_rationale: str   # 评分依据说明


class WorkflowContext(BaseModel):
    # 输入
    question: str
    history: List[Dict] = []

    # M1 输出
    sao_list: List[SAO] = []
    resources: Dict[str, List[str]] = {}
    ifr: str = ""

    # M2 输出
    root_param: Optional[str] = None
    key_problem: Optional[str] = None
    candidate_attributes: List[str] = []
    causal_chain: List[str] = []

    # M3 输出
    problem_type: Optional[Literal["tech", "phys"]] = None
    improve_aspect: Optional[str] = None   # 需要改善的方面
    worsen_aspect: Optional[str] = None    # 随之恶化的方面
    contradiction_desc: str = ""  # 矛盾自然语言描述（兼容旧逻辑）
    evidence: List[str] = []      # 矛盾判定的支持证据（来自因果链）

    # M4 输出
    principles: List[int] = []
    sep_type: Optional[str] = None
    match_conf: float = 0.0
    improve_param_id: Optional[int] = None
    worsen_param_id: Optional[int] = None
    need_state: Optional[str] = None
    need_not_state: Optional[str] = None

    # FOS 输出
    cases: List[Case] = []

    # M5 输出
    solution_drafts: List[SolutionDraft] = []

    # M6 输出
    ranked_solutions: List[Solution] = []
    max_ideality: float = 0.0
    unresolved_signals: List[str] = []

    # 迭代控制
    iteration: int = 0
    history_log: List[Dict] = []
    feedback: str = ""


class ConvergenceDecision(BaseModel):
    action: Literal["CONTINUE", "TERMINATE", "CLARIFY"]
    reason: str
    feedback: str = ""
