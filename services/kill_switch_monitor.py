import time

from database.auth_db import get_first_available_api_key
from services.trading_kill_switch import check_balance, is_killed
from database.auth_db import get_auth_token_broker
from services.cancel_all_order_service import cancel_all_orders_with_auth
from services.close_position_service import close_position_with_auth
from services.kill_switch_emergency import emergency_flatten
from utils.logging import get_logger

logger = get_logger(__name__)

POLL_INTERVAL = 15


def main() -> None:
    logger.info("Kill-switch monitor started")

    while True:
        try:
            api_key = get_first_available_api_key()

            if not api_key:
                logger.critical(
                    "KILL SWITCH: no active broker authentication available"
                )
                # check_balance cannot verify without an API key.
                # The persistent kill latch is the fail-closed state.
                from services.trading_kill_switch import latch
                latch()
            else:
                was_killed = is_killed()
                result = check_balance(api_key)

                if result.get("killed"):
                    logger.critical(
                        "KILL SWITCH ACTIVE: %s",
                        result.get("reason", "Trading blocked"),
                    )

                    # Emergency actions run only when this monitor observes
                    # a fresh kill transition. A persistent KILLED state
                    # must not repeatedly submit flatten/cancel requests.
                    if not was_killed:
                        auth_token, broker = get_auth_token_broker(api_key)

                        if auth_token and broker:
                            emergency_result = emergency_flatten(
                                api_key,
                                cancel_all_orders_with_auth,
                                close_position_with_auth,
                                auth_token,
                                broker,
                            )
                            logger.critical(
                                "KILL SWITCH EMERGENCY: %s",
                                emergency_result,
                            )
                        else:
                            logger.critical(
                                "KILL SWITCH EMERGENCY: authentication unavailable; "
                                "cannot cancel/flatten"
                            )

                    time.sleep(POLL_INTERVAL)
                    continue

                logger.info(
                    "Kill-switch check OK: availablecash=%.2f",
                    result["availablecash"],
                )

        except Exception:
            logger.exception("KILL SWITCH MONITOR ERROR")
            from services.trading_kill_switch import latch
            latch()

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
