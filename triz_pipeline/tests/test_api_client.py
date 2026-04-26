import pytest
from triz_pipeline.utils.api_client import OpenAIClient
from unittest.mock import MagicMock, patch, Mock


def test_openai_client_initialization():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    assert client.model == "gpt-4o-mini"


def test_openai_client_chat_mock():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    with patch.object(client.client.chat.completions, "create") as mock_create:
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"test": true}'))]
        )
        result = client.chat("Hello")
        assert result == '{"test": true}'
        mock_create.assert_called_once()


def test_chat_with_tools_returns_response():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    mock_choice = Mock()
    mock_choice.message.content = "Test response"
    mock_choice.message.tool_calls = None
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    client.client.chat.completions.create = Mock(return_value=mock_response)

    messages = [{"role": "user", "content": "test"}]
    tools = [{"type": "function", "function": {"name": "test_tool"}}]

    result = client.chat_with_tools(messages=messages, tools=tools)

    assert result == mock_response
    client.client.chat.completions.create.assert_called_once()
    call_kwargs = client.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"] == messages
    assert call_kwargs["tools"] == tools
    assert call_kwargs["tool_choice"] == "auto"
