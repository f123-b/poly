# PolyQuant Intelligence V3 Plan

V3 turns the V2 research terminal into a persistent, auditable research platform.

## Stages
1. Historical snapshot warehouse for market/features/predictions/evidence.
2. Evidence-aware probability ensemble with bounded influence.
3. Smart-money trader profiles and market flow scoring.
4. Experiment registry and research snapshots.
5. Portfolio/risk observability endpoints.
6. Multi-view dashboard for opportunities, evidence, calibration, smart money, experiments and system health.
7. CI and offline smoke coverage for all V3 paths.

## Safety invariants
- AI and external evidence never call execution directly.
- Automatic loops remain Paper-only.
- Live execution stays opt-in, fail-closed and subject to existing hard limits and geoblock preflight.
- External text is treated as untrusted data.
