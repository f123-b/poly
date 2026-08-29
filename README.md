# PolyQuant Intelligence V7

Realtime prediction-market quantitative research, validation, Paper settlement and decision-audit terminal.

Core chain:

`Public Market Stream → Realtime Cache → Browser WebSocket → Research/Prediction → Risk Audit → Persistent Paper → Resolution/Settlement → Scorecard`

## V7 realtime layer

- `RealtimeMarketCache` stores current public quotes and full order books when book events are available.
- Non-Demo mode **prefers the current official Polymarket unified Python SDK**: `AsyncPublicClient.subscribe(MarketSpec(...))`.
- If `polymarket-client` is not installed or the upstream stream fails, the engine automatically falls back to public REST polling.
- Demo mode provides a deterministic network-free realtime heartbeat path for CI/local development.
- Local browser clients subscribe to `WS /ws/markets`; slow clients use bounded queues so they cannot create unbounded server memory growth.
- Realtime data is read-only. It has no execution reference and cannot bypass RiskEngine.

Install the official upstream realtime adapter when desired:

```bash
pip install -e '.[realtime]'
```

Base install still works without it and falls back automatically.

## Realtime APIs

- `GET /api/realtime/status`
- `GET /api/realtime/snapshot`
- `WS /ws/markets`

`/api/system/status` and `/api/health` also expose realtime mode, reconnect/fallback counters, cache size and last event time.

## Existing platform

V6 features remain: persistent starting bankroll, Paper trade+settlement replay, Resolution settlement at $1/$0, Prediction→RiskDecision→Trade audit chain, model/category scorecards, CSV dataset export, maintenance/resolution sync, conservative backtest, Smart Money, evidence-aware probability and fail-closed optional live execution.

## Quick start

```bash
git clone https://github.com/f123-b/poly.git
cd poly
cp .env.example .env
docker compose up --build
```
Open `http://localhost:8000`.

For fully offline validation:
```bash
pip install -e '.[dev]'
POLYQUANT_MODE=demo python -m polyquant
```

## Safety

Realtime, AI, Evidence and Smart Money are data/research inputs only. Automatic execution remains Paper-only. Live remains disabled by default, explicit-confirmation gated, hard-notional limited, and geoblock fail-closed. No restriction-bypass path is included.

## Validate
```bash
python -m compileall -q polyquant tests scripts
node --check web/app.js
pytest -q
POLYQUANT_MODE=demo python scripts/smoke.py
```
