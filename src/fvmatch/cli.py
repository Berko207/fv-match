"""Typer CLI for fv-match. Commands are stubs in Phase 0."""

from __future__ import annotations

import typer

from fvmatch.config import settings

app = typer.Typer(
    name="fvmatch",
    help="fv-match: football fair-value engine. DRY_RUN=true by default.",
    add_completion=False,
)


@app.command()
def backfill(
    competition: str = typer.Option(..., help="Competition slug or external id"),
    season: str = typer.Option(..., help="Season e.g. 2024-2025 or 2026"),
    limit: int = typer.Option(1000, help="Max fixtures to backfill"),
) -> None:
    """Ingest historical fixtures + results + ratings for a competition/season.

    Phase 0: STUB. Will call data.fixtures, data.results, data.ratings.
    """
    if settings.dry_run:
        typer.echo(f"[DRY_RUN] Would backfill {competition} {season} (limit={limit})")
    else:
        raise NotImplementedError("backfill not implemented in Phase 0")


@app.command()
def fit(
    competition: str = typer.Option(..., help="Competition to fit model on"),
    model_version: str | None = typer.Option(None, help="Override MODEL_VERSION"),
) -> None:
    """Fit Dixon-Coles model (or latest) on historical data for competition.

    Stores model_probs + scoreline_matrix in Supabase.
    Phase 0: STUB.
    """
    version = model_version or settings.model_version
    if settings.dry_run:
        typer.echo(f"[DRY_RUN] Would fit model {version} for {competition}")
    else:
        raise NotImplementedError("fit not implemented in Phase 0")


@app.command()
def paper(
    competition: str = typer.Option(..., help="Competition slug for paper trading"),
    hours_ahead: int = typer.Option(48, help="Lookahead window for upcoming fixtures"),
) -> None:
    """Run paper-trading cycle: fetch live markets, compute edges, log proposed bets.

    Respects DRY_RUN (always in Phase 0). Uses edge.gate + kelly.
    Phase 0: STUB.
    """
    if settings.dry_run:
        typer.echo(
            f"[DRY_RUN] Would run paper cycle for {competition} (+{hours_ahead}h)"
        )
    else:
        raise NotImplementedError("paper not implemented in Phase 0")


@app.command()
def report(
    days: int = typer.Option(30, help="Lookback days for P&L + CLV report"),
    output: str | None = typer.Option(None, help="Path to write JSON/CSV report"),
) -> None:
    """Generate accounting report: realized P&L, CLV stats, edge calibration.

    Phase 0: STUB. Will use accounting.resolve + clv.
    """
    if settings.dry_run:
        typer.echo(f"[DRY_RUN] Would generate {days}d report")
    else:
        raise NotImplementedError("report not implemented in Phase 0")


if __name__ == "__main__":
    app()
