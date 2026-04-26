"""CLI 渲染测试：验证 TRIZConsole 事件处理和命令行为。"""
import pytest
from unittest.mock import patch, MagicMock
from rich.console import Console

from triz_pipeline.cli import TRIZConsole
from triz_pipeline.context import WorkflowContext, SAO, Solution, SolutionDraft, QualitativeTags


@pytest.fixture
def console():
    c = TRIZConsole()
    c.console = Console(record=True, width=120)
    return c


def _make_ctx(**kwargs):
    """创建带有所需字段的 WorkflowContext。"""
    ctx = WorkflowContext(question="测试问题")
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    return ctx


# ---------------------------------------------------------------------------
# 事件渲染
# ---------------------------------------------------------------------------

def test_event_node_start(console):
    """node_start 事件应渲染节点 Panel。"""
    console._on_event("node_start", {"node_name": "问题建模", "current": 1, "total": 5})
    output = console.console.export_text()
    assert "问题建模" in output
    assert "1/5" in output


def test_event_step_start_and_complete(console):
    """step_start 和 step_complete 应正确更新步骤状态。"""
    console._on_event("node_start", {"node_name": "矛盾求解", "current": 2, "total": 5})
    console._on_event("step_start", {"step_name": "m4_solver", "step_type": "Skill"})
    console._on_event("step_complete", {"step_name": "m4_solver", "step_type": "Skill", "result": {"principles": [1]}})
    output = console.console.export_text()
    assert "m4_solver" in output


def test_event_step_error(console):
    """step_error 事件应显示错误信息且不破坏布局。"""
    console._on_event("node_start", {"node_name": "矛盾求解", "current": 2, "total": 5})
    console._on_event("step_start", {"step_name": "m4_solver", "step_type": "Skill"})
    console._on_event("step_error", {"step_name": "m4_solver", "step_type": "Skill", "error": "API timeout"})
    output = console.console.export_text()
    assert "API timeout" in output


def test_event_m2_gate_skip(console):
    """M2 gate skip 应正确标记步骤为跳过，不崩溃。"""
    console._on_event("node_start", {"node_name": "问题建模", "current": 1, "total": 5})
    console._on_event("step_start", {"step_name": "m2_causal", "step_type": "Gate"})
    console._on_event("step_complete", {
        "step_name": "m2_causal", "step_type": "Gate",
        "result": {"skipped": True, "reason": "无负面功能"}
    })
    # 验证内部状态正确
    assert len(console._nodes) == 1
    steps = console._nodes[0]["steps"]
    assert len(steps) == 1
    assert steps[0].get("skipped") is True


def test_event_node_complete_with_summary(console):
    """node_complete 带 ctx 时应渲染节点摘要。"""
    console._on_event("node_start", {"node_name": "问题建模", "current": 1, "total": 5})
    ctx = _make_ctx(
        sao_list=[SAO(subject="刀片", action="切割", object="组织", function_type="useful")],
        ifr="自动保持锋利",
        root_param="摩擦热",
        contradiction_desc="既要快又要慢"
    )
    console._on_event("node_complete", {"node_name": "问题建模", "ctx": ctx, "outputs": []})
    output = console.console.export_text()
    assert "刀片" in output
    assert "摩擦热" in output


def test_event_decision_terminate(console):
    """TERMINATE 决策应渲染为绿色成功样式。"""
    console._on_event("decision", {"action": "TERMINATE", "reason": "信号已清空", "feedback": ""})
    output = console.console.export_text()
    assert "TERMINATE" in output
    assert "信号已清空" in output


def test_event_decision_continue(console):
    """CONTINUE 决策应渲染为黄色循环样式。"""
    console._on_event("decision", {"action": "CONTINUE", "reason": "需改进", "feedback": "试其他原理"})
    output = console.console.export_text()
    assert "CONTINUE" in output


def test_event_decision_clarify(console):
    """CLARIFY 决策应渲染为红色问号样式。"""
    console._on_event("decision", {"action": "CLARIFY", "reason": "信息不足", "feedback": ""})
    output = console.console.export_text()
    assert "CLARIFY" in output


