"""Pytest fixtures for RAG API unit tests."""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
os.environ.setdefault("AZURE_OPENAI_MODEL", "gpt-4o")

import backend.app as app_module  # noqa: E402


@pytest.fixture
def client():
    """FastAPI test client with mocked Azure OpenAI client."""
    mock_response = MagicMock()
    mock_response.choices[
        0
    ].message.content = "Kubernetes is a container orchestration platform."

    with patch.object(
        app_module.azure_client.chat.completions, "create", return_value=mock_response
    ):
        from fastapi.testclient import TestClient

        yield TestClient(app_module.app)
