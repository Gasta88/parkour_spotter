"""SQL queries for OSM feature extraction with H3 aggregation.

This module contains parameterized SQL queries for extracting 8 categories
of parkour-relevant features from OpenStreetMap data loaded via osm2pgsql.

All queries use the h3-pg PostGIS extension for SQL-side H3 hexagon
aggregation at resolution 11 (~25m edge length).

Usage:
    from common.sql_queries import FEATURE_QUERIES, build_feature_query

    query = build_feature_query("walls", h3_indices=["8b1fb46622dffff", ...])
    result = await session.execute(query)

Note on H3 index format:
    h3-pg returns H3 indices as bigint values. The Python h3 library uses
    hex strings. The queries return bigint h3_index values which must be
    converted to hex strings in Python using: format(h3_bigint, 'x').
"""

from sqlalchemy import text

# H3 resolution used for parkour spot indexing
H3_RESOLUTION = 11

# ---------------------------------------------------------------------------
# Feature extraction queries
# ---------------------------------------------------------------------------
# Each query aggregates OSM features into H3 hexagons using h3-pg's
# h3_lat_lng_to_cell function. Results are grouped by h3_index and include
# count and geometry metrics (length for lines, area for polygons).
#
# Parameters:
#   :h3_indices — array of bigint H3 indices to filter on (k-ring coverage)
#
# The WHERE clause filters to only features whose centroid falls within
# one of the requested H3 cells, ensuring efficient index usage.
# ---------------------------------------------------------------------------

# FEATURE: walls
# OSM tags: barrier=wall, barrier=retaining_wall
# Geometry: line (planet_osm_line), polygon (planet_osm_polygon)
# Metric: count + total_length_m (lines), count + total_area_m2 (polygons)
#
# Walls are primary parkour features for vaulting, balancing, and climbing.
# Both linear walls (fence-like) and area walls (thick retaining walls) are captured.
QUERY_WALLS = """
-- FEATURE: walls
-- OSM tags: barrier=wall, barrier=retaining_wall
-- Geometry: line (planet_osm_line), polygon (planet_osm_polygon)
-- Metric: count + total_length_m (lines), count + total_area_m2 (polygons)
--
-- Combines line and polygon wall features. Line walls contribute length,
-- polygon walls contribute area. Both contribute to the count metric.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Length(ST_Transform(way, 4326)::geography)), 0) AS total_length_m,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_line
WHERE barrier IN ('wall', 'retaining_wall')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    0 AS total_length_m,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE (barrier IN ('wall', 'retaining_wall'))
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: steps
# OSM tags: highway=steps
# Geometry: line (planet_osm_line), polygon (planet_osm_polygon)
# Metric: count + total_length_m (lines), count + total_area_m2 (polygons)
#
# Steps/stairs are essential for precision jumps, drops, and vertical movement.
QUERY_STEPS = """
-- FEATURE: steps
-- OSM tags: highway=steps
-- Geometry: line (planet_osm_line), polygon (planet_osm_polygon)
-- Metric: count + total_length_m (lines), count + total_area_m2 (polygons)
--
-- Steps mapped as ways (lines) and as areas (polygons, e.g. wide staircases).
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Length(ST_Transform(way, 4326)::geography)), 0) AS total_length_m,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_line
WHERE highway = 'steps'
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    0 AS total_length_m,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE (highway = 'steps')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: rails_fences
# OSM tags: barrier=fence, railway=rail, barrier=handrail, barrier=guard_rail
# Geometry: line (planet_osm_line)
# Metric: count + total_length_m
#
# Rails and fences are used for balancing, vaulting, and as obstacles.
QUERY_RAILS_FENCES = """
-- FEATURE: rails_fences
-- OSM tags: barrier=fence, railway=rail, barrier=handrail, barrier=guard_rail
-- Geometry: line (planet_osm_line)
-- Metric: count + total_length_m
--
-- Linear features suitable for balance training and vaulting.
-- Includes fences, rails, handrails, and guard rails.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Length(ST_Transform(way, 4326)::geography)), 0) AS total_length_m
FROM planet_osm_line
WHERE (barrier IN ('fence', 'handrail', 'guard_rail')
   OR railway = 'rail')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: playgrounds
# OSM tags: leisure=playground
# Geometry: polygon (planet_osm_polygon), point (planet_osm_point)
# Metric: count + total_area_m2 (polygons), count (points)
#
# Playgrounds often have varied structures (walls, bars, platforms) ideal for parkour.
QUERY_PLAYGROUNDS = """
-- FEATURE: playgrounds
-- OSM tags: leisure=playground
-- Geometry: polygon (planet_osm_polygon), point (planet_osm_point)
-- Metric: count + total_area_m2 (polygons), count (points)
--
-- Playgrounds mapped as areas (polygons) and as point markers.
-- Area playgrounds provide total surface area; points provide count only.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE leisure = 'playground'
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    0 AS total_area_m2
FROM planet_osm_point
WHERE leisure = 'playground'
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: parking
# OSM tags: amenity=parking, parking=multi-storey, parking=underground
# Geometry: polygon (planet_osm_polygon)
# Metric: count + total_area_m2
#
# Multi-level and underground parking structures offer columns, ramps,
# ledges, and varied heights — excellent for advanced parkour training.
QUERY_PARKING = """
-- FEATURE: parking
-- OSM tags: amenity=parking, parking=multi-storey, parking=underground
-- Geometry: polygon (planet_osm_polygon)
-- Metric: count + total_area_m2
--
-- Parking areas, especially multi-storey and underground structures,
-- provide columns, ramps, ledges, and varied vertical elements.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE (amenity = 'parking'
   OR tags->'parking' IN ('multi-storey', 'underground'))
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: benches_blocks
# OSM tags: amenity=bench, barrier=block
# Geometry: point (planet_osm_point)
# Metric: count
#
# Benches and blocks are used for precision jumps, vaults, and as obstacles.
QUERY_BENCHES_BLOCKS = """
-- FEATURE: benches_blocks
-- OSM tags: amenity=bench, barrier=block
-- Geometry: point (planet_osm_point)
-- Metric: count
--
-- Benches and concrete blocks serve as precision targets and vault obstacles.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_point
WHERE (amenity = 'bench'
   OR barrier = 'block')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: fitness_stations
