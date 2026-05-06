#!/bin/bash
set -e

log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1"
}

cleanup() {
    rm -f "$PGPASSFILE" "$OSM_FILE"
}
trap cleanup EXIT

log "Starting OSM data loader..."

if [ -z "$DATABASE_URL" ]; then
    log "Error: DATABASE_URL not set"
    exit 1
fi

if [ -z "$OSM_URL" ]; then
    log "Error: OSM_URL not set"
    exit 1
fi

OSM_MIN_FILE_SIZE_MB=${OSM_MIN_FILE_SIZE_MB:-1}
REFRESH_INTERVAL_HOURS=${REFRESH_INTERVAL_HOURS:-24}
FORCE_RELOAD=${FORCE_RELOAD:-false}
OSM2PGSQL_CACHE_MB=${OSM2PGSQL_CACHE_MB:-512}
OSM2PGSQL_PROCESSES=${OSM2PGSQL_PROCESSES:-2}

OSM_FILE="/tmp/data.osm.pbf"

log "Downloading OSM data from $OSM_URL..."
if ! wget -O "$OSM_FILE" "$OSM_URL"; then
    log "Error: Failed to download OSM file from $OSM_URL"
    exit 1
fi

if [ ! -f "$OSM_FILE" ]; then
    log "Error: Downloaded file not found"
    exit 1
fi

FILE_SIZE_BYTES=$(stat -c%s "$OSM_FILE" 2>/dev/null || stat -f%z "$OSM_FILE" 2>/dev/null)
FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE_BYTES / 1048576" | bc)

log "Downloaded file size: ${FILE_SIZE_MB}MB"

if (( $(echo "$FILE_SIZE_MB < $OSM_MIN_FILE_SIZE_MB" | bc -l) )); then
    log "Error: File size ${FILE_SIZE_MB}MB is below minimum threshold ${OSM_MIN_FILE_SIZE_MB}MB"
    rm -f "$OSM_FILE"
    exit 1
fi

log "Computing SHA-256 hash..."
OSM_FILE_HASH=$(sha256sum "$OSM_FILE" | awk '{print $1}')
log "File hash: $OSM_FILE_HASH"

log "Extracting database connection details..."
DB_HOST=$(echo "$DATABASE_URL" | grep -oP '@\K[^:]+')
DB_PORT=$(echo "$DATABASE_URL" | grep -oP ':\K[0-9]+(?=/)')
DB_NAME=$(echo "$DATABASE_URL" | grep -oP '/\K[^?]+')
DB_USER=$(echo "$DATABASE_URL" | grep -oP '://\K[^:]+')
DB_PASSWORD=$(echo "$DATABASE_URL" | grep -oP '://[^:]+:\K[^@]+')

if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ] || [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    log "Error: Failed to parse DATABASE_URL"
    rm -f "$OSM_FILE"
    exit 1
fi

PGPASSFILE="/tmp/.pgpass"
echo "${DB_HOST}:${DB_PORT}:${DB_NAME}:${DB_USER}:${DB_PASSWORD}" > "$PGPASSFILE"
chmod 600 "$PGPASSFILE"
export PGPASSFILE

log "Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log "Error: PostgreSQL did not become ready after $MAX_RETRIES attempts"
        rm -f "$OSM_FILE"
        exit 1
    fi
    log "PostgreSQL is unavailable - sleeping (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

log "PostgreSQL is up"

log "Creating data_version table if not exists..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
CREATE TABLE IF NOT EXISTS data_version (
    id SERIAL PRIMARY KEY,
    loaded_at TIMESTAMPTZ DEFAULT NOW(),
    osm_source_url TEXT NOT NULL,
    osm_file_hash TEXT NOT NULL,
    file_size_mb REAL NOT NULL,
    row_counts JSONB NOT NULL,
    load_duration_seconds INTEGER,
    success BOOLEAN DEFAULT TRUE
);
EOF

if [ "$FORCE_RELOAD" != "true" ]; then
    log "Checking for recent load within ${REFRESH_INTERVAL_HOURS}h with matching hash..."
    RECENT_LOAD=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -v hash="$OSM_FILE_HASH" -v interval_hours="$REFRESH_INTERVAL_HOURS" <<EOF
SELECT COUNT(*) FROM data_version 
WHERE loaded_at > NOW() - INTERVAL ':interval_hours hours' 
AND osm_file_hash = ':hash'
AND success = TRUE;
EOF
)
    if [[ "$RECENT_LOAD" =~ ^[0-9]+$ ]] && [ "$RECENT_LOAD" -gt 0 ]; then
        log "Idempotency check passed: recent successful load with same file hash found. Skipping reload."
        rm -f "$OSM_FILE"
        exit 0
    fi
    log "No recent load found, proceeding with import"
