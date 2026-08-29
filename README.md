# PolyQuant Intelligence V4

A runnable Polymarket / prediction-market quantitative research, forecasting, validation, backtesting and paper-trading terminal.

Core loop:

`Market → Feature → Evidence → Probability → Edge → Hard Risk → Paper → Resolution → Calibration → Experiment → Validation Gate`

## What V4 adds

V4 builds on the V3 research warehouse and adds the controls needed for long-running strategy validation:

- conservative backtest execution with liquidity participation limits
- explicit latency + slippage + fee accounting
- partial-fill simulation and turnover/cost metrics
- public resolved-market sync for calibration labels (non-Demo mode)
- strategy validation gate using resolved samples, Paper trades, Brier score, ROI, drawdown and Sharpe
- research-snapshot retention to prevent unbounded SQLite growth
- V4 dashboard controls for Resolution sync and Validation Gate

The validation gate can recommend `research`, `paper`, or `shadow-live`, but **never unlocks real-money execution automatically**.

## Existing platform capabilities

- Polymarket public market discovery, order books and price history with Demo fallback
- persistent market / feature / prediction / evidence research warehouse
- bounded evidence-aware probability components
- optional capped OpenAI-compatible research model
- cross-market relation/anomaly analysis
- Smart Money leaderboard, trader profiles and market-flow scoring
- experiment registry and demo parameter grid
- resolved-market Brier / Log Loss / ECE calibration
- Fractional Kelly, portfolio exposure rules and hard RiskEngine
- Paper Broker + automatic Paper trading loop
- optional fail-closed live executor with geoblock preflight and explicit per-order confirmation
- Chinese browser dashboard, Docker, CI and offline smoke validation

## Quick start

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000`.

Fully offline:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## V4 APIs

Research/data:
- `GET /api/markets`
- `GET /api/opportunities`
- `GET /api/markets/{id}/history`
- `GET /api/markets/{id}/research-history`
- `GET /api/markets/{id}/evidence`
- `GET /api/markets/{id}/smart-money`
- `GET /api/system/status`

Calibration/validation:
- `GET /api/calibration/history`
- `POST /api/calibration/resolve`
- `POST /api/calibration/sync`
- `POST /api/validation/gate`

Research experiments/backtest:
- `GET/POST /api/experiments`
- `POST /api/experiments/demo-grid`
- `POST /api/backtest`
- `POST /api/backtest/demo`

Paper/live:
- `GET /api/paper/account`
- `POST /api/paper/orders`
- `GET|POST /api/auto/*`
- `GET /api/live/preflight`
- `POST /api/live/orders`

## Conservative backtest input

Each point may include available liquidity:

```json
{"price":0.42,"model_probability":0.55,"available_liquidity":1000}
```

`execution_mode=conservative` caps each fill to `available_liquidity * max_participation`, applies `slippage_bps + latency_bps`, tracks fees, slippage cost, turnover and partial fills. Historical order-book depth is not always available, so this is deliberately a conservative approximation rather than a claim of exact replay.

## Resolution sync

`POST /api/calibration/sync` reads recently closed public markets and only labels a market when YES/NO prices are effectively settled (>= 0.995 vs <= 0.005). Ambiguous closed markets are skipped. Demo mode performs no network resolution sync.

## Safety invariants

1. AI, evidence and Smart Money cannot call execution directly.
2. Automatic execution is Paper-only.
3. RiskEngine remains authoritative over entries.
4. Validation Gate never enables live trading.
5. Live trading is disabled by default, geoblock checked, explicitly confirmed, and hard-notional limited.
6. No proxy/VPN/geographic-restriction bypass logic is included.
7. Backtest/Paper performance is not a guarantee of future profitability.

## Validation

```bash
pip install -e '.[dev]'
python -m compileall -q polyquant tests scripts
node --check web/app.js
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```
