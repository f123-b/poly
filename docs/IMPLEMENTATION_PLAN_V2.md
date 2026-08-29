# PolyQuant Intelligence V2 implementation plan

This branch upgrades V1 into a more complete research/paper-trading terminal while preserving live-trading fail-closed behavior.

## Phase 1 - event intelligence
- Structured event/news evidence model
- Market-to-event matching
- Deterministic demo feed for offline runs
- Optional external JSON feed ingestion

## Phase 2 - persistence and calibration
- Event/evidence audit tables
- Resolved prediction outcomes
- Historical calibration metrics from stored predictions

## Phase 3 - cross-market graph
- Market relation graph (subset / mutually-exclusive / temporal)
- Logical anomaly scanner with explicit explanations

## Phase 4 - research API
- Event feed, market evidence, historical calibration and diagnostics endpoints

## Phase 5 - UI
- Research/event panel, model-vs-market probability, risk status and paper account dashboard

## Phase 6 - hardening
- Unit tests for matching, graph relations and persistence
- Documentation and delivery checklist

Live execution stays disabled by default and is not reachable from the automated paper-trading loop.
