# fv-match — Ops Notes (Phase 0)

**What it is**: Competition-agnostic football (soccer) match-outcome fair-value engine. Estimates H/D/A and full scoreline probabilities via Dixon-Coles + Elo prior, compares to de-vigged Polymarket (Gamma/CLOB) prices, and surfaces +EV bets sized by fractional Kelly only when model edge exceeds threshold after liquidity gates. First live target: FIFA World Cup 2026. Reuses existing Polymarket CLOB v2 bot as dumb executor; this repo is the probabilistic brain + risk engine.

**Pipeline (invariant)**: `data (fixtures/results/ratings/markets) → model (Dixon-Coles fit + ratings prior → scoreline matrix + H/D/A probs) → edge (de-vig prices → model vs market edge + fractional Kelly stake) → execution (CLOB adapter, only if DRY_RUN=false) → accounting (realized P&L + CLV tracking)`.

**Key invariant**: **Nothing places a real order unless `DRY_RUN=false` AND a positive-CLV validation gate has passed on historical fixtures.** All paths default to dry-run; CLV (entry vs closing line) is the north-star metric — beating the close proves edge before results resolve. No live money without it.

**Module map**:
- `src/fvmatch/config.py`: pydantic-settings env config (DRY_RUN, thresholds, Supabase creds, MODEL_VERSION).
- `src/fvmatch/cli.py`: typer entrypoint (backfill, fit, paper, report stubs).
- `src/fvmatch/data/`: Supabase client + typed helpers; stubs for fixtures/results/ratings/market snapshots (Gamma + CLOB).
- `src/fvmatch/model/`: `dixon_coles.py` (fit/predict), `ratings_prior.py` (Elo), `calibration.py` (logloss vs market).
- `src/fvmatch/edge/`: `devig.py` (IMPLEMENTED: multiplicative/shin/power), `kelly.py` (IMPLEMENTED: frac Kelly + joint), `gate.py` (stub: threshold + liq).
- `src/fvmatch/accounting/`: `resolve.py`, `clv.py` (stubs).
- `src/fvmatch/execution/client.py`: adapter to CLOB bot (no-op in dry-run).
- `supabase/migrations/0001_init.sql`: core tables (competitions, teams, fixtures, ratings, markets, snapshots, model_probs, bets, clv) — competition-agnostic.
- `tests/`: only deterministic math tests for devig/kelly (green CI).

**Current phase**: Phase 0 — scaffold complete. Deterministic spine (devig + kelly) + full skeleton + types + CI green. Next: implement data ingestion (Gamma live + historical), model (Dixon-Coles), gate/execution, accounting + CLV, then backtest harness. Do not remove DRY_RUN guardrails.

All code is typed, lint-clean, test-covered on the math core. Secrets never committed.