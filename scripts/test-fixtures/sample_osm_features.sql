-- Deterministic OSM fixture for integration tests.
-- Idempotent: clears its own rows before inserting so it can be applied
-- repeatedly against the same test container.
-- Coordinates match the Veneto test area used by the API test suite.

DELETE FROM planet_osm_line WHERE osm_id BETWEEN 90001 AND 90099;
DELETE FROM planet_osm_point WHERE osm_id BETWEEN 90001 AND 90099;
DELETE FROM planet_osm_polygon WHERE osm_id BETWEEN 90001 AND 90099;
DELETE FROM data_version WHERE osm_source_url = 'test-fixture';

INSERT INTO data_version (osm_source_url, osm_file_hash, file_size_mb, row_counts)
VALUES (
    'test-fixture',
    'fixture-sha256',
    0.01,
    '{"planet_osm_line": 3, "planet_osm_point": 2, "planet_osm_polygon": 1}'::jsonb
);

-- Wall along the test coordinates
INSERT INTO planet_osm_line (osm_id, name, barrier, way) VALUES (
    90001,
    'Fixture wall',
    'wall',
    ST_Transform(
        ST_SetSRID(
            ST_MakeLine(
                ST_MakePoint(12.3095, 45.4395),
                ST_MakePoint(12.3110, 45.4405)
            ),
            4326
        ),
        3857
    )
);

-- Staircase near the same cell
INSERT INTO planet_osm_line (osm_id, name, highway, way) VALUES (
    90002,
    'Fixture steps',
    'steps',
    ST_Transform(
        ST_SetSRID(
            ST_MakeLine(
                ST_MakePoint(12.3100, 45.4398),
                ST_MakePoint(12.3104, 45.4402)
            ),
            4326
        ),
        3857
    )
);

-- Railing for vault features
INSERT INTO planet_osm_line (osm_id, name, barrier, way) VALUES (
    90003,
    'Fixture railing',
    'fence',
    ST_Transform(
        ST_SetSRID(
            ST_MakeLine(
                ST_MakePoint(12.3115, 45.4400),
                ST_MakePoint(12.3120, 45.4404)
            ),
            4326
        ),
        3857
    )
);

-- Bench and fitness station points
INSERT INTO planet_osm_point (osm_id, name, amenity, leisure, way) VALUES (
    90010,
    'Fixture bench',
    'bench',
    NULL,
    ST_Transform(ST_SetSRID(ST_MakePoint(12.3102, 45.4399), 4326), 3857)
);

INSERT INTO planet_osm_point (osm_id, name, amenity, leisure, way) VALUES (
    90011,
    'Fixture fitness station',
    NULL,
    'fitness_station',
    ST_Transform(ST_SetSRID(ST_MakePoint(12.3106, 45.4403), 4326), 3857)
);

-- Parking polygon gives the scoring layer an open-space feature
INSERT INTO planet_osm_polygon (osm_id, name, amenity, parking, way) VALUES (
    90020,
    'Fixture parking',
    'parking',
    'surface',
    ST_Transform(
        ST_GeomFromText(
            'POLYGON((12.3112 45.4396, 12.3122 45.4396, 12.3122 45.4402, 12.3112 45.4402, 12.3112 45.4396))',
            4326
        ),
        3857
    )
);
