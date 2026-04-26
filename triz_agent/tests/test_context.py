import pytest
from triz_agent.context import (
    SAO,
    WorkflowContext,
    ConvergenceDecision,
    Solution,
    QualitativeTags,
    SolutionDraft,
)


def test_sao_creation():
    sao = SAO(subject="刀片", action="切割", object="纸张", function_type="useful")
    assert sao.subject == "刀片"
    assert sao.function_type == "useful"


def test_workflow_context_defaults():
    ctx = WorkflowContext(question="如何提高电池续航")
    assert ctx.question == "如何提高电池续航"
    assert ctx.sao_list == []
    assert ctx.iteration == 0
    assert ctx.contradiction_desc == ""


def test_convergence_decision():
    decision = ConvergenceDecision(action="TERMINATE", reason="信号已清空")
    assert decision.action == "TERMINATE"


def test_solution_model():
    draft = SolutionDraft(
        title="测试", description="描述", applied_principles=[1], resource_mapping="无"
    )
    tags = QualitativeTags(
        feasibility_score=4,
        resource_fit_score=5,
        innovation_score=3,
        uniqueness_score=3,
        risk_level="low",
        ifr_deviation_reason="",
    )
    sol = Solution(
        draft=draft, tags=tags, ideality_score=0.8, evaluation_rationale="测试"
    )
    assert sol.ideality_score == 0.8
    assert sol.tags.risk_level == "low"
