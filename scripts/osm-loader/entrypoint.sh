#!/bin/bash
set -e

echo "Starting OSM data loader..."

if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL not set"
    exit 1
fi

if [ -z "$OSM_URL" ]; then
    echo "Error: OSM_URL not set"
    exit 1
fi

OSM_FILE="/tmp/data.osm.pbf"

echo "Downloading OSM data from $OSM_URL..."
wget -O "$OSM_FILE" "$OSM_URL"

echo "Extracting database connection details..."
DB_HOST=$(echo "$DATABASE_URL" | grep -oP '@\K[^:]+')
DB_PORT=$(echo "$DATABASE_URL" | grep -oP ':\K[0-9]+(?=/)')
DB_NAME=$(echo "$DATABASE_URL" | grep -oP '/\K[^?]+')
DB_USER=$(echo "$DATABASE_URL" | grep -oP '://\K[^:]+')
export PGPASSWORD=$(echo "$DATABASE_URL" | grep -oP '://[^:]+:\K[^@]+')

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "PostgreSQL is up - loading OSM data..."

osm2pgsql \
    --database "$DB_NAME" \
    --host "$DB_HOST" \
    --port "$DB_PORT" \
    --username "$DB_USER" \
    --slim \
    --drop \
    --number-processes 2 \
    "$OSM_FILE"

echo "OSM data loaded successfully!"
rm "$OSM_FILE"