def test_event_report_renders_markdown(console):
    """report 事件应渲染 Markdown 最终报告。"""
    report = "# TRIZ 解决方案报告\n\n## 问题\n测试\n\n## 核心矛盾\n矛盾描述"
    console._on_event("report", {"content": report})
    output = console.console.export_text()
    assert "TRIZ 解决方案报告" in output
    assert "矛盾描述" in output


# ---------------------------------------------------------------------------
# 命令处理
# ---------------------------------------------------------------------------

def test_cmd_save_report(tmp_path):
    """/save 命令应将报告写入文件。"""
    console = TRIZConsole()
    console.last_report = "# Test Report\n\nContent"
    with patch.object(console.console, 'print'):
        console._save_report(str(tmp_path / "test_report"))
    saved = tmp_path / "test_report.md"
    assert saved.exists()
    assert "# Test Report" in saved.read_text(encoding="utf-8")


def test_cmd_save_no_report(console):
    """无报告时 /save 应提示错误。"""
    console.last_report = ""
    console.console = Console(record=True)
    console._save_report("")
    output = console.console.export_text()
    assert "暂无报告" in output


def test_cmd_show_existing_node(console):
    """/show 对已存在的节点应渲染详情。"""
    console.console = Console(record=True)
    ctx = _make_ctx(sao_list=[SAO(subject="A", action="B", object="C", function_type="useful")])
    console._nodes = [{
        "node_name": "问题建模",
        "current": 1, "total": 5, "status": "done",
        "steps": [], "ctx": ctx,
    }]
    console._show_node("问题建模")
    output = console.console.export_text()
    assert "A" in output  # SAO 摘要中应包含 subject


def test_cmd_show_nonexistent_node(console):
    """/show 对不存在的节点应提示错误。"""
    console.console = Console(record=True)
    console._show_node("不存在的节点")
    output = console.console.export_text()
    assert "未找到节点" in output


def test_cmd_history_empty(console):
    """无节点时 /history 应提示。"""
    console.console = Console(record=True)
    console._show_history()
    output = console.console.export_text()
    assert "无节点记录" in output


def test_cmd_history_with_nodes(console):
    """/history 应渲染所有节点（紧凑模式）。"""
    console.console = Console(record=True)
    console._nodes = [
        {"node_name": "问题建模", "current": 1, "total": 5, "status": "done", "steps": []},
        {"node_name": "矛盾求解", "current": 2, "total": 5, "status": "done", "steps": []},
    ]
    console._show_history()
    output = console.console.export_text()
    assert "问题建模" in output
    assert "矛盾求解" in output


def test_cmd_new_resets_state(console):
    """/new 应重置 orchestrator 和会话历史。"""
    console.orch = MagicMock()
    console.session_history = [{"question": "old"}]
    console.console = Console(record=True)
    console._handle_command("/new")
    assert console.orch is None
    assert console.session_history == []


def test_cmd_unknown(console):
    """未知命令应提示错误。"""
    console.console = Console(record=True)
    console._handle_command("/unknown_cmd")
    output = console.console.export_text()
    assert "未知命令" in output


def test_cmd_exit_returns_true(console):
    """/exit 应返回 True。"""
    result = console._handle_command("/exit")
    assert result is True


# ---------------------------------------------------------------------------
# 长文本 / 边界
# ---------------------------------------------------------------------------

def test_long_text_report(console):
    """超长报告不应导致渲染溢出或异常。"""
    long_desc = "这是一个非常长的描述。" * 200
    report = f"# 报告\n\n{long_desc}\n\n## 结论\n完成。"
    console._on_event("report", {"content": report})
    output = console.console.export_text()
    assert "报告" in output
    assert "完成" in output


def test_empty_step_result(console):
    """步骤 result 为空 dict 时不应崩溃。"""
    console._on_event("node_start", {"node_name": "矛盾求解", "current": 2, "total": 5})
    console._on_event("step_start", {"step_name": "m4_solver", "step_type": "Skill"})
    console._on_event("step_complete", {"step_name": "m4_solver", "step_type": "Skill", "result": {}})
    # 验证内部状态正确（不崩溃即为通过）
    assert len(console._nodes) == 1
    steps = console._nodes[0]["steps"]
    assert len(steps) == 1
    assert steps[0]["status"] == "done"
