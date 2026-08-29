# V3 Data Model

V3 keeps SQLite as the zero-config operational store and adds normalized research tables so the app remains runnable without external infrastructure.

- `market_snapshots`: normalized market state over time.
- `feature_snapshots`: computed feature vector over time.
- `prediction_snapshots`: indexed probability/model output for research queries.
- `evidence_snapshots`: evidence payload audit trail.
- `trader_profiles`: cached smart-money profile snapshots.
- `experiments`: immutable experiment metadata/results.
- `resolutions`: authoritative/manual resolution labels used for calibration.

The schema is intentionally portable to PostgreSQL/TimescaleDB later; table APIs remain repository-local rather than leaking SQL into strategies.
