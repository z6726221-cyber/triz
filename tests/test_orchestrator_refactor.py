import pytest
from triz.orchestrator import Orchestrator
from triz.tools.registry import ToolRegistry, register_default_tools


def test_register_tools():
    """验证 Tools 注册正确"""
    registry = register_default_tools()
    tools = registry.list_tools()
    assert "solve_contradiction" in tools
    assert "search_patents" in tools
    assert "map_to_parameters" in tools
    assert "query_matrix" in tools
    assert "query_separation" in tools
    assert len(tools) == 5


def test_orchestrator_initialization():
    """Orchestrator 能正确初始化"""
    orch = Orchestrator()
    assert orch.tool_registry is not None
    assert isinstance(orch.tool_registry, ToolRegistry)
