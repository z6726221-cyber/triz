import pytest
from unittest.mock import patch, MagicMock
from triz.cli import main


def test_cli_single_mode():
    with patch('sys.argv', ['triz', '-q', '如何提高续航']), \
         patch('triz.cli.Orchestrator') as MockOrch, \
         patch('triz.cli.init_database'), \
         patch('sys.stdin.isatty', return_value=True):
        mock_orch = MockOrch.return_value
        mock_orch.run_workflow.return_value = "# 报告"
        main()
        mock_orch.run_workflow.assert_called_once_with("如何提高续航")


def test_cli_default_interactive():
    """默认无参数时进入交互模式"""
    with patch('sys.argv', ['triz']), \
         patch('triz.cli.TRIZConsole') as MockConsole, \
         patch('sys.stdin.isatty', return_value=False):
        mock_console = MockConsole.return_value
        main()
        mock_console.run.assert_called_once()
