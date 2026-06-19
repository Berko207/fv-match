-- fv-match initial schema (competition-agnostic)
-- Run with: psql $SUPABASE_URL -f 0001_init.sql or via Supabase dashboard/migrations

-- Enable uuid if needed (Supabase usually has)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- competitions
CREATE TABLE IF NOT EXISTS competitions (
    id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        text NOT NULL,
    kind        text NOT NULL CHECK (kind IN ('league', 'international', 'cup')),
    country     text,
    external_ids jsonb DEFAULT '{}'::jsonb,
    created_at  timestamptz DEFAULT now()
);

-- teams
CREATE TABLE IF NOT EXISTS teams (
    id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           text NOT NULL,
    competition_id uuid REFERENCES competitions(id) ON DELETE CASCADE,
    external_ids   jsonb DEFAULT '{}'::jsonb,
    created_at     timestamptz DEFAULT now()
);

-- fixtures
CREATE TABLE IF NOT EXISTS fixtures (
    id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id uuid REFERENCES competitions(id) ON DELETE CASCADE,
    season        text NOT NULL,
    home_team_id  uuid REFERENCES teams(id),
    away_team_id  uuid REFERENCES teams(id),
    kickoff_utc   timestamptz NOT NULL,
    status        text DEFAULT 'scheduled',  -- scheduled|live|finished|postponed|cancelled
    home_goals    int,
    away_goals    int,
    external_ids  jsonb DEFAULT '{}'::jsonb,
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fixtures_kickoff ON fixtures(kickoff_utc);
CREATE INDEX IF NOT EXISTS idx_fixtures_comp_season ON fixtures(competition_id, season);

-- team_ratings (Elo etc)
CREATE TABLE IF NOT EXISTS team_ratings (
    id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id    uuid REFERENCES teams(id) ON DELETE CASCADE,
    as_of      timestamptz NOT NULL,
    rating     numeric NOT NULL,
    source     text DEFAULT 'elo',
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_team_ratings_team_asof ON team_ratings(team_id, as_of DESC);

-- markets
CREATE TABLE IF NOT EXISTS markets (
    id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    fixture_id      uuid REFERENCES fixtures(id) ON DELETE CASCADE,
    platform        text NOT NULL,  -- polymarket|gamma|...
    market_type     text NOT NULL CHECK (market_type IN ('match_odds', 'correct_score', 'totals', 'dnb', 'other')),
    external_id     text,
    clob_token_ids  jsonb DEFAULT '{}'::jsonb,  -- for Polymarket CLOB
    created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_markets_fixture ON markets(fixture_id);

-- market_snapshots (time series prices)
CREATE TABLE IF NOT EXISTS market_snapshots (
    id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_id  uuid REFERENCES markets(id) ON DELETE CASCADE,
    ts         timestamptz NOT NULL DEFAULT now(),
    outcome    text NOT NULL,  -- 'home'|'draw'|'away' or score like '2-1'
    price      numeric NOT NULL CHECK (price > 0),
    source     text NOT NULL CHECK (source IN ('gamma', 'clob')),
    is_close   boolean DEFAULT false,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_market_ts ON market_snapshots(market_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_close ON market_snapshots(market_id, is_close) WHERE is_close;

-- model_probs
CREATE TABLE IF NOT EXISTS model_probs (
    id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    fixture_id     uuid REFERENCES fixtures(id) ON DELETE CASCADE,
    model_version  text NOT NULL,
    p_home         numeric NOT NULL CHECK (p_home BETWEEN 0 AND 1),
    p_draw         numeric NOT NULL CHECK (p_draw BETWEEN 0 AND 1),
    p_away         numeric NOT NULL CHECK (p_away BETWEEN 0 AND 1),
    scoreline_matrix jsonb,  -- full P(i,j) matrix
    created_at     timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_probs_fixture_version ON model_probs(fixture_id, model_version, created_at DESC);

-- bets (proposed + executed)
CREATE TABLE IF NOT EXISTS bets (
    id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_id      uuid REFERENCES markets(id),
    fixture_id     uuid REFERENCES fixtures(id) ON DELETE CASCADE,
    outcome        text NOT NULL,
    stake          numeric NOT NULL CHECK (stake >= 0),
    entry_price    numeric NOT NULL,
    model_p        numeric NOT NULL,
    edge           numeric,
    kelly_fraction numeric,
    status         text DEFAULT 'proposed',  -- proposed|placed|filled|cancelled|resolved
    dry_run        boolean DEFAULT true,
    realized_pnl   numeric,
    created_at     timestamptz DEFAULT now(),
    resolved_at    timestamptz
);

CREATE INDEX IF NOT EXISTS idx_bets_fixture ON bets(fixture_id);
CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);

-- clv
CREATE TABLE IF NOT EXISTS clv (
    id           uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    bet_id       uuid REFERENCES bets(id) ON DELETE CASCADE,
    close_price  numeric NOT NULL,
    clv_pct      numeric,
    computed_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clv_bet ON clv(bet_id);
