import pytest
from triz.utils.api_client import OpenAIClient
from unittest.mock import MagicMock, patch


def test_openai_client_initialization():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    assert client.model == "gpt-4o-mini"


def test_openai_client_chat_mock():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    with patch.object(client.client.chat.completions, 'create') as mock_create:
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"test": true}'))]
        )
        result = client.chat("Hello")
        assert result == '{"test": true}'
        mock_create.assert_called_once()
