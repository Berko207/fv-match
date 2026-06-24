"""Typer CLI for fv-match.

The headline command is ``analyze`` — an end-to-end fair-value report for a
single fixture that runs fully offline (Elo prior → Dixon-Coles → de-vig → edge
→ Kelly). ``live`` polls ESPN for match state and Polymarket for odds, then
runs the in-play model on a refresh loop. ``fit`` calibrates a Dixon-Coles model
on a results file, ``paper`` runs a slate of fixtures, and ``report`` summarizes
P&L + CLV from a bets file.
All paths respect the ``DRY_RUN`` guardrail.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fvmatch.config import settings
from fvmatch.engine import MatchAnalysis, analyze_live_match, analyze_match
from fvmatch.model.live import LiveState

if TYPE_CHECKING:
    from fvmatch.data.live_feed import LiveMatch

app = typer.Typer(
    name="fvmatch",
    help="fv-match: football fair-value engine. DRY_RUN=true by default.",
    add_completion=False,
)
console = Console()


def _fmt_pct(x: float | None) -> str:
    return "-" if x is None else f"{x * 100:5.1f}%"


def _fmt_odds(x: float | None) -> str:
    return "-" if x is None else f"{x:6.2f}"


def render_analysis(analysis: MatchAnalysis) -> None:
    """Pretty-print a :class:`MatchAnalysis` to the console."""
    venue = "neutral" if analysis.neutral else "home advantage"
    header = (
        f"[bold]{analysis.home}[/bold]  vs  [bold]{analysis.away}[/bold]\n"
        f"Elo {analysis.elo_home:.0f} – {analysis.elo_away:.0f}  ·  venue: {venue}\n"
        f"Model xG  {analysis.expected_home_goals:.2f} – "
        f"{analysis.expected_away_goals:.2f}"
    )
    if analysis.live_state is not None:
        ls = analysis.live_state
        header += (
            f"\n[bold cyan]LIVE[/bold cyan]  {ls.minute:.0f}'  "
            f"score {ls.home_goals}-{ls.away_goals}"
        )
        if ls.red_cards_home or ls.red_cards_away:
            header += f"  ·  reds {ls.red_cards_home}-{ls.red_cards_away}"
    console.print(Panel(header, title="fv-match", expand=False))

    table = Table(title="Model vs Market", show_lines=False)
    table.add_column("Outcome", style="bold")
    table.add_column("Model P", justify="right")
    table.add_column("Fair odds", justify="right")
    table.add_column("Mkt odds", justify="right")
    table.add_column("Consensus", justify="right")
    table.add_column("Edge", justify="right")
    table.add_column("EV/$", justify="right")
    table.add_column("Stake", justify="right")

    labels = {
        "home": analysis.home,
        "draw": "Draw",
        "away": analysis.away,
    }
    for ov in analysis.outcomes:
        edge_str = _fmt_pct(ov.edge)
        if ov.edge is not None:
            color = "green" if ov.edge > 0 else "red"
            edge_str = f"[{color}]{edge_str}[/{color}]"
        stake_str = "-"
        if ov.bet:
            stake_str = f"[green]${ov.stake_usd:,.2f}[/green]"
        table.add_row(
            labels[ov.outcome],
            _fmt_pct(ov.model_p),
            _fmt_odds(ov.fair_odds),
            _fmt_odds(ov.market_odds),
            _fmt_pct(ov.consensus_p),
            edge_str,
            "-" if ov.ev_per_dollar is None else f"{ov.ev_per_dollar:+.2%}",
            stake_str,
        )
    console.print(table)

    if analysis.overround is not None:
        console.print(
            f"Market overround: [yellow]{analysis.overround * 100:.2f}%[/yellow]"
        )

    score_tbl = Table(title="Most likely scorelines", show_header=True)
    score_tbl.add_column("Score")
    score_tbl.add_column("Prob", justify="right")
    for i, j, p in analysis.top_scorelines:
        score_tbl.add_row(f"{i}-{j}", _fmt_pct(p))
    console.print(score_tbl)

    if analysis.has_bets:
        total = sum(o.stake_usd for o in analysis.outcomes)
        mode = "DRY_RUN (no orders placed)" if analysis.dry_run else "LIVE"
        console.print(
            Panel(
                f"Recommended total stake: [bold]${total:,.2f}[/bold]  "
                f"(bankroll ${settings.bankroll:,.0f})\nMode: [bold]{mode}[/bold]",
                title="Proposed bets",
                border_style="green" if analysis.dry_run else "red",
                expand=False,
            )
        )
    else:
        console.print("[dim]No outcome clears the edge gate — no bet.[/dim]")


def _live_status_line(snapshot: LiveMatch) -> str:
    if snapshot.is_final:
        return f"FT {snapshot.home_goals}-{snapshot.away_goals}"
    if snapshot.is_pre:
        return "pre-match"
    detail = snapshot.status_detail or f"{snapshot.minute:.0f}'"
    return f"{snapshot.minute:.0f}' {snapshot.home_goals}-{snapshot.away_goals} ({detail})"


def _live_cycle(
    *,
    home: str,
    away: str,
    poly_slug: str,
    league: str,
    home_field: bool,
    elo_home: float | None,
    elo_away: float | None,
) -> tuple[MatchAnalysis, LiveMatch] | None:
    """One ESPN + Polymarket + in-play engine cycle."""
    from fvmatch.data.live_feed import find_live_match
    from fvmatch.data.polymarket import fetch_match_odds

    snapshot = find_live_match(home, away, league=league)
    if snapshot is None:
        return None

    state = snapshot.to_live_state()
    home_odds = draw_odds = away_odds = None
    match_odds = fetch_match_odds(poly_slug, home, away)
    if match_odds:
        home_odds = match_odds.home_odds
        draw_odds = match_odds.draw_odds
        away_odds = match_odds.away_odds

    analysis = analyze_live_match(
        home=home,
        away=away,
        state=state,
        home_odds=home_odds,
        draw_odds=draw_odds,
        away_odds=away_odds,
        neutral=not home_field,
        elo_home=elo_home,
        elo_away=elo_away,
    )
    return analysis, snapshot


def _analysis_json_payload(analysis: MatchAnalysis) -> dict[str, object]:
    payload: dict[str, object] = {
        "home": analysis.home,
        "away": analysis.away,
        "neutral": analysis.neutral,
        "elo": {"home": analysis.elo_home, "away": analysis.elo_away},
        "expected_goals": {
            "home": analysis.expected_home_goals,
            "away": analysis.expected_away_goals,
        },
        "model_probs": {
            "home": analysis.p_home,
            "draw": analysis.p_draw,
            "away": analysis.p_away,
        },
        "overround": analysis.overround,
        "outcomes": [
            {
                "outcome": o.outcome,
                "model_p": o.model_p,
                "fair_odds": o.fair_odds,
                "market_odds": o.market_odds,
                "consensus_p": o.consensus_p,
                "edge": o.edge,
                "ev_per_dollar": o.ev_per_dollar,
                "stake_usd": o.stake_usd,
                "bet": o.bet,
            }
            for o in analysis.outcomes
        ],
        "top_scorelines": [
            {"home": i, "away": j, "p": p} for i, j, p in analysis.top_scorelines
        ],
        "dry_run": analysis.dry_run,
    }
    if analysis.live_state is not None:
        ls = analysis.live_state
        payload["live"] = {
            "minute": ls.minute,
            "home_goals": ls.home_goals,
            "away_goals": ls.away_goals,
            "red_cards_home": ls.red_cards_home,
            "red_cards_away": ls.red_cards_away,
        }
    return payload


@app.command()
def analyze(
    home: str = typer.Option(..., help="Home (or first) team name"),
    away: str = typer.Option(..., help="Away (or second) team name"),
    home_odds: float | None = typer.Option(None, help="Decimal odds for home win"),
    draw_odds: float | None = typer.Option(None, help="Decimal odds for draw"),
    away_odds: float | None = typer.Option(None, help="Decimal odds for away win"),
    poly_slug: str | None = typer.Option(
        None, help="Polymarket Gamma market slug to fetch live 3-way odds"
    ),
    home_field: bool = typer.Option(
        False, "--home-field", help="Apply home advantage (default: neutral venue)"
    ),
    elo_home: float | None = typer.Option(None, help="Override home Elo rating"),
    elo_away: float | None = typer.Option(None, help="Override away Elo rating"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Fair-value analysis for one fixture: model probs vs market edge + stakes."""
    if poly_slug and not (home_odds and draw_odds and away_odds):
        from fvmatch.data.polymarket import fetch_three_way_odds

        odds = fetch_three_way_odds(poly_slug)
        if odds:
            home_odds, draw_odds, away_odds = (
                odds["home"],
                odds["draw"],
                odds["away"],
            )
            console.print(
                f"[dim]Fetched live odds from Polymarket slug {poly_slug}[/dim]"
            )
        else:
            console.print(
                "[yellow]Could not fetch/parse Polymarket odds; "
                "continuing model-only.[/yellow]"
            )

    analysis = analyze_match(
        home=home,
        away=away,
        home_odds=home_odds,
        draw_odds=draw_odds,
        away_odds=away_odds,
        neutral=not home_field,
        elo_home=elo_home,
        elo_away=elo_away,
    )

    if json_out:
        payload = {
            "home": analysis.home,
            "away": analysis.away,
            "neutral": analysis.neutral,
            "elo": {"home": analysis.elo_home, "away": analysis.elo_away},
            "expected_goals": {
                "home": analysis.expected_home_goals,
                "away": analysis.expected_away_goals,
            },
            "model_probs": {
                "home": analysis.p_home,
                "draw": analysis.p_draw,
                "away": analysis.p_away,
            },
            "overround": analysis.overround,
            "outcomes": [
                {
                    "outcome": o.outcome,
                    "model_p": o.model_p,
                    "fair_odds": o.fair_odds,
                    "market_odds": o.market_odds,
                    "consensus_p": o.consensus_p,
                    "edge": o.edge,
                    "ev_per_dollar": o.ev_per_dollar,
                    "stake_usd": o.stake_usd,
                    "bet": o.bet,
                }
                for o in analysis.outcomes
            ],
            "top_scorelines": [
                {"home": i, "away": j, "p": p} for i, j, p in analysis.top_scorelines
            ],
            "dry_run": analysis.dry_run,
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        render_analysis(analysis)


@app.command("analyze-live")
def analyze_live(
    home: str = typer.Option(..., help="Home (or first) team name"),
    away: str = typer.Option(..., help="Away (or second) team name"),
    minute: float = typer.Option(..., help="Elapsed match minutes (0–90+)"),
    home_goals: int = typer.Option(0, "--home-goals", help="Home goals scored"),
    away_goals: int = typer.Option(0, "--away-goals", help="Away goals scored"),
    red_home: int = typer.Option(0, "--red-home", help="Red cards for home team"),
    red_away: int = typer.Option(0, "--red-away", help="Red cards for away team"),
    home_odds: float | None = typer.Option(None, help="Decimal odds for home win"),
    draw_odds: float | None = typer.Option(None, help="Decimal odds for draw"),
    away_odds: float | None = typer.Option(None, help="Decimal odds for away win"),
    home_field: bool = typer.Option(
        False, "--home-field", help="Apply home advantage (default: neutral venue)"
    ),
    elo_home: float | None = typer.Option(None, help="Override home Elo rating"),
    elo_away: float | None = typer.Option(None, help="Override away Elo rating"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """In-play fair-value analysis: conditional model probs vs market edge + stakes."""
    state = LiveState(
        minute=minute,
        home_goals=home_goals,
        away_goals=away_goals,
        red_cards_home=red_home,
        red_cards_away=red_away,
    )
    analysis = analyze_live_match(
        home=home,
        away=away,
        state=state,
        home_odds=home_odds,
        draw_odds=draw_odds,
        away_odds=away_odds,
        neutral=not home_field,
        elo_home=elo_home,
        elo_away=elo_away,
    )

    if json_out:
        payload = {
            "home": analysis.home,
            "away": analysis.away,
            "neutral": analysis.neutral,
            "live": {
                "minute": state.minute,
                "home_goals": state.home_goals,
                "away_goals": state.away_goals,
                "red_cards_home": state.red_cards_home,
                "red_cards_away": state.red_cards_away,
            },
            "elo": {"home": analysis.elo_home, "away": analysis.elo_away},
            "expected_goals": {
                "home": analysis.expected_home_goals,
                "away": analysis.expected_away_goals,
            },
            "model_probs": {
                "home": analysis.p_home,
                "draw": analysis.p_draw,
                "away": analysis.p_away,
            },
            "overround": analysis.overround,
            "outcomes": [
                {
                    "outcome": o.outcome,
                    "model_p": o.model_p,
                    "fair_odds": o.fair_odds,
                    "market_odds": o.market_odds,
                    "consensus_p": o.consensus_p,
                    "edge": o.edge,
                    "ev_per_dollar": o.ev_per_dollar,
                    "stake_usd": o.stake_usd,
                    "bet": o.bet,
                }
                for o in analysis.outcomes
            ],
            "top_scorelines": [
                {"home": i, "away": j, "p": p} for i, j, p in analysis.top_scorelines
            ],
            "dry_run": analysis.dry_run,
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        render_analysis(analysis)


@app.command()
def live(
    home: str = typer.Option(..., help="Home (or first) team name"),
    away: str = typer.Option(..., help="Away (or second) team name"),
    poly_slug: str = typer.Option(
        ..., help="Polymarket Gamma event slug for live H/D/A odds"
    ),
    interval: int = typer.Option(
        30, "--interval", "-i", min=5, help="Seconds between ESPN/Polymarket polls"
    ),
    once: bool = typer.Option(False, "--once", help="Run one cycle and exit"),
    league: str = typer.Option(
        "fifa.world", "--league", help="ESPN scoreboard league slug"
    ),
    home_field: bool = typer.Option(
        False, "--home-field", help="Apply home advantage (default: neutral venue)"
    ),
    elo_home: float | None = typer.Option(None, help="Override home Elo rating"),
    elo_away: float | None = typer.Option(None, help="Override away Elo rating"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Poll ESPN + Polymarket and run in-play fair-value analysis on a loop."""
    try:
        while True:
            ts = datetime.now().strftime("%H:%M:%S")
            result = _live_cycle(
                home=home,
                away=away,
                poly_slug=poly_slug,
                league=league,
                home_field=home_field,
                elo_home=elo_home,
                elo_away=elo_away,
            )
            if result is None:
                if once:
                    console.print(
                        f"[yellow]{ts} ESPN: fixture not on scoreboard[/yellow]"
                    )
                    raise typer.Exit(code=1)
                console.print(
                    f"[yellow]{ts} ESPN: fixture not on scoreboard — "
                    f"retrying in {interval}s…[/yellow]"
                )
                time.sleep(interval)
                continue

            analysis, snapshot = result
            if not json_out and not once:
                console.clear()
            status = _live_status_line(snapshot)
            console.print(
                f"[dim]Updated {ts}  ·  ESPN {status}  ·  slug {poly_slug}[/dim]"
            )
            if analysis.overround is None:
                console.print(
                    "[yellow]Polymarket odds unavailable — model-only.[/yellow]"
                )
            if json_out:
                typer.echo(json.dumps(_analysis_json_payload(analysis), indent=2))
            else:
                render_analysis(analysis)

            if snapshot.is_final:
                console.print("[dim]Match finished — stopping.[/dim]")
                break
            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")
        raise typer.Exit(code=0) from None


@app.command()
def backfill(
    competition: str = typer.Option(..., help="Competition slug or external id"),
    season: str = typer.Option(..., help="Season e.g. 2024-2025 or 2026"),
    limit: int = typer.Option(1000, help="Max fixtures to backfill"),
) -> None:
    """Ingest historical fixtures + results + ratings (requires Supabase)."""
    if not settings.has_supabase:
        console.print(
            "[yellow]No Supabase configured. Backfill needs SUPABASE_URL/"
            "SUPABASE_SERVICE_KEY. For offline modeling use `fit --results <file>`."
            "[/yellow]"
        )
        raise typer.Exit(code=1)
    console.print(
        f"[dim]Would backfill {competition} {season} (limit={limit}) into Supabase.[/dim]"
    )


@app.command()
def fit(
    results: Path = typer.Option(
        ...,
        exists=True,
        help="JSON file: list of {home_team, away_team, home_goals, away_goals, kickoff_utc?}",
    ),
    out: Path | None = typer.Option(None, help="Write fitted params to this JSON file"),
) -> None:
    """Fit a Dixon-Coles model on a results file and report the parameters."""
    from fvmatch.model.dixon_coles import fit as dc_fit

    fixtures = json.loads(results.read_text(encoding="utf-8"))
    params = dc_fit(fixtures, decay_lambda=settings.dc_decay, rho=settings.dc_rho)

    console.print(
        Panel(
            f"Fitted Dixon-Coles on [bold]{params['n_fixtures']}[/bold] fixtures, "
            f"{len(params['teams'])} teams\n"
            f"converged={params['converged']}  "
            f"home-adv γ={params['gamma']:.3f}  ρ={params['rho']:.3f}  "
            f"μ={params['mu']:.3f}",
            title="fit",
            expand=False,
        )
    )
    ranked = sorted(
        params["teams"],
        key=lambda t: params["attack"][t] - params["defence"][t],
        reverse=True,
    )
    tbl = Table(title="Team strength (attack − defence)")
    tbl.add_column("Team")
    tbl.add_column("Attack", justify="right")
    tbl.add_column("Defence", justify="right")
    for t in ranked[:15]:
        tbl.add_row(t, f"{params['attack'][t]:+.3f}", f"{params['defence'][t]:+.3f}")
    console.print(tbl)

    if out:
        out.write_text(json.dumps(params, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote params to {out}[/green]")


@app.command()
def paper(
    slate: Path = typer.Option(
        ...,
        exists=True,
        help="JSON file: list of {home, away, home_odds?, draw_odds?, away_odds?, neutral?}",
    ),
) -> None:
    """Run a paper-trading slate: analyze each fixture, list proposed bets."""
    fixtures = json.loads(slate.read_text(encoding="utf-8"))
    total_stake = 0.0
    n_bets = 0
    for fx in fixtures:
        analysis = analyze_match(
            home=fx["home"],
            away=fx["away"],
            home_odds=fx.get("home_odds"),
            draw_odds=fx.get("draw_odds"),
            away_odds=fx.get("away_odds"),
            neutral=fx.get("neutral", True),
        )
        render_analysis(analysis)
        for o in analysis.outcomes:
            if o.bet:
                total_stake += o.stake_usd
                n_bets += 1
        console.print()

    mode = "DRY_RUN" if settings.dry_run else "LIVE"
    console.print(
        Panel(
            f"Slate complete: {len(fixtures)} fixtures, {n_bets} proposed bets, "
            f"total stake ${total_stake:,.2f} · mode {mode}",
            title="paper",
            expand=False,
        )
    )


@app.command()
def report(
    bets: Path = typer.Option(
        ...,
        exists=True,
        help="JSON file: list of bets with entry_price, close_price?, stake, outcome, fixture_result?",
    ),
) -> None:
    """Summarize realized P&L + CLV from a bets file (offline accounting)."""
    from fvmatch.accounting.resolve import batch_resolve
    from fvmatch.model.calibration import clv_vs_market_edge

    rows = json.loads(bets.read_text(encoding="utf-8"))
    resolved = batch_resolve(rows)
    realized = sum(
        float(b.get("realized_pnl", 0.0) or 0.0)
        for b in rows
        if b.get("status") == "resolved"
    )
    clv_stats = clv_vs_market_edge(rows)

    console.print(
        Panel(
            f"Bets: {len(rows)}  ·  resolved: {resolved}\n"
            f"Realized P&L: [bold]${realized:,.2f}[/bold]\n"
            f"Mean CLV: {clv_stats['mean_clv_pct'] * 100:.2f}%  ·  "
            f"beat-close rate: {clv_stats['beat_close_rate'] * 100:.1f}%  "
            f"(n={int(clv_stats['n'])})",
            title="report",
            expand=False,
        )
    )


if __name__ == "__main__":
    app()
