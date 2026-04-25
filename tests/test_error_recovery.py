"""错误恢复路径测试：验证系统在各环节出错时的降级行为。"""
import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from triz.context import WorkflowContext, ConvergenceDecision, SAO
from triz.orchestrator import Orchestrator
from triz.tools.registry import ToolRegistry
from triz.tools.query_matrix import query_matrix
from triz.database.init_db import init_database
from triz.tools import input_classifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
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


def _make_mock_response(content: str = None, tool_calls: list = None):
    mock_message = Mock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls or []
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_mock_tool_call(id: str, name: str, arguments: dict):
    mock_func = Mock()
    mock_func.name = name
    mock_func.arguments = json.dumps(arguments)
    mock_tc = Mock()
    mock_tc.id = id
    mock_tc.type = "function"
    mock_tc.function = mock_func
    return mock_tc


# ---------------------------------------------------------------------------
# 1. API 超时 / 异常
# ---------------------------------------------------------------------------

def test_orchestrator_catches_api_timeout():
    """Skill 执行抛出 TimeoutError 时，Orchestrator 应捕获并继续，不崩溃。"""
    orch = Orchestrator(callback=None)
    errors = []
    orch.callback = lambda et, ed: errors.append(ed) if et == "step_error" else None

    with patch.object(orch, '_run_skill', side_effect=TimeoutError("API timeout")):
        ctx = WorkflowContext(question="test")
        ctx.sao_list = [SAO(subject="A", action="B", object="C", function_type="useful")]
        result = orch._execute_node("矛盾求解", 2, 5, ctx, [("m4_solver", "Skill")])

    assert len(errors) == 1
    assert "API timeout" in errors[0]["error"]
    assert result is not None  # 没有崩溃


def test_orchestrator_catches_generic_exception():
    """任意异常都应被捕获并通知 callback。"""
    orch = Orchestrator(callback=None)
    errors = []
    orch.callback = lambda et, ed: errors.append(ed) if et == "step_error" else None

    with patch.object(orch, '_run_skill', side_effect=RuntimeError("Boom")):
        ctx = WorkflowContext(question="test")
        ctx.sao_list = [SAO(subject="A", action="B", object="C", function_type="useful")]
        result = orch._execute_node("矛盾求解", 2, 5, ctx, [("m4_solver", "Skill")])

    assert len(errors) == 1
    assert "Boom" in errors[0]["error"]



# ---------------------------------------------------------------------------
# 3. Orchestrator 硬终止路径
# ---------------------------------------------------------------------------

def test_orchestrator_clarify_when_empty_sao():
    """M1 返回空结果 → ctx.sao_list 为空 → 触发 clarify。"""
    orch = Orchestrator()
    with patch.object(input_classifier, 'classify_input', return_value={"category": "engineering", "proceed": True, "response": None}):
        with patch.object(orch, '_run_skill', return_value={}):
            result = orch.run_workflow("test question")
    assert "需要补充信息" in result


def test_orchestrator_fallback_when_empty_principles():
    """M4 返回空 principles → 触发 fallback。"""
    orch = Orchestrator()

    def mock_run(step_name, ctx):
        if step_name == "m1_modeling":
            return {
                "sao_list": [
                    {"subject": "A", "action": "B", "object": "C", "function_type": "useful"},
                    {"subject": "D", "action": "E", "object": "F", "function_type": "harmful"},
                ],
                "resources": {},
                "ifr": "test"
            }
        elif step_name == "m2_causal":
            return {
                "root_param": "磨损",
                "causal_chain": ["a", "b"],
                "candidate_attributes": ["x"]
            }
        elif step_name == "m4_solver":
            return {"principles": []}  # 空 principles
        return {}

    with patch.object(input_classifier, 'classify_input', return_value={"category": "engineering", "proceed": True, "response": None}):
        with patch.object(orch, '_run_skill', side_effect=mock_run):
            result = orch.run_workflow("test")
    assert "流程中断" in result
    assert "无法从矛盾定义中匹配到发明原理" in result


def test_orchestrator_fallback_when_empty_drafts():
    """M5 返回空 solution_drafts → 触发 fallback。"""
    orch = Orchestrator()

    def mock_run(step_name, ctx):
        if step_name == "m1_modeling":
            return {
                "sao_list": [
                    {"subject": "A", "action": "B", "object": "C", "function_type": "harmful"}
                ],
                "resources": {},
                "ifr": "test"
            }
        elif step_name == "m2_causal":
            return {
                "root_param": "磨损",
                "causal_chain": ["a"],
                "candidate_attributes": []  # 空属性，使 M4 fallback 也失败
            }
        elif step_name == "m4_solver":
            return {"principles": []}
        elif step_name == "m5_generation":
            return {"solution_drafts": []}  # 空 drafts
        return {}

    with patch.object(input_classifier, 'classify_input', return_value={"category": "engineering", "proceed": True, "response": None}):
        with patch.object(orch, '_run_skill', side_effect=mock_run):
            result = orch.run_workflow("test")
    assert "流程中断" in result


# ---------------------------------------------------------------------------
# 4. 数据库 - fallback
# ---------------------------------------------------------------------------

