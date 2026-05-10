-- Initialize h3-pg extension for SQL-side H3 hexagon aggregation.
-- This script is mounted into the PostGIS container via docker-compose.yml
-- and executed on first startup via /docker-entrypoint-initdb.d/.
--
-- The h3-pg extension provides functions like:
--   h3_latlng_to_cell(lat, lng, resolution) -> h3_index
--   h3_cell_to_latlng(h3_index) -> (lat, lng)
--   h3_grid_disk(h3_index, k) -> setof h3_index (k-ring)
--
-- These are used by the feature extraction SQL queries to aggregate
-- OSM features into H3 hexagons at resolution 11 (~25m edge).

CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS h3;
