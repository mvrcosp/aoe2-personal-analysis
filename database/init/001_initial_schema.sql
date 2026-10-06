BEGIN;

CREATE TABLE IF NOT EXISTS players (
    profile_id BIGINT PRIMARY KEY,
    current_name TEXT,
    current_alias TEXT,
    country CHAR(2),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS matches (
    match_id BIGINT PRIMARY KEY,
    guid UUID,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    replay_timestamp TIMESTAMP WITHOUT TIME ZONE,
    duration_microseconds BIGINT
        CHECK (duration_microseconds IS NULL OR duration_microseconds >= 0),
    map_id INTEGER,
    map_name TEXT,
    map_size TEXT,
    match_type_id INTEGER,
    match_type TEXT,
    game_mode_id INTEGER,
    dataset_id INTEGER,
    dataset TEXT,
    game_version TEXT,
    replay_hash TEXT,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE IF NOT EXISTS match_participants (
    participant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    profile_id BIGINT REFERENCES players(profile_id) ON DELETE RESTRICT,
    player_number SMALLINT,
    observed_name TEXT,
    civilization_id INTEGER,
    civilization TEXT,
    team_id INTEGER,
    result_type SMALLINT,
    outcome SMALLINT CHECK (outcome IS NULL OR outcome IN (0, 1)),
    won BOOLEAN,
    eapm INTEGER CHECK (eapm IS NULL OR eapm >= 0),
    rating_snapshot INTEGER,
    UNIQUE (match_id, profile_id),
    UNIQUE (match_id, player_number)
);

CREATE TABLE IF NOT EXISTS match_ratings (
    match_id BIGINT NOT NULL,
    profile_id BIGINT NOT NULL,
    report_type SMALLINT NOT NULL,
    statgroup_id BIGINT,
    old_rating NUMERIC(8, 2),
    new_rating NUMERIC(8, 2),
    wins INTEGER CHECK (wins IS NULL OR wins >= 0),
    losses INTEGER CHECK (losses IS NULL OR losses >= 0),
    streak INTEGER,
    arbitration SMALLINT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, profile_id, report_type),
    FOREIGN KEY (match_id, profile_id)
        REFERENCES match_participants(match_id, profile_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS replay_assets (
    replay_asset_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    profile_id BIGINT REFERENCES players(profile_id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    source_url TEXT,
    file_format TEXT NOT NULL,
    availability_status TEXT NOT NULL DEFAULT 'discovered'
        CHECK (availability_status IN (
            'discovered', 'available', 'downloaded', 'extracted',
            'processed', 'unavailable', 'failed'
        )),
    storage_path TEXT,
    file_size_bytes BIGINT CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    sha256 CHAR(64),
    first_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    downloaded_at TIMESTAMPTZ,
    extracted_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-fA-F]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_replay_assets_match
    ON replay_assets(match_id);
CREATE INDEX IF NOT EXISTS idx_replay_assets_status
    ON replay_assets(availability_status);

CREATE TABLE IF NOT EXISTS replay_download_attempts (
    attempt_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    replay_asset_id BIGINT REFERENCES replay_assets(replay_asset_id) ON DELETE SET NULL,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    profile_id BIGINT REFERENCES players(profile_id) ON DELETE SET NULL,
    requested_url TEXT NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    http_status SMALLINT,
    succeeded BOOLEAN NOT NULL,
    error_message TEXT,
    response_headers JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_replay_attempts_match_date
    ON replay_download_attempts(match_id, attempted_at DESC);

CREATE TABLE IF NOT EXISTS match_actions (
    action_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
    player_number SMALLINT,
    elapsed_microseconds BIGINT NOT NULL CHECK (elapsed_microseconds >= 0),
    action_type TEXT NOT NULL,
    position_x NUMERIC(8, 2),
    position_y NUMERIC(8, 2),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (match_id, sequence_number),
    FOREIGN KEY (match_id, player_number)
        REFERENCES match_participants(match_id, player_number)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_actions_match_time
    ON match_actions(match_id, elapsed_microseconds);
CREATE INDEX IF NOT EXISTS idx_match_actions_player_time
    ON match_actions(match_id, player_number, elapsed_microseconds);
CREATE INDEX IF NOT EXISTS idx_match_actions_type
    ON match_actions(action_type);

CREATE TABLE IF NOT EXISTS match_inputs (
    input_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
    player_number SMALLINT,
    elapsed_microseconds BIGINT NOT NULL CHECK (elapsed_microseconds >= 0),
    input_type TEXT NOT NULL,
    position_x NUMERIC(8, 2),
    position_y NUMERIC(8, 2),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (match_id, sequence_number),
    FOREIGN KEY (match_id, player_number)
        REFERENCES match_participants(match_id, player_number)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_inputs_match_time
    ON match_inputs(match_id, elapsed_microseconds);
CREATE INDEX IF NOT EXISTS idx_match_inputs_type
    ON match_inputs(input_type);

CREATE TABLE IF NOT EXISTS match_player_snapshots (
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    profile_id BIGINT NOT NULL,
    elapsed_microseconds BIGINT NOT NULL CHECK (elapsed_microseconds >= 0),
    total_resources BIGINT CHECK (total_resources IS NULL OR total_resources >= 0),
    total_objects INTEGER CHECK (total_objects IS NULL OR total_objects >= 0),
    PRIMARY KEY (match_id, profile_id, elapsed_microseconds),
    FOREIGN KEY (match_id, profile_id)
        REFERENCES match_participants(match_id, profile_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_snapshots_profile_time
    ON match_player_snapshots(profile_id, match_id, elapsed_microseconds);

CREATE TABLE IF NOT EXISTS match_objects (
    match_object_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    owner_player_number SMALLINT,
    instance_id BIGINT,
    object_index INTEGER,
    class_id INTEGER,
    object_id INTEGER,
    object_name TEXT,
    position_x NUMERIC(8, 2),
    position_y NUMERIC(8, 2),
    is_gaia BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (NOT is_gaia OR owner_player_number IS NULL),
    FOREIGN KEY (match_id, owner_player_number)
        REFERENCES match_participants(match_id, player_number)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_objects_match_owner
    ON match_objects(match_id, owner_player_number);
CREATE INDEX IF NOT EXISTS idx_match_objects_match_instance
    ON match_objects(match_id, instance_id);

CREATE TABLE IF NOT EXISTS match_chat (
    chat_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL CHECK (sequence_number >= 0),
    player_number SMALLINT,
    elapsed_microseconds BIGINT NOT NULL CHECK (elapsed_microseconds >= 0),
    message TEXT NOT NULL,
    origination TEXT,
    audience TEXT,
    UNIQUE (match_id, sequence_number),
    FOREIGN KEY (match_id, player_number)
        REFERENCES match_participants(match_id, player_number)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_chat_match_time
    ON match_chat(match_id, elapsed_microseconds);

CREATE TABLE IF NOT EXISTS match_age_ups (
    match_id BIGINT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    profile_id BIGINT NOT NULL,
    age TEXT NOT NULL,
    elapsed_microseconds BIGINT NOT NULL CHECK (elapsed_microseconds >= 0),
    PRIMARY KEY (match_id, profile_id, age),
    FOREIGN KEY (match_id, profile_id)
        REFERENCES match_participants(match_id, profile_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    ingestion_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    profile_id BIGINT REFERENCES players(profile_id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'completed_with_errors', 'failed')),
    matches_found INTEGER CHECK (matches_found IS NULL OR matches_found >= 0),
    error_summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE IF NOT EXISTS source_artifacts (
    source_artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_run_id BIGINT REFERENCES ingestion_runs(ingestion_run_id) ON DELETE SET NULL,
    match_id BIGINT REFERENCES matches(match_id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    file_path TEXT,
    sha256 CHAR(64),
    payload JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-fA-F]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_source_artifacts_match
    ON source_artifacts(match_id, collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_run
    ON source_artifacts(ingestion_run_id);

COMMIT;
