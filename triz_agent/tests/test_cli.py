import pytest
from unittest.mock import patch, MagicMock
from triz_agent.cli import main


def test_cli_single_mode():
    with (
        patch("sys.argv", ["triz", "-q", "如何提高续航"]),
        patch("triz_agent.cli.TrizAgent") as MockAgent,
        patch("triz_agent.cli.init_database"),
        patch("sys.stdin.isatty", return_value=True),
    ):
        mock_agent = MockAgent.return_value
        mock_agent.run.return_value = "# 报告"
        main()
        mock_agent.run.assert_called_once_with("如何提高续航")


def test_cli_default_interactive():
    """默认无参数时进入交互模式"""
    with (
        patch("sys.argv", ["triz"]),
        patch("triz_agent.cli.TRIZAgentConsole") as MockConsole,
        patch("sys.stdin.isatty", return_value=False),
    ):
        mock_console = MockConsole.return_value
        main()
        mock_console.run.assert_called_once()
