import pytest
import os
from triz.context import WorkflowContext, SAO, ConvergenceDecision, Solution, SolutionDraft, QualitativeTags
from tests.helpers import formulate_problem
from triz.tools.m7_convergence import check_convergence
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.fos_search import search_cases
from triz.database.init_db import init_database


def _make_solution(relevance=5, consistency=5, ideality=0.7):
    """辅助函数：创建测试用的 Solution"""
    return Solution(
        draft=SolutionDraft(
            title="测试方案",
            description="测试描述",
            applied_principles=[1, 15],
            resource_mapping="测试资源",
        ),
        tags=QualitativeTags(
            feasibility_score=4,
            resource_fit_score=4,
            innovation_score=4,
            uniqueness_score=3,
            risk_level="low",
            ifr_deviation_reason="",
            problem_relevance_score=relevance,
            logical_consistency_score=consistency,
        ),
        ideality_score=ideality,
        evaluation_rationale="测试评估",
    )


# --- M3 问题定型 ---

def test_formulate_tech_contradiction():
    ctx = WorkflowContext(question="test")
    ctx.root_param = "刀片磨损太快"
    ctx.key_problem = "摩擦热量过高导致接触面积问题"
    ctx.candidate_attributes = ["接触面积", "摩擦热"]
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]

    result = formulate_problem(ctx)
    assert result["problem_type"] == "tech"
    assert "磨损" in result["contradiction_desc"] or "摩擦" in result["contradiction_desc"]


def test_formulate_phys_contradiction():
    ctx = WorkflowContext(question="test")
    ctx.root_param = "接触面积既要大又要小"
    ctx.key_problem = "强度与摩擦的矛盾"
    ctx.candidate_attributes = ["接触面积"]
    ctx.sao_list = []

    result = formulate_problem(ctx)
    assert result["problem_type"] == "phys"
    assert "既要" in result["contradiction_desc"] or "大" in result["contradiction_desc"]


def test_formulate_fallback():
    ctx = WorkflowContext(question="test")
    ctx.root_param = ""
    ctx.key_problem = ""
    ctx.candidate_attributes = []
    ctx.sao_list = []

    result = formulate_problem(ctx)
    assert result["problem_type"] == "tech"
    assert result["contradiction_desc"] == "" or result["contradiction_desc"] == "未识别矛盾"


# --- M7 收敛控制 ---

def test_convergence_terminate_signals_cleared():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.7
    ctx.iteration = 1
    ctx.unresolved_signals = []
    ctx.history_log = [{"max_ideality": 0.5}]
    ctx.ranked_solutions = [_make_solution(relevance=5, consistency=5, ideality=0.7)]

    decision = check_convergence(ctx)
    assert decision.action == "TERMINATE"
    assert "信号已清空" in decision.reason


def test_convergence_continue():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.5
    ctx.iteration = 1
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.3}]
    ctx.ranked_solutions = [_make_solution(relevance=4, consistency=4, ideality=0.5)]

    decision = check_convergence(ctx)
    assert decision.action == "CONTINUE"


def test_convergence_high_ideality_terminate():
    """高理想度即使有未解决信号也提前终止（前提是相关性和一致性通过）"""
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.86
    ctx.iteration = 0
    ctx.unresolved_signals = ["方案风险过高: XX"]
    ctx.history_log = []
    ctx.ranked_solutions = [_make_solution(relevance=5, consistency=5, ideality=0.86)]

    decision = check_convergence(ctx)
    assert decision.action == "TERMINATE"
    assert "较高水平" in decision.reason


def test_convergence_clarify_low_ideality():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.1
    ctx.iteration = 1
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.05}]
    ctx.ranked_solutions = [_make_solution(relevance=4, consistency=4, ideality=0.1)]

    decision = check_convergence(ctx)
    assert decision.action == "CLARIFY"


def test_convergence_max_iterations():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.7
    ctx.iteration = 5
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.6}, {"max_ideality": 0.65}, {"max_ideality": 0.7}]
    ctx.ranked_solutions = [_make_solution(relevance=5, consistency=5, ideality=0.7)]

    decision = check_convergence(ctx)
    assert decision.action == "TERMINATE"


def test_convergence_low_relevance_continue():
    """问题相关性不足时强制 CONTINUE"""
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.8
    ctx.iteration = 0
    ctx.unresolved_signals = []
    ctx.history_log = []
    ctx.ranked_solutions = [_make_solution(relevance=2, consistency=5, ideality=0.8)]

    decision = check_convergence(ctx)
    assert decision.action == "CONTINUE"
    assert "相关性不足" in decision.reason


def test_convergence_low_consistency_continue():
    """逻辑不一致时强制 CONTINUE"""
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.8
    ctx.iteration = 0
    ctx.unresolved_signals = []
    ctx.history_log = []
    ctx.ranked_solutions = [_make_solution(relevance=5, consistency=2, ideality=0.8)]

    decision = check_convergence(ctx)
    assert decision.action == "CONTINUE"
    assert "逻辑不自洽" in decision.reason


# --- M2 门控 ---

def test_m2_gate_trigger_with_harmful_sao():
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="A", action="损坏", object="B", function_type="harmful")]
    assert should_trigger_m2(ctx) is True


def test_m2_gate_skip_all_useful():
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="A", action="切割", object="B", function_type="useful")]
    assert should_trigger_m2(ctx) is False


# --- FOS 跨界检索 ---

@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
    """初始化测试数据库（模块级）。"""
    db_path = tmp_path_factory.mktemp("data") / "test_triz.db"
    import triz.config
    import triz.database.init_db
    import triz.database.queries
    triz.config.DB_PATH = db_path
    triz.database.init_db.DB_PATH = db_path
    triz.database.queries.DB_PATH = db_path
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)


def test_search_local_cases(monkeypatch):
    from triz.context import SearchResult

    def mock_search_serpapi(query, num=5):
        return [
            SearchResult(title="Test Patent", snippet="test snippet", source="Google Patents", query=query),
        ]

    monkeypatch.setattr("triz.tools.fos_search._search_serpapi", mock_search_serpapi)
    monkeypatch.setattr("triz.tools.fos_search._get_cache", lambda q: None)
    monkeypatch.setattr("triz.tools.fos_search._set_cache", lambda q, r: None)

    ctx = WorkflowContext(question="如何提高手术刀片耐用性")
    ctx.principles = [15, 28]
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]

    cases = search_cases(ctx)
    assert len(cases) > 0
    assert all(hasattr(c, "principle_id") for c in cases)


def test_search_returns_empty_when_no_match():
    """无匹配且SerpApi不可用时返回空。"""
    ctx = WorkflowContext(question="test")
    ctx.principles = [999]
    ctx.sao_list = []

    cases = search_cases(ctx)
    # SerpApi 未配置时返回空
    assert cases == []