else
    log "FORCE_RELOAD=true, bypassing idempotency check"
fi

log "TRUNCATING existing planet_osm_* tables for city-switching..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
TRUNCATE TABLE planet_osm_point CASCADE;
TRUNCATE TABLE planet_osm_line CASCADE;
TRUNCATE TABLE planet_osm_polygon CASCADE;
TRUNCATE TABLE planet_osm_roads CASCADE;
EOF

START_TIME=$(date +%s)

log "Running osm2pgsql with cache=${OSM2PGSQL_CACHE_MB}MB, processes=${OSM2PGSQL_PROCESSES}..."
if ! osm2pgsql \
    --database "$DB_NAME" \
    --host "$DB_HOST" \
    --port "$DB_PORT" \
    --username "$DB_USER" \
    --slim \
    --drop \
    --hstore-all \
    --number-processes "$OSM2PGSQL_PROCESSES" \
    --cache "$OSM2PGSQL_CACHE_MB" \
    "$OSM_FILE"; then
    log "Error: osm2pgsql failed"
    log "Rolling back: TRUNCATING planet_osm_* tables..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
TRUNCATE TABLE planet_osm_point CASCADE;
TRUNCATE TABLE planet_osm_line CASCADE;
TRUNCATE TABLE planet_osm_polygon CASCADE;
TRUNCATE TABLE planet_osm_roads CASCADE;
EOF
    rm -f "$OSM_FILE"
    exit 1
fi

END_TIME=$(date +%s)
LOAD_DURATION=$((END_TIME - START_TIME))

log "Validating load: counting rows in planet_osm_* tables..."
POINT_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT COUNT(*) FROM planet_osm_point;")
LINE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT COUNT(*) FROM planet_osm_line;")
POLYGON_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -A -c "SELECT COUNT(*) FROM planet_osm_polygon;")

log "Row counts: point=$POINT_COUNT, line=$LINE_COUNT, polygon=$POLYGON_COUNT"

if ! [[ "$POINT_COUNT" =~ ^[0-9]+$ ]] || ! [[ "$LINE_COUNT" =~ ^[0-9]+$ ]] || ! [[ "$POLYGON_COUNT" =~ ^[0-9]+$ ]]; then
    log "Error: Invalid row count values received"
    rm -f "$OSM_FILE"
    exit 1
fi

TOTAL_ROWS=$((POINT_COUNT + LINE_COUNT + POLYGON_COUNT))
if [ "$TOTAL_ROWS" -eq 0 ]; then
    log "Error: Load validation failed - all tables are empty"
    log "Rolling back: TRUNCATING planet_osm_* tables..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
TRUNCATE TABLE planet_osm_point CASCADE;
TRUNCATE TABLE planet_osm_line CASCADE;
TRUNCATE TABLE planet_osm_polygon CASCADE;
TRUNCATE TABLE planet_osm_roads CASCADE;
EOF
    rm -f "$OSM_FILE"
    exit 1
fi

log "Recording data version metadata..."
ROW_COUNTS_JSON="{\"point\":$POINT_COUNT,\"line\":$LINE_COUNT,\"polygon\":$POLYGON_COUNT}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v url="$OSM_URL" -v hash="$OSM_FILE_HASH" -v size_mb="$FILE_SIZE_MB" -v counts="$ROW_COUNTS_JSON" -v duration="$LOAD_DURATION" <<EOF
INSERT INTO data_version (osm_source_url, osm_file_hash, file_size_mb, row_counts, load_duration_seconds, success)
VALUES (:url, :hash, :size_mb, :counts::jsonb, :duration, TRUE);
EOF

log "Creating/refreshing parkour_features materialized view..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
DROP MATERIALIZED VIEW IF EXISTS parkour_features;
CREATE MATERIALIZED VIEW parkour_features AS
SELECT 
    osm_id,
    name,
    amenity,
    leisure,
    sport,
    way
FROM planet_osm_polygon
WHERE 
    amenity IN ('park', 'playground', 'sports_centre', 'stadium')
    OR leisure IN ('park', 'playground', 'sports_centre', 'stadium', 'pitch')
    OR sport IS NOT NULL
UNION ALL
SELECT 
    osm_id,
    name,
    amenity,
    NULL as leisure,
    NULL as sport,
    way
FROM planet_osm_point
WHERE 
    amenity IN ('park', 'playground', 'sports_centre', 'stadium');
CREATE INDEX IF NOT EXISTS idx_parkour_features_way ON parkour_features USING GIST (way);
EOF

log "OSM data loaded successfully in ${LOAD_DURATION}s!"
log "Cleaning up temporary PBF file..."
rm -f "$OSM_FILE"

log "Data loader completed successfully"
