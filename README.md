# PolyQuant Intelligence V6

Prediction-market quantitative research and validation terminal with persistent Paper accounting, automatic settlement and end-to-end decision audit.

Core chain:

`Market → Evidence/Features → Prediction ID → Risk Decision ID → Paper/Live Result → Resolution → Paper Settlement → Calibration/Scorecard`

## V6 adds

- **Automatic Paper settlement**: when a market is resolved, winning shares pay `$1`, losing shares pay `$0`, cash and realized PnL are updated, positions are closed, and the settlement is persisted.
- **Settlement replay after restart**: trades and settlements are replayed chronologically, so a restarted process reconstructs the same Paper account.
- **Persistent starting bankroll**: the first Paper starting cash is stored in SQLite; changing `.env` later does not silently rewrite historical account economics.
- **Decision audit ledger**: each accepted/rejected Paper or Live request records market, Prediction ID, action, request, RiskDecision and result ID.
- **Trade traceability**: `GET /api/audit/trades/{trade_id}` traces a Paper trade back to its risk decision and prediction.
- **Resolved-market lock**: new Paper entries are rejected once a market has a recorded resolution.

V5 capabilities remain: model/category scorecards, CSV/JSON dataset export, maintenance loop, anti-pyramiding automatic Paper, conservative backtest, Smart Money, evidence-aware probability, experiments and validation gates.

## Quick start

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```
Open `http://localhost:8000`.

Offline:
```bash
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## Audit / settlement APIs

- `GET /api/audit/decisions?limit=100`
- `GET /api/audit/trades/{trade_id}`
- `POST /api/calibration/resolve` — saves resolution and settles matching Paper position
- `POST /api/calibration/sync` — conservative public resolution sync + Paper settlement
- `GET /api/paper/account`

Research/validation:
- `GET /api/analytics/scorecards`
- `GET /api/datasets/predictions.csv`
- `GET /api/validation/auto`
- `GET /api/maintenance/status`

## Safety

Automatic execution is still Paper-only. Validation and scorecards never unlock real money. Live execution remains disabled by default, explicit-confirmation gated, hard-notional limited, and geoblock fail-closed. No restriction-bypass logic is included.

## Validate
```bash
python -m compileall -q polyquant tests scripts
node --check web/app.js
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```
