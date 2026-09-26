import pytest

from services import jev_service


def test_guard_tool_call_requires_api_key(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)

    with pytest.raises(jev_service.JevError, match="JEV_API_KEY is not configured"):
        jev_service.guard_tool_call(
            tool="test_tool",
            action="test action",
        )


def test_guard_tool_call_success(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "code": 0,
                "message": "ok",
                "data": {
                    "decision": "allow",
                    "confidence": 0.91,
                    "probabilities": {
                        "allow": 0.91,
                        "confirm": 0.04,
                        "review": 0.03,
                        "deny": 0.02,
                    },
                    "guidance": "Proceed.",
                    "guidance_source": "jev_preset",
                    "answers": {},
                },
            }

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(jev_service.httpx, "Client", lambda **kwargs: MockClient())

    result = jev_service.guard_tool_call(
        tool="trade_ai_test",
        action="Test action",
    )

    assert result["decision"] == "allow"
    assert result["confidence"] == 0.91


def test_guard_tool_call_rate_limit(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    class MockResponse:
        status_code = 429

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(jev_service.httpx, "Client", lambda **kwargs: MockClient())

    with pytest.raises(jev_service.JevError, match="rate limit"):
        jev_service.guard_tool_call(
            tool="trade_ai_test",
            action="Test action",
        )


def test_guard_tool_call_rejects_invalid_decision(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "code": 0,
                "message": "ok",
                "data": {
                    "decision": "invalid",
                },
            }

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(jev_service.httpx, "Client", lambda **kwargs: MockClient())

    with pytest.raises(jev_service.JevError, match="invalid decision"):
        jev_service.guard_tool_call(
            tool="trade_ai_test",
            action="Test action",
        )
