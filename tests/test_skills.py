import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext, SAO, Case, SolutionDraft


# --- M1 功能建模 ---

def test_model_function_with_mock():
    from triz.skills.m1_modeling import model_function
    ctx = WorkflowContext(question="如何提高手术刀片耐用性")
    mock_response = '''{
        "sao_list": [
            {"subject": "刀片", "action": "切割", "object": "组织", "function_type": "useful"},
            {"subject": "摩擦", "action": "磨损", "object": "刀片", "function_type": "harmful"}
        ],
        "resources": {"物质": ["刀片", "组织"], "场": ["热场"]},
        "ifr": "刀片在无限切割时保持零磨损"
    }'''

    with patch('triz.skills.m1_modeling.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = model_function(ctx)
        assert len(result["sao_list"]) == 2
        assert result["sao_list"][0].subject == "刀片"
        assert result["ifr"] == "刀片在无限切割时保持零磨损"


# --- M2 根因分析 ---

def test_analyze_cause_with_mock():
    from triz.skills.m2_causal import analyze_cause
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]
    ctx.resources = {"物质": ["刀片"]}

    mock_response = '''{
        "root_param": "接触面积导致摩擦热积累",
        "key_problem": "接触面积过大导致磨损",
        "candidate_attributes": ["接触面积", "摩擦热", "切割强度"],
        "causal_chain": ["刀片磨损", "摩擦热量过高", "接触面积大"]
    }'''

    with patch('triz.skills.m2_causal.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = analyze_cause(ctx)
        assert result["root_param"] == "接触面积导致摩擦热积累"
        assert "接触面积" in result["candidate_attributes"]
        assert len(result["causal_chain"]) == 3


# --- M5 方案生成 ---

def test_generate_solutions_with_mock():
    from triz.skills.m5_generation import generate_solutions
    ctx = WorkflowContext(question="test")
    ctx.principles = [15, 28]
    ctx.cases = [Case(principle_id=15, source="本地", title="F1悬挂", description="动态调节", function="支撑")]
    ctx.contradiction_desc = "改善速度恶化形状"
    ctx.resources = {"物质": ["刀片"], "场": ["热场"]}
    ctx.ifr = "刀片零磨损"
    ctx.feedback = ""

    mock_response = '''[
        {"title": "动态压力调节", "description": "参考F1悬挂设计...", "applied_principles": [15], "resource_mapping": "利用热场"}
    ]'''

    with patch('triz.skills.m5_generation.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = generate_solutions(ctx)
        assert len(result["solution_drafts"]) == 1
        assert result["solution_drafts"][0].title == "动态压力调节"


# --- M6 方案评估 ---

def test_evaluate_solutions_with_mock():
    from triz.skills.m6_evaluation import evaluate_solutions
    ctx = WorkflowContext(question="test")
    ctx.solution_drafts = [
        SolutionDraft(title="方案1", description="动态调节...", applied_principles=[15], resource_mapping="热场")
    ]
    ctx.contradiction_desc = "改善速度恶化形状"
    ctx.resources = {"场": ["热场"]}
    ctx.ifr = "零磨损"

    mock_response = '''[
        {
            "draft": {"title": "方案1", "description": "动态调节...", "applied_principles": [15], "resource_mapping": "热场"},
            "tags": {"feasibility_score": 4, "resource_fit_score": 5, "innovation_score": 4, "uniqueness_score": 3, "risk_level": "low", "ifr_deviation_reason": ""},
            "ideality_score": 0.78,
            "evaluation_rationale": "利用现有热场资源，可行性高"
        }
    ]'''

    with patch('triz.skills.m6_evaluation.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = evaluate_solutions(ctx)
        assert len(result["ranked_solutions"]) == 1
        assert result["ranked_solutions"][0].ideality_score == 0.78
        assert result["max_ideality"] == 0.78
