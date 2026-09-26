import pytest

from services import jev_service


def mock_client(monkeypatch, status_code=200, body=None):
    class MockResponse:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return body

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(
        jev_service.httpx,
        "Client",
        lambda **kwargs: MockClient(),
    )


def test_guard_tool_call_requires_api_key(monkeypatch):
    monkeypatch.delenv("JEV_API_KEY", raising=False)

    with pytest.raises(jev_service.JevError, match="not configured"):
        jev_service.guard_tool_call(
            tool="test_tool",
            action="test action",
        )


@pytest.mark.parametrize("decision", ["allow", "confirm", "review", "deny"])
def test_guard_tool_call_accepts_valid_decisions(monkeypatch, decision):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    mock_client(
        monkeypatch,
        body={
            "code": 0,
            "message": "ok",
            "data": {
                "decision": decision,
                "confidence": 0.9,
                "probabilities": {},
                "guidance": "",
                "guidance_source": "jev_preset",
            },
        },
    )

    result = jev_service.guard_tool_call(
        tool="trade_ai_test",
        action="Test action",
    )

    assert result["decision"] == decision


def test_require_jev_allow_allows_only_allow(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    mock_client(
        monkeypatch,
        body={
            "code": 0,
            "message": "ok",
            "data": {
                "decision": "allow",
                "confidence": 0.91,
                "probabilities": {},
            },
        },
    )

    result = jev_service.require_jev_allow(
        tool="trade_ai_test",
        action="Test action",
    )

    assert result["decision"] == "allow"


@pytest.mark.parametrize("decision", ["confirm", "review", "deny"])
def test_require_jev_allow_fails_closed(monkeypatch, decision):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    mock_client(
        monkeypatch,
        body={
            "code": 0,
            "message": "ok",
            "data": {
                "decision": decision,
            },
        },
    )

    with pytest.raises(
        jev_service.JevError,
        match=f"Jev blocked action: {decision}",
    ):
        jev_service.require_jev_allow(
            tool="trade_ai_test",
            action="Test action",
        )


def test_guard_tool_call_rate_limit(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")
    mock_client(monkeypatch, status_code=429)

    with pytest.raises(jev_service.JevError, match="rate limit"):
        jev_service.guard_tool_call(
            tool="trade_ai_test",
            action="Test action",
        )


def test_guard_tool_call_rejects_invalid_decision(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")

    mock_client(
        monkeypatch,
        body={
            "code": 0,
            "message": "ok",
            "data": {
                "decision": "invalid",
            },
        },
    )

    with pytest.raises(jev_service.JevError, match="invalid decision"):
        jev_service.guard_tool_call(
            tool="trade_ai_test",
            action="Test action",
        )


def test_guard_tool_call_rejects_http_failure(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev_test_key")
    mock_client(monkeypatch, status_code=503)

    with pytest.raises(jev_service.JevError, match="HTTP 503"):
        jev_service.guard_tool_call(
            tool="trade_ai_test",
            action="Test action",
        )
