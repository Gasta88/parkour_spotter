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

if [ -z "$OSM_LOCAL_FILE" ]; then
    log "Error: OSM_LOCAL_FILE is not set. Please provide a local .osm.pbf file."
    exit 1
fi

OSM_MIN_FILE_SIZE_MB=${OSM_MIN_FILE_SIZE_MB:-1}
REFRESH_INTERVAL_HOURS=${REFRESH_INTERVAL_HOURS:-24}
FORCE_RELOAD=${FORCE_RELOAD:-false}
OSM2PGSQL_CACHE_MB=${OSM2PGSQL_CACHE_MB:-512}
OSM2PGSQL_PROCESSES=${OSM2PGSQL_PROCESSES:-2}

OSM_FILE="/tmp/data.osm.pbf"

LOCAL_PATH="/osm-data/$OSM_LOCAL_FILE"
if [ -f "$LOCAL_PATH" ]; then
    log "Using local OSM file: $LOCAL_PATH"
    cp "$LOCAL_PATH" "$OSM_FILE"
else
    log "Error: OSM_LOCAL_FILE is set to '$OSM_LOCAL_FILE' but file not found at $LOCAL_PATH"
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
DB_NAME=$(echo "$DATABASE_URL" | grep -oP ':\d+/\K[^?]+')
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

log "Enabling required PostgreSQL extensions..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS h3;
EOF

log "TRUNCATING existing planet_osm_* tables for city-switching (if they exist)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF
DO \$\$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'planet_osm_point') THEN
        TRUNCATE TABLE planet_osm_point CASCADE;
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'planet_osm_line') THEN
        TRUNCATE TABLE planet_osm_line CASCADE;
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'planet_osm_polygon') THEN
        TRUNCATE TABLE planet_osm_polygon CASCADE;
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'planet_osm_roads') THEN
        TRUNCATE TABLE planet_osm_roads CASCADE;
    END IF;
END \$\$;
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

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v source="$OSM_LOCAL_FILE" -v hash="$OSM_FILE_HASH" -v size_mb="$FILE_SIZE_MB" -v counts="$ROW_COUNTS_JSON" -v duration="$LOAD_DURATION" <<EOF
INSERT INTO data_version (osm_source_url, osm_file_hash, file_size_mb, row_counts, load_duration_seconds, success)
VALUES (:'source', :'hash', :size_mb, :'counts'::jsonb, :duration, TRUE);
EOF

log "OSM data loaded successfully in ${LOAD_DURATION}s!"
log "Cleaning up temporary PBF file..."
rm -f "$OSM_FILE"

log "Data loader completed successfully"
