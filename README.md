# fv-match

> Competition-agnostic football match-outcome fair-value engine. Phase 0 scaffold complete.

Estimates home/draw/away (and full scoreline) probabilities, de-viggs Polymarket prices, and only proposes bets on positive edge (fractional Kelly sized). Edge proven via CLV on historical data before live deployment (FWC 2026 target).

**Status**: Phase 0 — skeleton + deterministic math modules (`edge/devig.py`, `edge/kelly.py`) + tests green. All other modules are typed stubs with docstrings. CI (ruff/mypy/pytest) passes. Ready for iterative implementation.

See `CLAUDE.md` for pipeline, invariants, and module map.

## Quick start (user machine with uv)

```bash
git clone <repo>
cd fv-match
uv sync --all-extras
uv run pre-commit install
uv run fvmatch --help
uv run pytest
```

## Implemented (green)

- `edge/devig.py`: `multiplicative`, `power`, `shin`, `devig` dispatcher (default shin). Pure, fully typed.
- `edge/kelly.py`: `kelly_fraction`, `fractional_kelly`, `joint_match_stakes`. Pure, typed, with correlation simplification documented.
- Full test coverage for above in `tests/test_devig.py`, `tests/test_kelly.py`.
- Repo scaffolding, Supabase schema, config, CLI stubs, CI, pre-commit, etc.

## Next steps (Phase 1+)

1. Implement `data/` ingestors (fixtures from football-data.org or equiv + Gamma live via their API; results backfill; Elo ratings; market snapshots + close capture).
2. `model/dixon_coles.py`: fit on historical (Poisson-ish with Dixon-Coles time decay + low-score corr), predict scoreline matrix + marginal H/D/A.
3. `model/ratings_prior.py`: Elo or Massey for sparse teams (esp. international).
4. `model/calibration.py`: reliability plots, log-loss vs closing line.
5. `edge/gate.py`: edge > threshold + liquidity/volume gate.
6. `accounting/`: P&L resolver, CLV calculator (entry vs close).
7. `execution/client.py`: thin adapter to existing Polymarket CLOB v2 bot (pass stakes, outcomes; respect dry_run).
8. CLI commands wired to above + paper trading mode.
9. Historical backtest harness (CLV as primary metric) + paper on current season.
10. (Later) live with DRY_RUN=false only after CLV validation passes.

**Never** remove the DRY_RUN + CLV gate invariant.

## Dev

- Lint: `uv run ruff check . && uv run ruff format --check .`
- Type: `uv run mypy src`
- Test: `uv run pytest -q`
- All must pass before commit. pre-commit configured.

Built with ❤️ for truth-seeking in sports markets. Beat the close.