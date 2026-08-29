# Architecture

## Decision pipeline

`Market data -> FeatureEngine -> ProbabilityEngine -> Strategy/Edge -> RiskEngine -> PaperBroker`

The V1 API does not permit an LLM or strategy to call an exchange executor directly. The optional LLM input is capped to 25% of the pre-calibration probability ensemble and the result is shrunk toward market probability.

## Modes

- `auto`: use Polymarket public Gamma/CLOB data; fall back to demo data on connectivity/API failure.
- `live-data`: same public market data preference, still Paper execution only.
- `demo`: deterministic bundled data, useful for offline validation.

## Safety boundary

V1 intentionally ships with **live execution disabled**. Public market data is production-capable; execution is paper-only. A future secure executor must sit behind the same `RiskEngine` and must never accept direct calls from AI providers.

## Persistence

SQLite is the zero-configuration V1 operational store for prediction and paper-trade audit records. This is deliberately isolated behind `Storage` so PostgreSQL/Timescale can replace it without changing strategy code.