# OSM tags: leisure=fitness_station, sport=fitness
# Geometry: point (planet_osm_point), polygon (planet_osm_polygon)
# Metric: count
#
# Outdoor fitness stations often have bars, platforms, and structures
# that double as parkour training equipment.
QUERY_FITNESS_STATIONS = """
-- FEATURE: fitness_stations
-- OSM tags: leisure=fitness_station, sport=fitness
-- Geometry: point (planet_osm_point), polygon (planet_osm_polygon)
-- Metric: count
--
-- Outdoor fitness areas with bars, platforms, and structures useful
-- for parkour cross-training (muscle-ups, balance, etc.).
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_point
WHERE (leisure = 'fitness_station'
   OR sport = 'fitness')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_polygon
WHERE (leisure = 'fitness_station'
   OR sport = 'fitness')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: private_access_penalty
# OSM tags: access=private, access=no
# Geometry: point (planet_osm_point), line (planet_osm_line), polygon (planet_osm_polygon)
# Metric: count (subtracted from score)
#
# Features with private/no access restrictions are penalized in scoring
# since they are not legally accessible for parkour training.
QUERY_PRIVATE_ACCESS = """
-- FEATURE: private_access_penalty
-- OSM tags: access=private, access=no
-- Geometry: point (planet_osm_point), line (planet_osm_line), polygon (planet_osm_polygon)
-- Metric: count (subtracted from score)
--
-- Features marked as private or no-access reduce the parkour suitability
-- score since they are not legally accessible for training.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_point
WHERE access IN ('private', 'no')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_line
WHERE access IN ('private', 'no')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_polygon
WHERE access IN ('private', 'no')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: bridges
# OSM tags: man_made=bridge, bridge=yes
# Geometry: line (planet_osm_line), polygon (planet_osm_polygon)
# Metric: count + total_length_m (lines), count + total_area_m2 (polygons)
#
# Bridges provide elevated platforms, railings, and varied heights for parkour.
QUERY_BRIDGES = """
-- FEATURE: bridges
-- OSM tags: man_made=bridge, bridge=yes
-- Geometry: line (planet_osm_line), polygon (planet_osm_polygon)
-- Metric: count + total_length_m (lines), count + total_area_m2 (polygons)
--
-- Bridges offer elevated walkways, railings, and structural elements
-- suitable for parkour training.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Length(ST_Transform(way, 4326)::geography)), 0) AS total_length_m,
    0 AS total_area_m2
FROM planet_osm_line
WHERE (man_made = 'bridge'
   OR bridge = 'yes')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    0 AS total_length_m,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE (man_made = 'bridge'
   OR bridge = 'yes')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: rocks_stones
# OSM tags: natural=stone, natural=rock
# Geometry: point (planet_osm_point), polygon (planet_osm_polygon)
# Metric: count + total_area_m2 (polygons), count (points)
#
# Natural rocks and stones provide varied textures and heights for climbing practice.
QUERY_ROCKS_STONES = """
-- FEATURE: rocks_stones
-- OSM tags: natural=stone, natural=rock
-- Geometry: point (planet_osm_point), polygon (planet_osm_polygon)
-- Metric: count + total_area_m2 (polygons), count (points)
--
-- Natural rock formations and large stones offer climbing and balancing
-- opportunities with varied textures and heights.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE (natural IN ('stone', 'rock'))
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    0 AS total_area_m2
FROM planet_osm_point
WHERE (natural IN ('stone', 'rock'))
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: sports_pitches
# OSM tags: leisure=pitch, sport=basketball, sport=football, sport=tennis, etc.
# Geometry: polygon (planet_osm_polygon)
# Metric: count + total_area_m2
#
# Sports pitches have lines, courts, walls, and equipment useful for parkour.
QUERY_SPORTS_PITCHES = """
-- FEATURE: sports_pitches
-- OSM tags: leisure=pitch, sport=basketball, sport=football, sport=tennis, etc.
-- Geometry: polygon (planet_osm_polygon)
-- Metric: count + total_area_m2
--
-- Sports courts and pitches provide marked lines, low walls, basketball hoops,
-- goal posts, and varied surfaces for parkour training.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count,
    COALESCE(SUM(ST_Area(ST_Transform(way, 4326)::geography)), 0) AS total_area_m2
FROM planet_osm_polygon
WHERE (leisure = 'pitch'
   OR sport IN ('basketball', 'football', 'tennis', 'volleyball', 'handball', 'futsal'))
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# FEATURE: good_surfaces
# OSM tags: surface=paving_stones, surface=concrete, surface=asphalt, surface=wood
# Geometry: point (planet_osm_point), line (planet_osm_line), polygon (planet_osm_polygon)
# Metric: count
#
# Good surfaces (smooth, flat) are preferred for safe parkour training.
# This acts as a bonus modifier rather than an additive feature.
QUERY_GOOD_SURFACES = """
-- FEATURE: good_surfaces
-- OSM tags: surface=paving_stones, surface=concrete, surface=asphalt, surface=wood
-- Geometry: point (planet_osm_point), line (planet_osm_line), polygon (planet_osm_polygon)
-- Metric: count
--
-- Features with smooth, flat surfaces are safer for parkour training.
-- This category acts as a bonus modifier on the final score.
SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_point
WHERE surface IN ('paving_stones', 'concrete', 'asphalt', 'wood', 'paved')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_line
WHERE surface IN ('paving_stones', 'concrete', 'asphalt', 'wood', 'paved')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index

