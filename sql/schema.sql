-- Raw facts only. Streaks are always computed, never stored (spec §5).
CREATE TABLE IF NOT EXISTS users (
    user_id                 text PRIMARY KEY,
    name                    text NOT NULL,
    signup_at               timestamptz NOT NULL,
    home_tz                 text NOT NULL,
    plan                    text NOT NULL,
    freeze_balance          integer NOT NULL,
    streak_as_of_2026_10_31 integer NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    video_id     text PRIMARY KEY,
    duration_s   integer NOT NULL,
    published_at timestamptz NOT NULL
);

-- Unique on event_id only: content duplicates are kept here and resolved in the engine,
-- so the result never depends on which copy reached the database first.
CREATE TABLE IF NOT EXISTS events (
    event_id    text PRIMARY KEY,
    user_id     text NOT NULL,
    event_type  text NOT NULL,
    video_id    text,
    watched_s   integer,
    client_ts   timestamptz NOT NULL,
    device_tz   text NOT NULL,
    received_at timestamptz NOT NULL,
    app_version text NOT NULL,
    meta        jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS events_user_id_idx ON events (user_id);

CREATE TABLE IF NOT EXISTS affected_uids (
    user_id text PRIMARY KEY
);
