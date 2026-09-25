from typing import Any

from services.trading_kill_switch import check_balance


def check_live_order_allowed(api_key: str) -> tuple[bool, dict[str, Any]]:
    if not api_key:
        return False, {
            "status": "error",
            "message": "Kill switch: missing OpenAlgo API key",
        }

    result = check_balance(api_key)

    if not result.get("allowed"):
        return False, {
            "status": "error",
            "message": f"Kill switch: {result.get("reason", "Trading blocked")}",
        }

    return True, {
        "status": "success",
        "availablecash": result.get("availablecash"),
    }
