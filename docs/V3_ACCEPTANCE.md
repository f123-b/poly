# V3 Acceptance Criteria

A V3 delivery is accepted only when:

- Demo mode runs without network, wallet, API keys or external databases.
- Market scan persists market, feature and prediction snapshots.
- Evidence can adjust probability only through bounded, auditable weights.
- Smart-money endpoints degrade safely when remote data is unavailable.
- Backtest/Paper/Live keep the same strategy/risk interfaces.
- Auto execution is Paper-only.
- Live execution remains disabled by default and fail-closed.
- API exposes research history, calibration, experiments, risk/system status.
- Dashboard can inspect opportunities, evidence, smart money, calibration and experiments.
- CI compiles, runs tests and executes the offline smoke path.
