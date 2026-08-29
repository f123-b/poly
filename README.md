# PolyQuant Intelligence V8

A realtime prediction-market quantitative research and validation terminal where the **same fresh quote/order-book data can drive the UI, Feature Engine, Probability Engine and server-side risk revalidation**.

Core chain:

`Official Public WSS → Freshness-Checked Cache → Market Prior + OrderBook Features → Probability/Edge → Risk Audit → Persistent Paper → Settlement/Calibration`

## V8: realtime Quant Core

V7 introduced public streaming and browser WebSocket delivery. V8 moves realtime data into the actual quantitative decision path:

- `QuantService` uses fresh realtime YES/NO quotes to normalize the market probability before prediction.
- `FeatureEngine` receives a fresh cached full YES order book when available.
- Cache entries older than `POLYQUANT_REALTIME_STALE_SECONDS` are ignored automatically.
- Missing/stale books fall back to public CLOB REST; Demo falls back to deterministic `demo_book`.
- REST realtime fallback refreshes full books only for the top configurable N markets to control request volume.
- Paper/Live requests call `get_market()` and therefore re-run Feature/Probability/Risk using the current server-side realtime cache when available.

This removes the V7 gap where the browser could see newer prices than the strategy engine.

## Realtime setup

Base install works with REST fallback. For the current official Polymarket unified SDK public stream:

```bash
pip install -e '.[realtime]'
```

Configuration:

```env
POLYQUANT_REALTIME_ENABLED=true
POLYQUANT_REALTIME_PREFER_SDK=true
POLYQUANT_REALTIME_STALE_SECONDS=20
POLYQUANT_REALTIME_BOOK_REFRESH_LIMIT=5
```

APIs:
- `GET /api/realtime/status`
- `GET /api/realtime/snapshot`
- `WS /ws/markets`

## Existing production-validation controls

- persistent Paper trade ledger and starting bankroll
- automatic $1/$0 Paper settlement on Resolution
- Prediction ID → Risk Decision ID → Trade audit chain
- anti-pyramiding automatic Paper by default
- model/category Brier/LogLoss/ECE scorecards
- CSV prediction dataset export
- maintenance + conservative Resolution sync
- conservative liquidity/latency/slippage/partial-fill backtest
- experiments and validation gate
- Smart Money, bounded Evidence and optional low-weight LLM research input
- optional Live adapter remains disabled/fail-closed by default

## Quick start

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```
Open `http://localhost:8000`.

Offline validation:
```bash
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## Safety

Realtime data can influence probability/features, but never calls execution. All execution still passes deterministic server-side RiskEngine and audit. Automatic execution remains Paper-only. Live remains explicit-confirmation gated, hard-notional limited and geoblock fail-closed. No geographic-restriction bypass is present.

## Validate
```bash
python -m compileall -q polyquant tests scripts
node --check web/app.js
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```
