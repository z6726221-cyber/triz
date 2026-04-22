import pytest
from unittest.mock import patch, MagicMock
from triz.cli import main


def test_cli_single_mode():
    with patch('sys.argv', ['triz', '如何提高续航']), \
         patch('triz.cli.Orchestrator') as MockOrch, \
         patch('triz.cli.init_database'), \
         patch('sys.stdin.isatty', return_value=True):
        mock_orch = MockOrch.return_value
        mock_orch.run_workflow.return_value = "# 报告"
        main()
        mock_orch.run_workflow.assert_called_once_with("如何提高续航")
