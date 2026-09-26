import os
from typing import Any

import httpx

JEV_API_URL = "https://www.jevai.org/api/v1/decisions/tool-guard"
JEV_TIMEOUT = 10.0


class JevError(Exception):
    """Raised when Jev cannot provide a valid decision."""


def _get_api_key() -> str:
    api_key = os.getenv("JEV_API_KEY", "").strip()

    if not api_key:
        raise JevError("JEV_API_KEY is not configured")

    return api_key


def guard_tool_call(
    *,
    tool: str,
    action: str,
    arguments_summary: list[str] | None = None,
    side_effects: list[str] | None = None,
    safeguards: list[str] | None = None,
    policy: list[str] | None = None,
    reversibility: str = "partially_reversible",
) -> dict[str, Any]:
    """
    Ask Jev to evaluate a consequential action.

    Jev only provides a decision. It never executes the action.
    The Trade AI safety layer remains authoritative.
    """

    api_key = _get_api_key()

    payload = {
        "tool": tool,
        "action": action,
        "arguments_summary": arguments_summary or [],
        "side_effects": side_effects or [],
        "safeguards": safeguards or [],
        "policy": policy or [],
        "reversibility": reversibility,
    }

    try:
        with httpx.Client(timeout=JEV_TIMEOUT) as client:
            response = client.post(
                JEV_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise JevError(f"Jev request failed: {exc}") from exc

    if response.status_code == 429:
        raise JevError("Jev rate limit reached; retry later")

    if response.status_code != 200:
        raise JevError(
            f"Jev returned HTTP {response.status_code}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise JevError("Jev returned invalid JSON") from exc

    if body.get("code") != 0:
        raise JevError(body.get("message", "Jev returned an error"))

    data = body.get("data")

    if not isinstance(data, dict):
        raise JevError("Jev response missing decision data")

    decision = data.get("decision")

    if decision not in {"allow", "confirm", "review", "deny"}:
        raise JevError("Jev returned an invalid decision")

    return {
        "decision": decision,
        "confidence": data.get("confidence"),
        "probabilities": data.get("probabilities", {}),
        "guidance": data.get("guidance", ""),
        "guidance_source": data.get("guidance_source", ""),
        "answers": data.get("answers", {}),
    }
