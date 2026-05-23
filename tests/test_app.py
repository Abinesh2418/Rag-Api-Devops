"""Unit tests for the RAG API."""

from fastapi.testclient import TestClient

import backend.app as app_module  # noqa: E402


def test_query_returns_200_and_answer(client: TestClient):
    """POST /query returns 200 and answer contains retrieved context."""
    response = client.post("http://testserver/query?q=What is Kubernetes?")
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "container" in data["answer"].lower()


def test_query_returns_error_on_api_failure():
    """When Azure OpenAI raises an exception, /query returns an error message."""
    from unittest.mock import patch

    with patch.object(
        app_module.azure_client.chat.completions,
        "create",
        side_effect=Exception("API error"),
    ):
        with TestClient(app_module.app) as c:
            response = c.post("http://testserver/query?q=anything")
    assert response.status_code == 200
    assert "Error" in response.json()["answer"]
