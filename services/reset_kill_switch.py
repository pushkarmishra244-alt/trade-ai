from services.auth_db import get_first_available_api_key
from services.trading_kill_switch import STATE_FILE, check_balance


def main() -> int:
    if not STATE_FILE.exists():
        print("Kill switch is not latched.")
        return 0

    api_key = get_first_available_api_key()
    if not api_key:
        print("RESET BLOCKED: no active broker authentication.")
        return 1

    result = check_balance(api_key)

    if result.get("killed"):
        print(f"RESET BLOCKED: {result.get('reason', 'account safety check failed')}")
        return 1

    balance = result.get("availablecash")
    if balance is None or balance <= 0:
        print("RESET BLOCKED: balance is not positive.")
        return 1

    STATE_FILE.unlink(missing_ok=True)
    print(f"Kill switch RESET. Verified available balance: ₹{balance:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