UNION ALL

SELECT
    h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) AS h3_index,
    COUNT(*) AS count
FROM planet_osm_polygon
WHERE surface IN ('paving_stones', 'concrete', 'asphalt', 'wood', 'paved')
  AND h3_lat_lng_to_cell(ST_Transform(ST_Centroid(way), 4326)::point, :resolution) = ANY(SELECT bigint_to_h3index(x) FROM unnest(CAST(:h3_indices AS bigint[])) AS x)
GROUP BY h3_index
"""

# ---------------------------------------------------------------------------
# Query registry — maps feature category name to SQL template
# ---------------------------------------------------------------------------

FEATURE_QUERIES: dict[str, str] = {
    "walls": QUERY_WALLS,
    "steps": QUERY_STEPS,
    "rails_fences": QUERY_RAILS_FENCES,
    "playgrounds": QUERY_PLAYGROUNDS,
    "parking": QUERY_PARKING,
    "benches_blocks": QUERY_BENCHES_BLOCKS,
    "fitness_stations": QUERY_FITNESS_STATIONS,
    "private_access_penalty": QUERY_PRIVATE_ACCESS,
    "bridges": QUERY_BRIDGES,
    "rocks_stones": QUERY_ROCKS_STONES,
    "sports_pitches": QUERY_SPORTS_PITCHES,
    "good_surfaces": QUERY_GOOD_SURFACES,
}


def build_feature_query(
    feature_name: str, h3_indices: list[int], resolution: int = H3_RESOLUTION
) -> text:
    """Build a parameterized SQLAlchemy text query for a feature category.

    Args:
        feature_name: One of the keys in FEATURE_QUERIES
        h3_indices: List of H3 indices as bigint values for k-ring filtering
        resolution: H3 resolution level (default: 11)

    Returns:
        SQLAlchemy text object ready for execution

    Raises:
        ValueError: If feature_name is not a recognized category
    """
    if feature_name not in FEATURE_QUERIES:
        raise ValueError(
            f"Unknown feature category: {feature_name}. "
            f"Valid categories: {list(FEATURE_QUERIES.keys())}"
        )

    sql_template = FEATURE_QUERIES[feature_name]
    return text(sql_template).bindparams(
        h3_indices=h3_indices,
        resolution=resolution,
    )


def get_all_feature_names() -> list[str]:
    """Return all recognized feature category names.

    Returns:
        List of feature category strings
    """
    return list(FEATURE_QUERIES.keys())
