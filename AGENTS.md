# AGENTS.md - Parkour Spotter

AI agent guidelines for developing in this repository.

## Project Overview

Parkour Spotter analyzes and annotates parkour spots using OpenStreetMap data and H3 hexagonal grid indexing. Python monorepo with Docker-based services.

## Tech Stack

- **Python 3.12+** with `uv` package manager
- **FastAPI** for backend (API + Annotator)
- **PostgreSQL 15 + PostGIS** for spatial data
- **H3** for hexagonal grid indexing
- **SQLAlchemy 2.0** (async) with `asyncpg`
- **Pydantic Settings** for configuration
- **Leaflet** for frontend map UI
- **Ruff** for linting/formatting
- **pytest + pytest-asyncio** for testing

## Project Structure

```
parkour_spotter/
├── common/                  # Shared Python package
│   └── common/
│       ├── db.py, h3_utils.py, models.py, osm_models.py, sql_queries.py
├── services/
│   ├── api/                 # Analysis API (port 8000)
│   │   └── app/
│   │       ├── config.py, db.py, main.py
│   │       ├── routers/     # analyze.py, health.py
│   │       ├── schemas/, scorers/, services/, tests/
│   ├── annotator/           # Annotation UI (port 8001)
│   │   └── app/
│   │       ├── config.py, db.py, main.py
│   │       ├── routers/     # health.py, spots.py
│   │       └── static/
│   ├── frontend/            # Leaflet map (port 8080)
│   └── postgis/             # PostGIS Docker image
├── scripts/
│   ├── init-db.sql, seed-data.sql
│   └── osm-loader/          # OSM data loader + tests
├── data/                    # Local OSM PBF files (git-ignored)
├── conftest.py              # pytest fixtures
├── docker-compose.yml
├── Makefile
└── pyproject.toml
```

## Key Commands

```bash
make up              # Start all services
make down            # Stop all services
make restart         # Restart services
make test            # Run tests
make lint            # Lint and format check
make logs            # View all logs
make logs-db         # Database logs
make logs-api        # API logs
make logs-annotator  # Annotator logs
make logs-frontend   # Frontend logs
make load-osm OSM_LOCAL_FILE=city.osm.pbf    # Load OSM data
make load-local OSM_LOCAL_FILE=city.osm.pbf  # Load from local PBF
make load-osm-force  # Force reload OSM data
make status          # Check database status
make seed            # Seed database
make clean-osm       # Clean tables (keeps volume)
make clean           # Full clean (removes volumes)
make shell-db        # Shell into database
```

## Python Workspace

`uv` workspace monorepo with members: `common`, `services/api`, `services/annotator`. Add dependencies to appropriate `pyproject.toml`.

## Testing

- `pytest` with `pytest-asyncio` (auto mode)
- `testcontainers` for isolated PostgreSQL instances
- Fixtures in `conftest.py`: `postgres_container`, `db_url`, `db_connection`, `postgis_db_url`, `postgis_connection`
- Test paths: `services/api/app/tests`, `scripts/osm-loader/tests`
- Run: `make test` or `uv run pytest`
- Docker required for testcontainers

## Linting & Formatting

```bash
make lint                    # Check only
uv run ruff check . --fix    # Auto-fix
uv run ruff format .         # Auto-format
```

## Database

- PostgreSQL 15 with PostGIS and H3 extensions
- OSM data: `planet_osm_point`, `planet_osm_line`, `planet_osm_polygon`, `planet_osm_roads`
- `data_version` tracks load history
- Application tables: `spots_annotated`, `saved_search`, `cell_feature`, `model`, `model_evaluation`, `training_run`
- Connection: `DATABASE_URL` (async: `postgresql+asyncpg://`, sync: `postgresql://`)

## Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Key variables: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, `DATABASE_URL`, `H3_RESOLUTION` (default: 11), `OSM_LOCAL_FILE`, `OSM_MIN_FILE_SIZE_MB`, `REFRESH_INTERVAL_HOURS`, `FORCE_RELOAD`, `OSM2PGSQL_CACHE_MB`, `OSM2PGSQL_PROCESSES`, `API_PORT`, `ANNOTATOR_PORT`, `FRONTEND_PORT`

## Service Ports

| Service     | Port | Description                    |
|-------------|------|--------------------------------|
| postgis     | 5432 | PostgreSQL with PostGIS        |
| api         | 8000 | FastAPI backend for analysis   |
| annotator   | 8001 | FastAPI annotation UI backend  |
| frontend    | 8080 | Leaflet map frontend           |
| osm-loader  | -    | One-shot OSM data loader       |

## Code Conventions

- Use async/await throughout (asyncpg, async SQLAlchemy)
- Follow module structure: routers -> services -> schemas
- Shared code goes in `common/` package
- Pydantic models for request/response validation
- SQLAlchemy models for database queries
- H3 resolution defaults to 11
- No comments unless explicitly requested

## Important Notes

- `specs/` is git-ignored - do not rely on it for persistent docs
- `data/*.pbf` files are git-ignored
- `uv.lock` is git-ignored (regenerated from workspace config)
- Always run `make lint` and `make test` before completing work
- Docker must be running for tests and services
