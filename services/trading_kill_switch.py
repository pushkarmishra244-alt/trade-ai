from pathlib import Path
from threading import Lock
from typing import Any

from services.funds_service import get_funds
from utils.logging import get_logger

logger = get_logger(__name__)

STATE_FILE = Path("/home/ubuntu/openalgo/kill_switch.state")
THRESHOLD = 0.0
_lock = Lock()


def is_killed() -> bool:
    try:
        return STATE_FILE.read_text().strip() == "KILLED"
    except FileNotFoundError:
        return False


def latch() -> None:
    with _lock:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text("KILLED\n")
        tmp.replace(STATE_FILE)


def check_balance(api_key: str) -> dict[str, Any]:
    if is_killed():
        return {
            "allowed": False,
            "killed": True,
            "reason": "Kill switch is latched",
        }

    success, response, _ = get_funds(api_key=api_key)

    if not success:
        latch()
        logger.critical("KILL SWITCH: unable to verify account balance")
        return {
            "allowed": False,
            "killed": True,
            "reason": "Unable to verify account balance",
        }

    try:
        balance = float(response["data"]["availablecash"])
    except (KeyError, TypeError, ValueError):
        latch()
        logger.critical("KILL SWITCH: invalid balance response")
        return {
            "allowed": False,
            "killed": True,
            "reason": "Invalid account balance response",
        }

    if balance <= THRESHOLD:
        latch()
        logger.critical(
            "KILL SWITCH TRIGGERED: availablecash=%.2f threshold=%.2f",
            balance,
            THRESHOLD,
        )
        return {
            "allowed": False,
            "killed": True,
            "availablecash": balance,
            "reason": "Balance reached kill threshold",
        }

    return {
        "allowed": True,
        "killed": False,
        "availablecash": balance,
    }
