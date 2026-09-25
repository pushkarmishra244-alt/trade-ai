# Trade AI

[![CI](https://github.com/pushkarmishra244-alt/trade-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/pushkarmishra244-alt/trade-ai/actions/workflows/ci.yml)
[![Security](https://img.shields.io/github/actions/workflow/status/pushkarmishra244-alt/trade-ai/security.yml?label=Security)](https://github.com/pushkarmishra244-alt/trade-ai/actions/workflows/security.yml)
[![Last Commit](https://img.shields.io/github/last-commit/pushkarmishra244-alt/trade-ai)](https://github.com/pushkarmishra244-alt/trade-ai/commits/main)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github)](https://github.com/pushkarmishra244-alt/trade-ai)

> Self-hosted algorithmic trading infrastructure with a fail-closed safety layer between strategy execution and real-money brokerage operations.

Trade AI is a self-hosted algorithmic trading system built around **OpenAlgo** and **Angel One SmartAPI**.

Its primary purpose is to establish an independent safety boundary between automated strategy logic and live broker execution.

```text
Strategy
   │
   ▼
OpenAlgo
   │
   ▼
┌─────────────────────────────┐
│       TRADE AI SAFETY       │
│                             │
│  Balance Verification       │
│  Live Order Guard           │
│  Kill Switch                │
│  Background Monitoring      │
│  Emergency Shutdown         │
│  Persistent Kill State      │
└──────────────┬──────────────┘
               │
               ▼
        Angel One SmartAPI

What is Trade AI?

Automated trading systems can continue operating even when their operating conditions are no longer safe.

A strategy may still be running.

The server may still be online.

The broker API may still be responding.

Yet the account state may be unknown or unsafe.

Trade AI treats execution safety as a separate infrastructure layer rather than something that individual strategies must implement themselves.

The system is designed around three principles:

* Fail closed
* Persist dangerous states
* Require explicit recovery

If the safety layer cannot reliably verify that trading is safe, live order execution is blocked.

⸻

Core Safety System

Persistent Kill Switch

The kill switch uses a configurable account-balance threshold.

Current threshold:

Available Balance ≤ ₹0

When triggered:

Account Balance
      │
      ▼
 ₹0 OR LESS
      │
      ▼
┌───────────────┐
│ KILL SWITCH   │
│   TRIGGERED   │
└───────┬───────┘
        │
        ├── Block new orders
        ├── Cancel pending orders
        ├── Attempt position closing
        ├── Persist KILLED state
        └── Prevent automatic revival

The kill state is stored persistently and survives application restarts.

Adding funds back to the account does not automatically reactivate trading.

⸻

Fail-Closed Behavior

Trade AI treats an unknown account state as unsafe.

Account State	Trading
Positive verified balance	Allowed
Balance = ₹0	Blocked
Balance < ₹0	Blocked
Broker authentication unavailable	Blocked
Balance API fails	Blocked
Invalid balance response	Blocked
Kill state already latched	Blocked

The intended behavior is:

Broker unavailable
       │
       ▼
Balance unknown
       │
       ▼
Trading BLOCKED

rather than allowing the strategy to continue operating without verified account state.

⸻

Protected Order Paths

Safety checks are integrated into the major live-order paths:

* Normal orders
* Basket orders
* Split orders
* Smart orders

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
       Broker API       Stop

The safety boundary is implemented at the execution layer rather than relying on every strategy to perform its own safety checks.

⸻

Emergency Shutdown

When the kill switch transitions into the killed state, Trade AI can initiate an emergency sequence:

1. Cancel pending orders
2. Attempt to close open positions
3. Persist the KILLED state
4. Block subsequent live orders

The emergency sequence has been tested using mocked broker operations.

Real broker-side cancellation and position-closing behavior should be independently validated under controlled conditions before relying on it with significant capital.

⸻

Background Safety Monitor

Trade AI includes a dedicated background monitor:

services/kill_switch_monitor.py

Current polling interval:

15 seconds

The monitor checks:

* Broker authentication
* Account availability
* Available balance
* Kill-switch state

It runs independently through systemd:

openalgo-kill-switch.service

This separates account-safety monitoring from the trading strategy process.

⸻

Kill Switch State Machine

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

Safety Components

Component	Responsibility
trading_kill_switch.py	Balance verification and persistent kill state
live_order_guard.py	Blocks unsafe live orders
kill_switch_monitor.py	Background account monitoring
kill_switch_emergency.py	Emergency cancellation and position-closing sequence
reset_kill_switch.py	Controlled manual recovery

⸻

Project Structure

trade-ai/
│
├── broker/
│   └── angel/
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
│
├── app.py
├── .env
└── ...

⸻

Architecture

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
                                   ▼
                         ┌─────────────────────┐
                         │   Angel One         │
                         │   SmartAPI          │
                         └─────────────────────┘

⸻

Infrastructure

Trade AI currently runs as a self-hosted deployment.

Component	Technology
Cloud	Oracle Cloud
Operating System	Ubuntu 22.04 LTS
Architecture	x86_64
Application	OpenAlgo
Broker	Angel One SmartAPI
Web Server	Nginx
Process Manager	systemd
Backend Runtime	Python 3.12
Frontend Runtime	Node.js 24
Frontend	React
Database	OpenAlgo storage layer

Application Flow

Internet
   │
   ▼
 Nginx
   │
   ▼
OpenAlgo
   │
   ├──────────────────┐
   ▼                  ▼
Trading Engine    Trade AI Safety
   │                  │
   └────────┬─────────┘
            ▼
      Angel One API

⸻

Technology Stack

Trading Infrastructure

* OpenAlgo
* Angel One SmartAPI
* Python
* React
* Nginx
* systemd
* Oracle Cloud

Safety Layer

* Persistent kill-switch state
* Balance verification
* Live-order guards
* Background monitoring
* Emergency shutdown sequence
* Explicit manual recovery

Development & Quality

* GitHub Actions
* Python testing
* Frontend linting
* Frontend build validation
* Playwright
* Bandit
* pip-audit

⸻

CI & Security

Trade AI uses GitHub Actions for automated project verification.

CI

The CI workflow validates major backend and frontend components, including:

* Backend checks
* Backend tests
* Frontend linting
* Frontend tests
* Frontend builds
* End-to-end testing
* Security-related checks

Security

The dedicated security workflow runs:

* Bandit security scanning
* pip-audit
* SARIF security reporting
* Artifact generation for security reports

Security scanning runs on pushes to main, pull requests, and the scheduled weekly security run.

⸻

Testing

The safety system has been tested for the following behaviors.

Balance Lifecycle

₹10,000 → ALLOWED
₹0      → KILLED
₹5,000  → STILL KILLED

Restart Persistence

The kill state survives:

* OpenAlgo restart
* Kill-switch monitor restart

Order Blocking

A mocked broker execution path confirms that the broker order function is not reached while the kill switch is active.

Emergency Sequence

The cancellation → position-closing sequence has been tested with mocked broker functions.

Real broker emergency behavior requires separate controlled validation.

⸻

Security

Never commit credentials or private infrastructure secrets.

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

Use environment variables or the application’s secure credential storage.

⸻

Recovery

The kill switch is intentionally persistent.

Example:

₹10,000
   │
   ▼
ACTIVE
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

Recovery requires an explicit reset operation.

The reset operation must first verify a positive account balance and active broker authentication before clearing the kill state.

⸻

Development Status

Trade AI is an active development project.

Current focus:

* Broker connectivity
* Automated execution infrastructure
* Live-order protection
* Balance monitoring
* Fail-closed behavior
* Persistent kill state
* Emergency shutdown
* Server-side reliability

Strategy research and automated strategy selection are separate from the execution safety layer.

⸻

Roadmap

Completed

* [x]	OpenAlgo deployment
* [x]	Angel One integration
* [x]	Production process management
* [x]	Live order safety guard
* [x]	Balance-based kill switch
* [x]	Persistent KILLED state
* [x]	Background monitoring
* [x]	Emergency shutdown sequence
* [x]	Manual recovery mechanism
* [x]	CI workflow
* [x]	Security workflow

Planned

* [ ]	Comprehensive integration test suite
* [ ]	Broker failure simulation
* [ ]	Order-state reconciliation
* [ ]	Execution audit trail
* [ ]	Advanced risk limits
* [ ]	Strategy validation framework
* [ ]	Paper-trading environment
* [ ]	Performance analytics

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

License

This project follows the licensing terms of its underlying OpenAlgo codebase and its applicable dependencies.

⸻

<div align="center">

Trade AI

Self-hosted algorithmic trading infrastructure with an independent execution-safety layer.

</div>
```


