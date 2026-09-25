from typing import Any, Callable

from utils.logging import get_logger

logger = get_logger(__name__)


def emergency_flatten(
    api_key: str,
    cancel_fn: Callable[..., tuple[bool, dict[str, Any], int]],
    flatten_fn: Callable[..., tuple[bool, dict[str, Any], int]],
    auth_token: str,
    broker: str,
) -> dict[str, Any]:
    """
    Emergency cleanup after the kill switch triggers.

    This deliberately bypasses the normal new-order guard.
    It only performs cancellation/flattening and never clears KILLED.
    """

    if not api_key or not auth_token or not broker:
        return {
            "success": False,
            "cancel": {"success": False, "message": "Missing emergency authentication"},
            "flatten": {"success": False, "message": "Missing emergency authentication"},
        }

    original_data = {"apikey": api_key}

    cancel_success, cancel_response, cancel_status = cancel_fn(
        {},
        auth_token,
        broker,
        original_data,
    )

    flatten_data = {"apikey": api_key}

    flatten_success, flatten_response, flatten_status = flatten_fn(
        flatten_data,
        auth_token,
        broker,
        original_data,
    )

    logger.critical(
        "KILL SWITCH EMERGENCY RESULT: cancel=%s flatten=%s",
        cancel_success,
        flatten_success,
    )

    return {
        "success": cancel_success and flatten_success,
        "cancel": {
            "success": cancel_success,
            "status_code": cancel_status,
            "response": cancel_response,
        },
        "flatten": {
            "success": flatten_success,
            "status_code": flatten_status,
            "response": flatten_response,
        },
    }
