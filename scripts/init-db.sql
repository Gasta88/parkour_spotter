-- Database initialization script for Parkour Spotter
-- This script is mounted into the PostGIS container via docker-compose.yml
-- and executed on first startup via /docker-entrypoint-initdb.d/
-- Idempotent: safe to run multiple times using IF NOT EXISTS clauses

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS h3;

-- ============================================================================
-- TABLE: data_version
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_version (
    id SERIAL PRIMARY KEY,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    osm_source_url VARCHAR NOT NULL,
    osm_file_hash VARCHAR NOT NULL,
    file_size_mb FLOAT NOT NULL,
    row_counts JSONB NOT NULL,
    load_duration_seconds INT,
    success BOOL NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_data_version_loaded_at ON data_version(loaded_at);
CREATE INDEX IF NOT EXISTS ix_data_version_osm_file_hash ON data_version(osm_file_hash);

-- ============================================================================
-- TABLE: spots_annotated
-- ============================================================================

CREATE TABLE IF NOT EXISTS spots_annotated (
    id SERIAL PRIMARY KEY,
    h3_index VARCHAR(16) NOT NULL,
    rating INT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    human_score FLOAT,
    features JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_spots_annotated_rating_range CHECK (rating >= 0 AND rating <= 5),
    CONSTRAINT uq_spots_annotated_h3_index UNIQUE (h3_index)
);

CREATE INDEX IF NOT EXISTS ix_spots_annotated_h3_index ON spots_annotated(h3_index);

-- ============================================================================
-- TABLE: saved_search
-- ============================================================================

CREATE TABLE IF NOT EXISTS saved_search (
    id UUID PRIMARY KEY,
    lat FLOAT NOT NULL,
    lon FLOAT NOT NULL,
    radius_m FLOAT NOT NULL,
    cell_count INT NOT NULL,
    score_distribution JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_saved_search_cache_lookup ON saved_search(lat, lon, radius_m);
CREATE INDEX IF NOT EXISTS ix_saved_search_created_at ON saved_search(created_at);

-- ============================================================================
-- TABLE: cell_feature
-- ============================================================================

CREATE TABLE IF NOT EXISTS cell_feature (
    id SERIAL PRIMARY KEY,
    h3_index VARCHAR(16) NOT NULL,
    osm_file_hash VARCHAR NOT NULL,
    walls_count INT NOT NULL DEFAULT 0,
    walls_total_length_m FLOAT NOT NULL DEFAULT 0.0,
    rails_count INT NOT NULL DEFAULT 0,
    rails_total_length_m FLOAT NOT NULL DEFAULT 0.0,
    gaps_count INT NOT NULL DEFAULT 0,
    gaps_total_length_m FLOAT NOT NULL DEFAULT 0.0,
    stairs_count INT NOT NULL DEFAULT 0,
    stairs_total_length_m FLOAT NOT NULL DEFAULT 0.0,
    vaults_count INT NOT NULL DEFAULT 0,
    vaults_total_area_m2 FLOAT NOT NULL DEFAULT 0.0,
    open_spaces_count INT NOT NULL DEFAULT 0,
    open_spaces_total_area_m2 FLOAT NOT NULL DEFAULT 0.0,
    h3_res8_parent VARCHAR(15) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_cell_feature_h3_osm UNIQUE (h3_index, osm_file_hash)
);

CREATE INDEX IF NOT EXISTS ix_cell_feature_h3_index ON cell_feature(h3_index);
CREATE INDEX IF NOT EXISTS ix_cell_feature_osm_file_hash ON cell_feature(osm_file_hash);
CREATE INDEX IF NOT EXISTS ix_cell_feature_res8_parent ON cell_feature(h3_res8_parent);

-- ============================================================================
-- TABLE: model
-- ============================================================================

CREATE TABLE IF NOT EXISTS model (
    id UUID PRIMARY KEY,
    model_type VARCHAR NOT NULL,
    version INT NOT NULL,
    name VARCHAR NOT NULL,
    feature_list VARCHAR[],
    hyperparameters JSONB,
    is_active BOOL NOT NULL DEFAULT FALSE,
    status VARCHAR NOT NULL DEFAULT 'pending',
    artifact_path TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_model_name_version UNIQUE (name, version)
);

CREATE INDEX IF NOT EXISTS ix_model_model_type ON model(model_type);
CREATE INDEX IF NOT EXISTS ix_model_name ON model(name);
CREATE INDEX IF NOT EXISTS ix_model_is_active ON model(is_active);

-- ============================================================================
-- TABLE: model_evaluation
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_evaluation (
    id UUID PRIMARY KEY,
    model_id UUID NOT NULL,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    confusion_matrix JSONB,
    feature_importance JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_model_evaluation_model_id FOREIGN KEY (model_id) REFERENCES model(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_model_evaluation_model_id ON model_evaluation(model_id);

-- ============================================================================
-- TABLE: training_run
-- ============================================================================

CREATE TABLE IF NOT EXISTS training_run (
    id UUID PRIMARY KEY,
    model_id UUID NOT NULL,
    evaluation_id UUID,
    train_test_split JSONB,
    status VARCHAR NOT NULL DEFAULT 'running',
    error_message TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_training_run_model_id FOREIGN KEY (model_id) REFERENCES model(id) ON DELETE CASCADE,
    CONSTRAINT fk_training_run_evaluation_id FOREIGN KEY (evaluation_id) REFERENCES model_evaluation(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_training_run_model_id ON training_run(model_id);
CREATE INDEX IF NOT EXISTS ix_training_run_evaluation_id ON training_run(evaluation_id);
CREATE INDEX IF NOT EXISTS ix_training_run_status ON training_run(status);
