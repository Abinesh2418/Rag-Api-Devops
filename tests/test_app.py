"""Unit tests for the RAG API."""

from fastapi.testclient import TestClient

# Import after conftest has set USE_MOCK_LLM
import app as app_module  # noqa: E402


def test_query_returns_200_and_answer(client: TestClient):
    """POST /query returns 200 and answer contains retrieved context."""
    response = client.post("http://testserver/query?q=What is Kubernetes?")
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "container" in data["answer"].lower()


def test_query_with_empty_documents_returns_empty_context():
    """When collection returns no documents, answer is empty string."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.query.return_value = {"documents": [], "metadatas": [], "ids": []}
    app_module.collection = mock

    with TestClient(app_module.app) as c:
        response = c.post("http://testserver/query?q=anything")
    assert response.status_code == 200
    assert response.json()["answer"] == ""
