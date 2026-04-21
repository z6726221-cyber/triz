import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext, ConvergenceDecision, SAO
from triz.orchestrator import Orchestrator


def test_orchestrator_init():
    orch = Orchestrator()
    assert orch is not None


def test_orchestrator_run_workflow_mock():
    """测试编排器能完整跑通 workflow（全部 mock）。"""
    orch = Orchestrator()

    with patch('triz.orchestrator.model_function') as m1, \
         patch('triz.orchestrator.should_trigger_m2', return_value=True), \
         patch('triz.orchestrator.analyze_cause') as m2, \
         patch('triz.orchestrator.formulate_problem') as m3, \
         patch('triz.orchestrator.solve_contradiction') as m4, \
         patch('triz.orchestrator.search_cases') as fos, \
         patch('triz.orchestrator.generate_solutions') as m5, \
         patch('triz.orchestrator.evaluate_solutions') as m6, \
         patch('triz.orchestrator.check_convergence') as m7:

        m1.return_value = {"sao_list": [SAO(subject="刀片", action="切割", object="组织", function_type="useful")], "resources": {}, "ifr": ""}
        m2.return_value = {"root_param": "根因", "key_problem": "问题", "candidate_attributes": [], "causal_chain": []}
        m3.return_value = {"problem_type": "tech", "contradiction_desc": "改善A恶化B", "evidence": []}
        m4.return_value = {"principles": [15], "sep_type": None, "match_conf": 0.8, "improve_param_id": 1, "worsen_param_id": 2, "need_state": None, "need_not_state": None}
        fos.return_value = []
        m5.return_value = {"solution_drafts": [MagicMock()]}
        m6.return_value = {"ranked_solutions": [MagicMock(ideality_score=0.8)], "max_ideality": 0.8, "unresolved_signals": []}
        m7.return_value = ConvergenceDecision(action="TERMINATE", reason="信号已清空")

        result = orch.run_workflow("如何提高续航")
        assert "解决方案报告" in result or "报告" in result
