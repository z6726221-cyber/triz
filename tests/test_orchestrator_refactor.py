import pytest
from triz.orchestrator import Orchestrator, _register_m4_tools
from triz.core.tool_registry import ToolRegistry


def test_register_m4_tools():
    """验证 M4 tools 注册正确"""
    registry = _register_m4_tools()
    tools = registry.list_tools()
    assert "map_to_parameters" in tools
    assert "query_matrix" in tools
    assert "query_separation" in tools
    assert "search_patents" in tools
    assert len(tools) == 4


def test_orchestrator_initialization():
    """Orchestrator 能正确初始化"""
    orch = Orchestrator()
    assert orch.tool_registry is not None
    assert isinstance(orch.tool_registry, ToolRegistry)
