import json
from unittest.mock import Mock
import pytest
from triz.context import WorkflowContext
from triz.core.skill_runner import SkillRunner
from triz.core.tool_registry import ToolRegistry


def _make_mock_response(content: str = None, tool_calls: list = None):
    mock_message = Mock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls
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


def test_skill_runner_parses_json_output(tmp_path, monkeypatch):
    registry = ToolRegistry()
    runner = SkillRunner(registry)

    mock_client = Mock()
    mock_response = _make_mock_response(content='{"sao_list": [], "ifr": "test"}')
    mock_client.chat_with_tools = Mock(return_value=mock_response)
    runner.client = mock_client

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "m1_modeling.md"
    skill_file.write_text("# M1\n输出JSON。", encoding="utf-8")

    monkeypatch.setattr(
        runner, "_get_skill_path",
        lambda name: tmp_path / "skills" / f"{name}.md"
    )

    ctx = WorkflowContext(question="test")
    result = runner.run("m1_modeling", ctx)

    assert result["ifr"] == "test"


def test_skill_runner_executes_tool_call(tmp_path, monkeypatch):
    registry = ToolRegistry()

    def mock_tool(x: int) -> int:
        return x * 2

    registry.register(
        name="mock_tool",
        func=mock_tool,
        schema={
            "name": "mock_tool",
            "description": "Mock tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
        }
    )

    runner = SkillRunner(registry)

    tc = _make_mock_tool_call("call_1", "mock_tool", {"x": 5})
    response1 = _make_mock_response(tool_calls=[tc])
    response2 = _make_mock_response(content='{"result": 10}')

    mock_client = Mock()
    mock_client.chat_with_tools = Mock(side_effect=[response1, response2])
    runner.client = mock_client

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "m1_modeling.md"
    skill_file.write_text("# M1", encoding="utf-8")

    monkeypatch.setattr(
        runner, "_get_skill_path",
        lambda name: tmp_path / "skills" / f"{name}.md"
    )

    ctx = WorkflowContext(question="test")
    result = runner.run("m1_modeling", ctx)

    assert result["result"] == 10
    assert mock_client.chat_with_tools.call_count == 2


def test_skill_runner_exceeds_max_rounds(tmp_path, monkeypatch):
    registry = ToolRegistry()

    def loop_tool():
        return {}

    registry.register(
        name="loop_tool",
        func=loop_tool,
        schema={
            "name": "loop_tool",
            "description": "Loops forever",
            "parameters": {"type": "object", "properties": {}},
        }
    )

    runner = SkillRunner(registry)

    tc = _make_mock_tool_call("call_1", "loop_tool", {})
    response = _make_mock_response(tool_calls=[tc])

    mock_client = Mock()
    mock_client.chat_with_tools = Mock(return_value=response)
    runner.client = mock_client

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "m1_modeling.md"
    skill_file.write_text("# M1", encoding="utf-8")

    monkeypatch.setattr(
        runner, "_get_skill_path",
        lambda name: tmp_path / "skills" / f"{name}.md"
    )

    ctx = WorkflowContext(question="test")
    with pytest.raises(RuntimeError, match="超过最大轮数"):
        runner.run("m1_modeling", ctx)