def test_query_matrix_returns_fallback_for_invalid_params():
    """传入不存在的参数 ID 时，应返回 fallback principles 而非空列表。"""
    principles = query_matrix(999, 998)
    assert len(principles) > 0  # fallback principles


# ---------------------------------------------------------------------------
# 5. 多轮迭代 CONTINUE 状态重置
# ---------------------------------------------------------------------------

def test_orchestrator_continue_resets_iteration_state():
    """M7 返回 CONTINUE 时，应正确重置状态并递增 iteration。"""
    orch = Orchestrator()

    call_log = []

    def mock_run(step_name, ctx):
        call_log.append(step_name)
        if step_name == "m1_modeling":
            return {
                "sao_list": [{"subject": "A", "action": "B", "object": "C", "function_type": "harmful"}],
                "resources": {},
                "ifr": "test"
            }
        elif step_name == "m2_causal":
            return {"root_param": "x", "causal_chain": ["a"], "candidate_attributes": ["y"]}
        elif step_name == "m4_solver":
            return {"principles": [1], "improve_param_id": 1, "worsen_param_id": 2}
        elif step_name == "m5_generation":
            return {
                "solution_drafts": [{
                    "title": "方案1",
                    "description": "测试方案描述",
                    "applied_principles": [1],
                    "resource_mapping": "测试资源"
                }]
            }
        elif step_name == "m6_evaluation":
            return {
                "ranked_solutions": [{
                    "draft": {
                        "title": "方案1",
                        "description": "测试方案描述",
                        "applied_principles": [1],
                        "resource_mapping": "测试资源"
                    },
                    "tags": {
                        "feasibility_score": 4,
                        "resource_fit_score": 4,
                        "innovation_score": 4,
                        "uniqueness_score": 3,
                        "risk_level": "low",
                        "ifr_deviation_reason": "",
                        "problem_relevance_score": 4,
                        "logical_consistency_score": 4,
                    },
                    "ideality_score": 0.6,
                    "evaluation_rationale": "测试"
                }],
                "max_ideality": 0.6,
                "unresolved_signals": ["风险过高"]
            }
        return {}

    def mock_solve(ctx=None, **kwargs):
        return {"principles": [1], "improve_param_id": 1, "worsen_param_id": 2}

    with patch.object(input_classifier, 'classify_input', return_value={"category": "engineering", "proceed": True, "response": None}):
        with patch.object(orch, '_run_skill', side_effect=mock_run):
            with patch('triz.tools.solve_contradiction.solve_contradiction', side_effect=mock_solve):
                with patch('triz.tools.m7_convergence.check_convergence') as mock_m7:
                    # 第一次 CONTINUE，第二次 TERMINATE
                    mock_m7.side_effect = [
                        ConvergenceDecision(action="CONTINUE", reason="需改进", feedback="试其他原理"),
                        ConvergenceDecision(action="TERMINATE", reason="完成", feedback=""),
                    ]
                    result = orch.run_workflow("test")

    # 验证最终报告生成（render_final_report 输出包含 "TRIZ 解决方案报告"）
    assert "TRIZ 解决方案报告" in result
    # M5/M6 应该被调用两次（两次迭代）
    assert call_log.count("m5_generation") == 2
    assert call_log.count("m6_evaluation") == 2


# ---------------------------------------------------------------------------
# 8. 输入分类器
# ---------------------------------------------------------------------------

def test_input_classifier_greeting():
    """打招呼应被识别并拒绝。"""
    result = input_classifier.classify_input("你好")
    assert result["category"] == "greeting"
    assert result["proceed"] is False
    assert "TRIZ" in result["response"]


def test_input_classifier_invalid():
    """无效输入应被识别并拒绝。"""
    result = input_classifier.classify_input("123456")
    assert result["category"] == "invalid"
    assert result["proceed"] is False


def test_input_classifier_non_engineering_keyword():
    """包含非工程关键词的问题应被拒绝。"""
    result = input_classifier.classify_input("今天天气怎么样")
    assert result["category"] == "non_engineering"
    assert result["proceed"] is False


def test_input_classifier_engineering_keyword():
    """包含工程关键词的问题应快速通过。"""
    result = input_classifier.classify_input("汽车发动机噪音大")
    assert result["category"] == "engineering"
    assert result["proceed"] is True


def test_input_classifier_unclear_passes():
    """无法判断的输入应放过（宁可放过不要错杀）。"""
    result = input_classifier.classify_input("asdfghjkl")
    assert result["proceed"] is True


def test_input_classifier_greeting_with_llm(monkeypatch):
    """LLM 返回 non_engineering+high confidence 时拒绝。"""
    monkeypatch.setattr(
        input_classifier, '_llm_classify',
        lambda text: {"category": "non_engineering", "confidence": "high"}
    )
    result = input_classifier.classify_input("anything")
    assert result["category"] == "non_engineering"
    assert result["proceed"] is False


def test_input_classifier_llm_unclear_passes(monkeypatch):
    """LLM 返回 unclear 时应放过。"""
    monkeypatch.setattr(
        input_classifier, '_llm_classify',
        lambda text: {"category": "unclear", "confidence": "medium"}
    )
    result = input_classifier.classify_input("anything")
    assert result["proceed"] is True
