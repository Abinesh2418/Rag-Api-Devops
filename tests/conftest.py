"""Pytest fixtures for RAG API unit tests."""

import os
from unittest.mock import MagicMock

import pytest

# Enable mock LLM before app imports so ollama is not required
os.environ["USE_MOCK_LLM"] = "1"

import app as app_module  # noqa: E402


@pytest.fixture
def mock_collection():
    """Mock ChromaDB collection that returns fixed context."""
    mock = MagicMock()
    mock.query.return_value = {
        "documents": [["Kubernetes is a container orchestration platform."]],
        "metadatas": [[]],
        "ids": [["doc1"]],
    }
    return mock


@pytest.fixture
def client(mock_collection):
    """FastAPI test client with mocked ChromaDB collection."""
    app_module.collection = mock_collection
    from fastapi.testclient import TestClient

    return TestClient(app_module.app)
