Trade AI

A self-hosted algorithmic trading infrastructure built around OpenAlgo, Angel One SmartAPI, and a custom fail-closed trading safety layer.

The system is designed to provide a controlled execution environment for automated trading while ensuring that trading can be permanently halted when account funds or broker connectivity cannot be safely verified.

Overview

Trade AI currently uses the following architecture:

Trading Strategy / Bot
        │
        ▼
     OpenAlgo
        │
        ├── Live Order Guard
        │
        ├── Balance / Kill Switch
        │
        ├── Emergency Shutdown
        │
        ▼
 Angel One SmartAPI
        │
        ▼
    Angel One

The project runs on an Oracle Cloud Ubuntu server and uses OpenAlgo as the trading/execution platform.

Core Safety System

The primary custom component is the Trading Kill Switch.

The safety layer is designed around a fail-closed principle:

If the system cannot reliably verify that trading is safe, trading is blocked.

Kill conditions

The kill switch activates when:

* Available account balance reaches ₹0
* Account balance cannot be retrieved
* Broker authentication cannot be verified
* The broker returns an invalid or unusable balance response
* The kill switch has previously been latched

Current threshold:

Available Balance <= ₹0

Persistent kill state

Once triggered, the system writes:

KILLED

to a local state file:

kill_switch.state

This state is intentionally not stored in GitHub.

The kill state survives:

* OpenAlgo restarts
* Kill-switch monitor restarts
* Server/application restarts

Adding money back into the trading account does not automatically reactivate trading.

A manual reset is required.

Live Order Protection

Trade AI places a safety check between OpenAlgo’s order services and the broker execution layer.

Protected execution paths include:

* Normal orders
* Basket orders
* Split orders
* Smart orders

Before a live broker order is submitted, the system verifies:

OpenAlgo API authentication
        ↓
Kill-switch state
        ↓
Broker balance
        ↓
Trading allowed?
        ↓
Broker order execution

If the safety check fails, the broker order is never reached.

Emergency Shutdown

When the kill switch transitions into the killed state, the emergency handler is designed to:

1. Cancel pending orders
2. Close existing positions
3. Preserve the KILLED state
4. Prevent new orders from being submitted

The emergency sequence is implemented in:

services/kill_switch_emergency.py

The emergency handler was designed to be testable without making unintended broker calls.

Background Kill-Switch Monitor

A persistent monitoring process continuously checks the account state.

File:

services/kill_switch_monitor.py

The monitor:

* Checks broker authentication
* Reads account balance
* Detects kill conditions
* Latches the kill state
* Initiates the emergency sequence
* Continues running after the system is killed

Current polling interval:

15 seconds

The monitor runs as a systemd service:

openalgo-kill-switch.service

Manual Reset

The kill switch does not automatically reactivate after a kill event.

Manual reset is handled by:

services/reset_kill_switch.py

Reset is permitted only when:

* Broker authentication is available
* Account balance can be successfully verified
* Available balance is positive

Example:

KILLED
   │
   ├── Balance still invalid/zero
   │       ↓
   │     BLOCKED
   │
   └── Positive verified balance
           ↓
       RESET ALLOWED

Project Structure

The custom safety components are located in:

services/
├── trading_kill_switch.py
├── live_order_guard.py
├── kill_switch_monitor.py
├── kill_switch_emergency.py
└── reset_kill_switch.py

The existing OpenAlgo execution services modified for safety checks include:

services/
├── place_order_service.py
├── basket_order_service.py
├── split_order_service.py
└── place_smart_order_service.py

Technology Stack

Trading platform

* OpenAlgo
* Angel One SmartAPI

Backend

* Python
* Flask/OpenAlgo services
* Gunicorn
* PostgreSQL-compatible database infrastructure used by OpenAlgo

Frontend

* React
* Vite
* Node.js

Infrastructure

* Oracle Cloud Infrastructure
* Ubuntu 22.04 LTS
* Nginx
* systemd
* UFW

Python environment

Python 3.12.11

Frontend environment

Node.js 24.13.0
npm 11.6.2

Server Architecture

Internet
   │
   ▼
 Nginx :80/:443
   │
   ▼
OpenAlgo :5000
   │
   ├── Trading Services
   │
   ├── Safety Layer
   │
   └── Broker Integration
           │
           ▼
    Angel One SmartAPI

OpenAlgo itself listens locally on:

127.0.0.1:5000

The public-facing traffic is handled by Nginx.

Port 5000 is not intended to be publicly exposed.

Systemd Services

OpenAlgo

openalgo.service

Kill Switch

openalgo-kill-switch.service

Both services are configured to start automatically with the server.

Fail-Closed Design

The safety layer intentionally does not assume that missing information means everything is safe.

For example:

Broker unavailable
       ↓
Balance unknown
       ↓
Trading BLOCKED

Instead of:

Broker unavailable
       ↓
Balance unknown
       ↓
Continue trading

This is important for automated trading systems because an inability to verify account state should not be interpreted as a safe account state.

Testing

The kill-switch implementation has been tested for:

Normal operation

₹10,000
   ↓
Trading allowed

Kill condition

₹0
   ↓
KILL SWITCH
   ↓
Trading blocked

Persistent kill

₹0
 ↓
KILLED
 ↓
₹5,000 added
 ↓
Still KILLED

Restart persistence

The kill state was verified to survive:

* OpenAlgo restart
* Kill-switch monitor restart

Order blocking

A mocked broker execution path was tested to ensure that the broker order function is not reached when the kill switch is active.

Emergency sequence

The emergency handler was tested using mocked cancellation and position-closing functions to verify the intended sequence without triggering real broker operations.

Current Trading State

The system is currently designed to remain in:

KILLED

until explicitly reset after a successful positive-balance verification.

This is intentional during development and testing.

Security

Sensitive credentials must never be committed to this repository.

Do not commit:

.env
*.pem
*.key
*.key.txt
kill_switch.state

Broker API credentials, authentication tokens, SSH private keys, TOTP secrets, and other credentials should remain outside source control.

Deployment

Clone the repository:

git clone https://github.com/pushkarmishra244-alt/trade-ai.git
cd trade-ai

Create the Python environment:

python3.12 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements-nginx.txt

Configure the environment:

cp .sample.env .env

Then configure the required OpenAlgo and broker settings before starting the application.

Safety Philosophy

Trade AI separates strategy logic from execution safety.

A strategy can request a trade, but it cannot override the safety layer.

Strategy
   │
   │ "Place order"
   ▼
Safety Layer
   │
   ├── Is system killed?
   ├── Can account balance be verified?
   ├── Is balance above threshold?
   └── Is broker authentication valid?
   │
   ▼
Broker

The safety layer therefore acts as an independent control boundary between automated strategy logic and real-money execution.

Disclaimer

Trade AI is an experimental automated-trading infrastructure project.

Automated trading involves financial risk. The safety mechanisms in this repository are intended to reduce operational risk, not eliminate market, broker, network, software, or infrastructure risk.

Never assume that a software kill switch guarantees that a broker position can always be cancelled or closed. Broker outages, network failures, rejected orders, partial fills, exchange conditions, and other external failures can still occur.

⸻
