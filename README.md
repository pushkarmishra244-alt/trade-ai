Yes. The previous README reads like technical documentation. For a GitHub repository, Trade AI should feel like a serious engineering project first, with the safety architecture as the centerpiece.

Here is a more polished version you can use directly:

# Trade AI
> Automated trading infrastructure with a hard safety boundary between strategy logic and real-money execution.
Trade AI is a self-hosted algorithmic trading system built around [OpenAlgo](https://github.com/marketcalls/openalgo) and Angel One SmartAPI.
The project is focused on one problem that matters when automated software is connected to a real brokerage account:
**What happens when something goes wrong?**
Trade AI adds an independent, fail-closed safety layer that can stop new orders, cancel pending orders, flatten positions, and permanently latch the system into a `KILLED` state when account safety cannot be verified.
---
## The Architecture
```text
                         ┌─────────────────────┐
                         │   Trading Strategy  │
                         │     / Trading Bot   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      OpenAlgo       │
                         │   Trading Engine    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │       TRADE AI SAFETY        │
                    │                              │
                    │  Balance Verification       │
                    │  Kill Switch                │
                    │  Order Guard                │
                    │  Emergency Shutdown         │
                    │  Persistent Kill State      │
                    └──────────────┬───────────────┘
                                   │
                         ┌─────────┴─────────┐
                         │                   │
                         ▼                   ▼
                  Cancel Orders        Close Positions
                         │                   │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌─────────────────────┐
                         │   Angel One         │
                         │   SmartAPI          │
                         └─────────────────────┘

The important design decision is simple:

A trading strategy never gets the final say on whether an order can reach the broker.

⸻

Why Trade AI?

Automated trading software can continue operating long after a human would have noticed that something is wrong.

A strategy can be profitable.

The server can be online.

The API can be responding.

And the system can still be unsafe to trade.

Trade AI therefore treats execution safety as a separate system, rather than something embedded inside individual strategies.

The result is a layered approach:

Strategy
   ↓
Execution
   ↓
Safety Verification
   ↓
Broker

If the safety layer says NO, the order stops there.

⸻

Hard Kill Switch

The core of Trade AI is a persistent kill switch.

Current threshold:

Available Balance ≤ ₹0

When the threshold is reached:

ACCOUNT BALANCE
      │
      ▼
   ₹0 OR LESS
      │
      ▼
┌───────────────┐
│ KILL SWITCH   │
│    TRIGGERED  │
└───────┬───────┘
        │
        ├── Block new orders
        ├── Cancel pending orders
        ├── Close positions
        ├── Persist KILLED state
        └── Prevent automatic revival

But the system does not only react to a zero balance.

It also fails closed when the balance cannot be reliably verified.

For example:

Broker unavailable
       ↓
Balance unknown
       ↓
Trading BLOCKED

rather than:

Broker unavailable
       ↓
Balance unknown
       ↓
Trading continues

⸻

Permanent Until Manually Reset

The kill switch is intentionally latched.

Example:

₹10,000
   │
   ▼
TRADING ACTIVE
   │
   ▼
₹0
   │
   ▼
KILLED
   │
   ▼
₹5,000 deposited
   │
   ▼
STILL KILLED

Adding money back to the account does not automatically restart trading.

A separate reset operation must verify the account and explicitly clear the kill state.

This prevents an unexpected account update from silently reactivating an automated strategy.

⸻

Protected Order Paths

Trade AI currently places safety checks around the major live-order paths:

* Normal orders
* Basket orders
* Split orders
* Smart orders

The broker execution boundary is therefore protected rather than relying on individual strategy authors to remember safety checks.

                Order Request
                     │
                     ▼
             ┌───────────────┐
             │  Safety Check │
             └───────┬───────┘
                     │
              ┌──────┴──────┐
              │             │
            SAFE          BLOCKED
              │             │
              ▼             ▼
          Broker API      Stop

⸻

Emergency Shutdown

When the kill switch transitions into the killed state, Trade AI can initiate an emergency sequence:

1. Cancel pending orders

Prevent outstanding orders from being executed.

2. Flatten positions

Attempt to close currently open positions.

3. Latch the system

Persist:

KILLED

4. Block future orders

Even if the strategy continues running, new live orders remain blocked.

⸻

Background Safety Monitor

The kill switch isn’t dependent on a trading strategy noticing the problem.

Trade AI runs a dedicated background monitor:

services/kill_switch_monitor.py

Current polling interval:

15 seconds

The monitor continuously checks:

* Broker authentication
* Account availability
* Available balance
* Kill-switch state

The monitor runs independently through systemd:

openalgo-kill-switch.service

This means the safety mechanism continues operating independently of the strategy process.

⸻

Fail-Closed by Design

One of the fundamental principles of Trade AI is:

Unknown is not safe.

If the system cannot determine the account state with sufficient confidence, it stops trading.

Examples:

Situation	Trading
Positive verified balance	Allowed
Balance = ₹0	Blocked
Balance < ₹0	Blocked
Broker authentication unavailable	Blocked
Balance API fails	Blocked
Invalid balance response	Blocked
Kill state already latched	Blocked

This is deliberately conservative.

⸻

Safety State Machine

                 ┌─────────────────────┐
                 │       ACTIVE        │
                 └──────────┬──────────┘
                            │
                  Balance ≤ threshold
                  OR verification fails
                            │
                            ▼
                 ┌─────────────────────┐
                 │       KILLED        │
                 └──────────┬──────────┘
                            │
                    Manual reset only
                            │
                            ▼
                 ┌─────────────────────┐
                 │  VERIFIED POSITIVE  │
                 │      BALANCE        │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │       ACTIVE        │
                 └─────────────────────┘

There is intentionally no automatic transition from KILLED back to ACTIVE.

⸻

Project Structure

trade-ai/
│
├── broker/
│   └── angel/
│       └── ...
│
├── services/
│   ├── basket_order_service.py
│   ├── place_order_service.py
│   ├── place_smart_order_service.py
│   ├── split_order_service.py
│   │
│   ├── trading_kill_switch.py
│   ├── live_order_guard.py
│   ├── kill_switch_monitor.py
│   ├── kill_switch_emergency.py
│   └── reset_kill_switch.py
│
├── frontend/
│   └── ...
│
├── app.py
├── .env
└── ...

Custom safety components

Component	Responsibility
trading_kill_switch.py	Balance verification and persistent kill state
live_order_guard.py	Prevents unsafe live orders
kill_switch_monitor.py	Background account monitoring
kill_switch_emergency.py	Cancel + flatten emergency sequence
reset_kill_switch.py	Controlled manual recovery

⸻

Infrastructure

Trade AI currently runs on an Oracle Cloud Ubuntu server.

OS              Ubuntu 22.04 LTS
Architecture    x86_64
Python          3.12.11
Node.js         24.13.0
npm             11.6.2
Web Server      Nginx
Application     OpenAlgo
Process Manager systemd
Broker          Angel One SmartAPI

Application architecture:

Internet
   │
   ▼
 Nginx
   │
   ▼
OpenAlgo
   │
   ├───────────────┐
   ▼               ▼
Trading Engine   Safety Layer
   │               │
   └───────┬───────┘
           ▼
      Angel One API

⸻

Reliability Philosophy

Trade AI is built around several simple principles.

1. Strategy and safety are separate

Strategies should decide what to trade.

The safety layer decides whether trading is permitted.

2. Fail closed

If account safety cannot be verified, don’t trade.

3. Kill states persist

A restart should not accidentally revive a disabled trading system.

4. Recovery requires verification

Returning to trading requires an explicit reset after a successful account check.

5. Test without touching the broker

Safety-critical functions are designed so their behavior can be tested using mocked broker operations before real-money execution is enabled.

⸻

Testing

The safety system has been tested for:

Balance lifecycle

₹10,000 → ALLOWED
₹0      → KILLED
₹5,000  → STILL KILLED

Restart persistence

The kill state survives:

* OpenAlgo restart
* Kill-switch monitor restart

Order blocking

A mocked broker execution path confirms that the broker order function is not reached while the kill switch is active.

Emergency sequence

The cancellation → position-closing sequence has been tested with mocked broker functions.

Real emergency cancellation/flattening should still be independently validated under controlled conditions before relying on it with significant capital.

⸻

Security

Never commit secrets.

The repository intentionally excludes local runtime state and sensitive credentials.

Do not commit:

.env
*.pem
*.key
*.key.txt
kill_switch.state

Never place the following in source control:

* Broker API credentials
* Authentication tokens
* SSH private keys
* TOTP secrets
* Passwords
* JWT secrets

Use environment variables or the application’s secure credential storage instead.

⸻

Development Status

Trade AI is currently an active development project.

The current implementation focuses on:

* Broker connectivity
* Automated execution infrastructure
* Order protection
* Balance monitoring
* Fail-closed behavior
* Persistent kill state
* Emergency shutdown
* Server-side reliability

Strategy research and automated strategy selection are separate concerns from the execution safety layer.

⸻

Roadmap

Potential future areas include:

[✓] OpenAlgo deployment
[✓] Angel One integration
[✓] Production process management
[✓] Live order safety guard
[✓] Balance-based kill switch
[✓] Persistent KILLED state
[✓] Background monitoring
[✓] Emergency shutdown sequence
[✓] Manual recovery mechanism
[ ] Comprehensive integration test suite
[ ] Broker failure simulation
[ ] Order-state reconciliation
[ ] Execution audit trail
[ ] Advanced risk limits
[ ] Strategy validation framework
[ ] Paper-trading environment
[ ] Performance analytics

⸻

Important

Trade AI is trading infrastructure, not a guarantee against financial loss.

A software safety layer cannot eliminate:

* Broker outages
* Network failures
* Exchange failures
* Slippage
* Partial fills
* Rejected orders
* API inconsistencies
* Infrastructure failures
* Market risk

The purpose of the safety architecture is to establish a controlled execution boundary and reduce the chance that an automated process continues trading when its operating conditions are no longer considered safe.

⸻

Repository

Trade AI

GitHub:

https://github.com/pushkarmishra244-alt/trade-ai

Built around:

* OpenAlgo
* Angel One SmartAPI
* Python
* React
* Nginx
* Ubuntu
* Oracle Cloud
* systemd

⸻

Core Idea

        AUTOMATED TRADING
               │
               ▼
        ┌──────────────┐
        │   OPENALGO   │
        └──────┬───────┘
               │
               ▼
       ┌─────────────────┐
       │   TRADE AI      │
       │  SAFETY LAYER   │
       └────────┬────────┘
                │
        ┌───────┴───────┐
        │               │
      SAFE            UNSAFE
        │               │
        ▼               ▼
     EXECUTE           KILL
        │               │
        ▼               ├── CANCEL
     BROKER             ├── FLATTEN
                        └── LOCK

The strategy decides what to do.
The safety layer decides whether it is allowed to do it.