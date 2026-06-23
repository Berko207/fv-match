# fv-match — Ops Notes (Phase 0)

**What it is**: Competition-agnostic football (soccer) match-outcome fair-value engine. Estimates H/D/A and full scoreline probabilities via Dixon-Coles + Elo prior, compares to de-vigged Polymarket (Gamma/CLOB) prices, and surfaces +EV bets sized by fractional Kelly only when model edge exceeds threshold after liquidity gates. First live target: FIFA World Cup 2026. Reuses existing Polymarket CLOB v2 bot as dumb executor; this repo is the probabilistic brain + risk engine.

**Pipeline (invariant)**: `data (fixtures/results/ratings/markets) → model (Dixon-Coles fit + ratings prior → scoreline matrix + H/D/A probs) → edge (de-vig prices → model vs market edge + fractional Kelly stake) → execution (CLOB adapter, only if DRY_RUN=false) → accounting (realized P&L + CLV tracking)`.

**Key invariant**: **Nothing places a real order unless `DRY_RUN=false` AND a positive-CLV validation gate has passed on historical fixtures.** All paths default to dry-run; CLV (entry vs closing line) is the north-star metric — beating the close proves edge before results resolve. No live money without it.

**Repo layout** (single project root — do not nest another clone inside this directory):
- `src/fvmatch/`, `tests/`, `examples/`, `supabase/` — Python engine + CLI (`uv run fvmatch …`)
- `web/` — Next.js dashboard (TypeScript port of the math core for Vercel; deploy root = `web/`)

**Module map**:
- `src/fvmatch/config.py`: pydantic-settings env config (DRY_RUN, thresholds, model params, Supabase creds, MODEL_VERSION).
- `src/fvmatch/cli.py`: typer entrypoint — `analyze` (IMPLEMENTED, headline), `fit`/`paper`/`report` (IMPLEMENTED, offline file-driven), `backfill` (Supabase-gated).
- `src/fvmatch/engine.py`: IMPLEMENTED — end-to-end fair-value pipeline glue (`analyze_match`).
- `src/fvmatch/data/`: Supabase `store.py` + typed helpers (stubs); `fixtures.py`/`results.py`/`ratings.py` (backfill stubs); `market.py` (snapshot/CLV scaffold); `polymarket.py` (lightweight Gamma odds for CLI); `polymarket/` package (Gamma/CLOB clients + constants); `seed/international_elo.json` bundled ratings (mirrored in `web/src/data/` for the TS app — keep in sync when updating).
- `src/fvmatch/model/`: `dixon_coles.py` (IMPLEMENTED: MLE fit + Elo→λ prior + scoreline matrix), `ratings_prior.py` (IMPLEMENTED: Elo), `calibration.py` (IMPLEMENTED: logloss/reliability/CLV).
- `src/fvmatch/edge/`: `devig.py` (IMPLEMENTED), `kelly.py` (IMPLEMENTED), `gate.py` (IMPLEMENTED: edge + liquidity + filter).
- `src/fvmatch/accounting/`: `resolve.py` (IMPLEMENTED: P&L), `clv.py` (IMPLEMENTED: CLV).
- `src/fvmatch/execution/`: `client.py` (CLOB adapter, no-op in dry-run), `clob.py` (low-level CLOB helpers).
- `web/src/core/`: TS port of engine, devig, gate, kelly, ratings, polymarket fixtures fetch.
- `web/src/app/api/`: `analyze` + `fixtures` API routes.
- `supabase/migrations/0001_init.sql`: core tables (competitions, teams, fixtures, ratings, markets, snapshots, model_probs, bets, clv) — competition-agnostic.
- `tests/`: deterministic tests for devig, kelly, model, ratings, gate, accounting, calibration, engine (green CI).
- `examples/`: sample `results`/`slate`/`bets` JSON for fit/paper/report.

**Current phase**: Functional engine + web UI. Full offline pipeline runs end-to-end (`fvmatch analyze` and the `web/` dashboard); math core + model + gate + accounting implemented and tested; types + lint + CI green. Next: real data ingestion (Gamma live + historical results backfill), Supabase persistence wiring, robust market auto-discovery, and a backtest harness with CLV as the primary metric. Do not remove DRY_RUN guardrails; no live money without positive-CLV validation.

All code is typed, lint-clean, test-covered on the math core. Secrets never committed.