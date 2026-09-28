from fastapi.testclient import TestClient

from gateway.app import main


async def fake_invoke_runtime(request):
    return {
        "output": f"Mock response to: {request.input}",
        "model": "mock-llm",
        "usage": {"input_tokens": 1, "output_tokens": 4},
    }


def test_invoke(monkeypatch):
    monkeypatch.setattr(main, "invoke_runtime", fake_invoke_runtime)
    client = TestClient(main.app)

    response = client.post(
        "/v1/agents/basic-agent/invoke",
        json={"input": "hello"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent_id"] == "basic-agent"
    assert body["status"] == "completed"
    assert body["output"] == "Mock response to: hello"
    assert body["execution_id"]
    assert body["trace_id"]

