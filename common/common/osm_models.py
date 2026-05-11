"""SQLAlchemy models for OSM planet_osm_* tables.

These models reflect the schema created by osm2pgsql in slim mode with hstore.
They are read-only and used for type hints and ORM-based queries.

Tables:
    - planet_osm_point: OSM point features (nodes)
    - planet_osm_line: OSM line features (ways mapped as lines)
    - planet_osm_polygon: OSM polygon features (closed ways / multipolygons)
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped

from common.models import Base


class PlanetOsmPoint(Base):
    """OSM point features loaded by osm2pgsql.

    Contains nodes with tags such as amenity, leisure, sport, barrier, etc.
    The `way` column is a PostGIS geometry (POINT).
    The `tags` column is an hstore key-value store for all OSM tags.
    """

    __tablename__ = "planet_osm_point"

    osm_id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str | None] = Column(String)
    amenity: Mapped[str | None] = Column(String)
    leisure: Mapped[str | None] = Column(String)
    sport: Mapped[str | None] = Column(String)
    barrier: Mapped[str | None] = Column(String)
    highway: Mapped[str | None] = Column(String)
    access: Mapped[str | None] = Column(String)
    # PostGIS geometry column (POINT) — not mapped as a standard SQLAlchemy type
    # Use text() queries with ST_* functions for spatial operations
    # tags: hstore column — accessed via text() queries


class PlanetOsmLine(Base):
    """OSM line features loaded by osm2pgsql.

    Contains ways mapped as lines with tags such as highway, barrier, railway, etc.
    The `way` column is a PostGIS geometry (LINESTRING).
    """

    __tablename__ = "planet_osm_line"

    osm_id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str | None] = Column(String)
    amenity: Mapped[str | None] = Column(String)
    leisure: Mapped[str | None] = Column(String)
    sport: Mapped[str | None] = Column(String)
    barrier: Mapped[str | None] = Column(String)
    highway: Mapped[str | None] = Column(String)
    railway: Mapped[str | None] = Column(String)
    access: Mapped[str | None] = Column(String)
    # PostGIS geometry column (LINESTRING) — use text() queries for spatial ops


class PlanetOsmPolygon(Base):
    """OSM polygon features loaded by osm2pgsql.

    Contains closed ways and multipolygons with tags such as amenity, leisure, etc.
    The `way` column is a PostGIS geometry (POLYGON / MULTIPOLYGON).
    """

    __tablename__ = "planet_osm_polygon"

    osm_id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str | None] = Column(String)
    amenity: Mapped[str | None] = Column(String)
    leisure: Mapped[str | None] = Column(String)
    sport: Mapped[str | None] = Column(String)
    barrier: Mapped[str | None] = Column(String)
    highway: Mapped[str | None] = Column(String)
    access: Mapped[str | None] = Column(String)
    parking: Mapped[str | None] = Column(String)
    # PostGIS geometry column (POLYGON/MULTIPOLYGON) — use text() queries for spatial ops
