# AGENTS.md - Parkour Spotter

AI agent guidelines for developing in this repository.

## Project Overview

Parkour Spotter is a platform for analyzing and annotating parkour spots using OpenStreetMap (OSM) data and H3 hexagonal grid indexing. It is a Python monorepo with Docker-based services.

## Tech Stack

- **Python 3.12+** with `uv` as the package manager
- **FastAPI** for backend services (API + Annotator)
- **PostgreSQL 15 + PostGIS** for spatial data
- **H3** for hexagonal grid indexing
- **SQLAlchemy 2.0** (async) with `asyncpg`
- **Pydantic Settings** for configuration
- **Leaflet** for frontend map UI
- **Docker Compose** for service orchestration
- **Ruff** for linting/formatting
- **pytest + pytest-asyncio** for testing

## Project Structure

```
parkour_spotter/
├── common/                  # Shared Python package (models, DB utils, H3 utils)
│   └── common/
│       ├── db.py            # Database connection utilities
│       ├── h3_utils.py      # H3 hex grid utilities
│       ├── models.py        # Shared Pydantic/SQLAlchemy models
│       ├── osm_models.py    # OSM table SQLAlchemy models
│       └── sql_queries.py   # Shared SQL queries
├── services/
│   ├── api/                 # Analysis API (port 8000)
│   │   └── app/
│   │       ├── config.py    # Service settings
│   │       ├── main.py      # FastAPI app entry point
│   │       ├── routers/     # API route handlers
│   │       ├── schemas/     # Pydantic request/response schemas
│   │       ├── scorers/     # Parkour spot scoring logic
│   │       ├── services/    # Business logic layer
│   │       └── tests/       # API service tests
│   ├── annotator/           # Annotation UI API (port 8001)
│   │   └── app/
│   │       ├── main.py      # FastAPI app entry point
│   │       ├── routers/     # API route handlers
│   │       └── static/      # Static frontend assets
│   ├── frontend/            # Leaflet map frontend (port 8080)
│   │   ├── index.html       # Single-page frontend
│   │   └── nginx.conf       # Nginx config for serving
│   └── postgis/
│       └── Dockerfile       # PostGIS Docker image
├── scripts/
│   ├── osm-loader/          # OSM data loading script + tests
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   └── tests/
│   └── init-h3-pg.sql       # H3 PostgreSQL extension init
├── specs/                   # Feature specs (git-ignored)
├── data/                    # Local OSM PBF files (git-ignored)
├── conftest.py              # Root pytest fixtures (PostgreSQL testcontainers)
├── docker-compose.yml       # Service orchestration
├── Makefile                 # Common dev commands
└── pyproject.toml           # Root workspace config + dev dependencies
```

## Key Commands

```bash
# Start all services
make up

# Stop all services
make down

# Run tests
make test

# Run linter and format check
make lint

# View logs
make logs

# Load OSM data (one-time setup)
make load-osm

# Load from local PBF file
make load-local OSM_LOCAL_FILE=city.osm.pbf

# Force reload OSM data
make load-osm-force

# Check database status
make status

# Clean database tables
make clean-osm

# Full clean (removes volumes)
make clean
```

## Python Workspace

This is a `uv` workspace monorepo. Members are:
- `common` - shared package
- `services/api` - analysis API
- `services/annotator` - annotation API

Add dependencies to the appropriate `pyproject.toml`. Root `pyproject.toml` contains shared dev dependencies.

## Testing

- Tests use `pytest` with `pytest-asyncio` in auto mode
- Database tests use `testcontainers` for isolated PostgreSQL instances
- Root `conftest.py` provides fixtures:
  - `postgres_container` - session-scoped PostgreSQL container
  - `db_url` - function-scoped clean database URL
  - `db_connection` - asyncpg connection
  - `postgis_db_url` - PostGIS-enabled database URL
  - `postgis_connection` - PostGIS connection
- Test paths: `services/api/app/tests`, `scripts/osm-loader/tests`
- Run: `make test` or `uv run pytest`

## Linting & Formatting

Uses `ruff` for both linting and formatting:

```bash
# Check only
make lint

# Auto-fix lint issues
uv run ruff check . --fix

# Auto-format
uv run ruff format .
```

## Database

- PostgreSQL 15 with PostGIS and H3 extensions
- OSM data loaded via `osm2pgsql` into `planet_osm_point`, `planet_osm_line`, `planet_osm_polygon`, `planet_osm_roads`
- `data_version` table tracks load history
- Connection via `DATABASE_URL` environment variable (async: `postgresql+asyncpg://`, sync: `postgresql://`)

## Configuration

Services use `pydantic-settings` for configuration. See `.env.example` for all available variables. Copy to `.env` before running:

```bash
cp .env.example .env
```

## Service Ports

| Service   | Port | Description                    |
|-----------|------|--------------------------------|
| postgis   | 5432 | PostgreSQL with PostGIS        |
| api       | 8000 | FastAPI backend for analysis   |
| annotator | 8001 | FastAPI annotation UI backend  |
| frontend  | 8080 | Leaflet map frontend           |

## Code Conventions

- Use async/await throughout (asyncpg, async SQLAlchemy)
- Follow existing module structure: routers -> services -> schemas
- Shared code goes in `common/` package
- Use Pydantic models for request/response validation
- Use SQLAlchemy models for database queries
- H3 resolution defaults to 11 (configurable via `H3_RESOLUTION`)
- No comments unless explicitly requested

## Important Notes

- `specs/` directory is git-ignored - do not rely on it for persistent documentation
- `data/*.pbf` files are git-ignored
- `uv.lock` is git-ignored (regenerated from workspace config)
- Always run `make lint` and `make test` before considering work complete
- Docker must be running for tests (testcontainers) and services
