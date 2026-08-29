# PolyQuant Intelligence V5

A runnable prediction-market quantitative research, forecasting, validation, backtesting and **persistent Paper trading** terminal for Polymarket-style markets.

Core loop:

`Market → Feature → Evidence → Probability → Edge → Hard Risk → Persistent Paper → Resolution → Calibration → Scorecard → Experiment → Validation Gate`

## V5 production-readiness improvements

- **Persistent Paper account**: cash, positions and realized PnL are reconstructed from the SQLite trade ledger after every restart.
- **No accidental pyramiding by default**: automatic Paper skips markets that already have exposure unless `POLYQUANT_AUTO_ALLOW_PYRAMIDING=true` is explicitly set.
- **Model/category scorecards**: resolved predictions are evaluated by model version and market category using Brier, Log Loss, ECE, direction accuracy, average edge and confidence.
- **Dataset export**: prediction history can be returned as JSON or downloaded as CSV for analysis/model training.
- **Maintenance loop**: low-frequency research retention and conservative public resolution sync run independently from the trading loop.
- **Automatic validation snapshot**: `/api/validation/auto` combines actual calibration, Paper trade count and the best stored backtest experiment. It can recommend research/paper/shadow-live but never unlocks live funds.

## Existing capabilities

- Public market discovery, order books and price history with deterministic Demo fallback
- persistent market / feature / prediction / evidence warehouse
- bounded evidence-aware probability components and optional capped LLM research input
- cross-market relation/anomaly analysis
- Smart Money leaderboard, profiles and market-flow scoring
- conservative backtest with liquidity participation, latency, slippage, fees and partial fills
- experiment registry, resolved-market calibration, Fractional Kelly and hard portfolio risk rules
- automatic Paper loop and optional fail-closed live adapter with geoblock preflight + explicit confirmation
- Chinese dashboard, Docker, CI and fully offline smoke validation

## Quick start

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000`.

Offline mode:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## V5 APIs

Research/analytics:
- `GET /api/opportunities`
- `GET /api/markets/{id}/research-history`
- `GET /api/analytics/scorecards`
- `GET /api/datasets/predictions`
- `GET /api/datasets/predictions.csv`

Calibration/validation/maintenance:
- `GET /api/calibration/history`
- `POST /api/calibration/sync`
- `POST /api/validation/gate`
- `GET /api/validation/auto`
- `GET /api/maintenance/status`
- `POST /api/maintenance/run-once`

Paper/backtest:
- `GET /api/paper/account`
- `POST /api/paper/orders`
- `GET|POST /api/auto/*`
- `POST /api/backtest`
- `GET|POST /api/experiments`

Live remains opt-in and fail-closed:
- `GET /api/live/preflight`
- `POST /api/live/orders`

## Persistence semantics

`paper_trades` is the append-only source of truth for Paper execution. On service startup V5 replays the ledger and applies the latest saved market marks. Deleting the SQLite database intentionally resets Paper/research state; restarting the service does not.

## Safety invariants

1. AI, evidence and Smart Money cannot call execution directly.
2. Automatic execution remains Paper-only.
3. Repeated automatic entries are disabled by default.
4. RiskEngine remains authoritative over entries.
5. Validation Gate/Scorecards never enable live trading.
6. Live execution remains disabled by default, geoblock checked, explicitly confirmed and hard-notional limited.
7. No geographic-restriction bypass logic is included.
8. Backtest/Paper results are not a guarantee of future profitability.

## Validation

```bash
pip install -e '.[dev]'
python -m compileall -q polyquant tests scripts
node --check web/app.js
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```
