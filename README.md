# fv-match

> Competition-agnostic football match-outcome fair-value engine. Phase 0 scaffold complete.

Estimates home/draw/away (and full scoreline) probabilities, de-viggs market prices, and only proposes bets on positive edge (fractional Kelly sized). Edge proven via CLV on historical data before live deployment (FWC 2026 target).

**Status**: Functional end-to-end engine. The full pipeline (Elo prior → Dixon-Coles scoreline matrix → H/D/A → de-vig → edge → gated fractional Kelly) runs offline with no database or network required. Live Polymarket odds fetch is best-effort/optional. CI (ruff/mypy/pytest) green. `DRY_RUN` + CLV guardrails intact.

See `CLAUDE.md` for pipeline, invariants, and module map.

## Quick start

```bash
git clone <repo>
cd fv-match
uv sync --all-extras
uv run fvmatch --help

# Fair-value analysis for a single fixture (model-only):
uv run fvmatch analyze --home Portugal --away Uzbekistan

# ...with market odds → edge + Kelly stakes (neutral venue by default):
uv run fvmatch analyze --home Portugal --away Uzbekistan \
  --home-odds 1.28 --draw-odds 6.0 --away-odds 12.0

# Machine-readable output:
uv run fvmatch analyze --home Portugal --away Uzbekistan \
  --home-odds 1.28 --draw-odds 6.0 --away-odds 12.0 --json
```

## CLI commands

- `analyze` — end-to-end fair-value report for one fixture: model H/D/A + fair odds,
  de-vigged market consensus, per-outcome edge/EV, and gated fractional-Kelly stakes.
  Add `--home-field` for a home-advantage venue, `--elo-home/--elo-away` to override
  ratings, or `--poly-slug <slug>` to fetch live Polymarket odds (best-effort).
- `fit --results <file.json>` — fit a Dixon-Coles model (attack/defence, home advantage,
  `rho`, time decay) on a JSON list of historical results; prints team strengths,
  optionally writes params with `--out`.
- `paper --slate <file.json>` — run a slate of fixtures and list all proposed bets.
- `report --bets <file.json>` — resolve a bets file into realized P&L + CLV stats.
- `backfill` — Supabase ingestion (requires `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`).

See `examples/` for sample `results`, `slate`, and `bets` JSON files.

## How it works

1. **Strength prior** (`model/ratings_prior.py`): Elo ratings (bundled men's
   national-team seed in `data/seed/international_elo.json`, recalibratable via Elo
   updates) anchor sparse international teams.
2. **Goal expectations** (`model/dixon_coles.py::lambdas_from_elo`): Elo supremacy →
   `(lambda_home, lambda_away)` around a configurable baseline total (`BASE_GOALS`).
3. **Scoreline matrix** (`scoreline_matrix`): product Poisson with the Dixon-Coles
   `tau` low-score correction → `marginal_hda` for H/D/A.
4. **De-vig** (`edge/devig.py`): market odds → fair consensus probabilities (Shin default).
5. **Edge + gate** (`edge/gate.py`): bet only when `model_p − consensus > EDGE_THRESHOLD`.
6. **Stakes** (`edge/kelly.py`): fractional Kelly on the price actually paid, capped per match.
7. **Accounting** (`accounting/`): P&L resolution + CLV — the north-star validation metric.

`fit` provides the full Dixon-Coles MLE path for data-rich leagues; the Elo prior path
is the default for sparse international fixtures (e.g. World Cup matches).

> The bundled Elo seed and goal-mapping defaults are illustrative; recalibrate against
> real results (and validate positive CLV) before risking live capital. `DRY_RUN=true`
> by default — no path places a real order until `DRY_RUN=false` after CLV validation.

## Dev

- Lint: `uv run ruff check . && uv run ruff format --check .`
- Type: `uv run mypy src`
- Test: `uv run pytest -q`
- All must pass before commit. pre-commit configured.

Built with ❤️ for truth-seeking in sports markets. Beat the close.