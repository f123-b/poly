# PolyQuant Intelligence V3

Polymarket / prediction-market quantitative research, forecasting, backtesting and paper-trading terminal.

The system is designed around an auditable decision chain:

`Market -> Features -> Evidence -> Probability -> Edge -> Hard Risk -> Paper/Live Gate -> Resolution -> Calibration`

## V3 highlights

- Public Polymarket market/order-book ingestion with automatic offline Demo fallback
- Persistent SQLite research warehouse for market, feature, prediction and evidence snapshots
- Opportunity ranking with spread/depth/imbalance/liquidity features
- Evidence-aware probability ensemble with hard-bounded external influence
- Optional OpenAI-compatible research model with capped weight
- Cross-market relation graph and subset-probability anomaly detection
- Resolved-market Brier / Log Loss / ECE calibration
- Smart-money profiles with safe demo fallback when remote data is unavailable
- Immutable experiment registry
- Paper broker, automatic Paper loop, portfolio and hard risk engine
- Backtesting with fees/slippage and experiment capture
- Optional live executor with geoblock preflight, explicit confirmation and hard notional limits
- Chinese multi-view research dashboard
- CI: compile, tests and offline V3 smoke path

> Automatic execution remains **Paper-only**. Live real-money execution is disabled by default and fail-closed.

## Start with Docker

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000`.

## Local Python

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
python -m polyquant
```

For a completely offline run set:

```env
POLYQUANT_MODE=demo
```

## Research APIs

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/markets`
- `GET /api/opportunities`
- `GET /api/markets/{market_id}`
- `GET /api/markets/{market_id}/evidence`
- `GET /api/events`
- `GET /api/research/history`
- `GET /api/cross-market/anomalies`
- `GET /api/cross-market/graph-anomalies`
- `GET /api/smart-money/leaderboard`
- `GET /api/smart-money/profiles`
- `GET /api/calibration/history`
- `POST /api/calibration/resolve`
- `GET/POST /api/experiments`
- `GET /api/paper/account`
- `POST /api/paper/orders`
- `POST /api/auto/start|stop|run-once`
- `POST /api/backtest`
- `GET /api/live/preflight`
- `POST /api/live/orders`

## V3 research warehouse

SQLite remains the zero-config default. V3 stores normalized snapshots in `market_snapshots`, `feature_snapshots`, `prediction_snapshots`, `evidence_snapshots`, plus `trader_profiles`, `experiments` and `resolutions`. The interfaces are kept repository-local so the storage backend can later migrate to PostgreSQL/TimescaleDB without leaking SQL into strategy code.

## Safety invariants

1. Strategy code cannot bypass RiskEngine.
2. AI/evidence are research inputs and cannot call execution.
3. External evidence influence is capped by `POLYQUANT_EVIDENCE_MAX_INFLUENCE`.
4. LLM weight is capped by `POLYQUANT_LLM_MAX_WEIGHT`.
5. Automatic execution remains Paper-only.
6. Live execution is opt-in, geoblock checked and explicitly confirmed per order.
7. No VPN/proxy/geographic-restriction bypass logic is provided.

This is a research platform, not a claim of profitable alpha. Use Paper and calibration data before considering any live deployment.
