# Spec: issue-initial-scaffold

## Requirements

### User Story
As a developer working on the Parkour Spotter project, I need a complete initial project scaffold with all services, shared packages, configuration files, and directory structures in place so that subsequent feature development (OSM data loading, parkour spot analysis, annotation UI, and frontend map) can proceed without structural blockers.

### Acceptance Criteria
- [ ] All directories and files from the light spec project structure exist on disk
- [ ] `pyproject.toml` at root defines a uv workspace containing `common`, `services/api`, and `services/annotator`
- [ ] `docker-compose.yml` defines all 5 services: postgis, osm-loader, api, annotator, frontend
- [ ] `common/` package contains `db.py`, `h3_utils.py`, `models.py` with stub implementations
- [ ] `services/api/` is a working FastAPI app with `/health` and `/analyze` endpoints (stub)
- [ ] `services/annotator/` is a working FastAPI app serving static UI with `/health` endpoint
- [ ] `services/frontend/` serves a Leaflet map via nginx on port 8080
- [ ] `scripts/osm-loader/` has a Dockerfile and entrypoint script for osm2pgsql
- [ ] `Makefile` provides common dev commands (up, down, test, lint)
- [ ] `.env.example` documents all required environment variables
- [ ] `docs/SCOPE.md` exists with project scope documentation
- [ ] All services start successfully via `docker compose up`
- [ ] pytest is configured and at least one placeholder test passes

### Functional Requirements
- Root `pyproject.toml` must declare a uv workspace with members: `common`, `services/api`, `services/annotator`
- `common` package must export async SQLAlchemy engine/session factory, H3 hex utilities, and shared model base
- API service must expose `POST /analyze` (stub returning placeholder scoring data) and `GET /health`
- Annotator service must serve static files from `static/` and expose `GET /health`
- Frontend must serve `index.html` with Leaflet map initialization via nginx
- OSM loader must be a one-shot container that depends on postgis being healthy
- All services must be orchestratable via a single `docker-compose.yml`

### Non-Functional Requirements
- Performance: All services must start within 30 seconds via `docker compose up`
- Security: `.env.example` must not contain real secrets; `.gitignore` must exclude `.env`
- Maintainability: Each service has its own `pyproject.toml` with explicit dependencies
- Reproducibility: Dockerfiles use pinned base image tags
- Testing: pytest configured with async support in `services/api`

## Technical Specification

### Files to Modify
| File | Change |
|------|--------|
| `.gitignore` | Add Python, Docker, uv, env, and IDE exclusions |
| `README.md` | Add project overview, quick-start, and make targets |

### Files to Create
| File | Purpose |
|------|---------|
| `pyproject.toml` | Root uv workspace definition with members |
| `docker-compose.yml` | Orchestrates all 5 services |
| `Makefile` | Dev commands: up, down, test, lint, load-osm, seed |
| `.env.example` | Template for environment variables |
| `common/pyproject.toml` | Common package definition |
| `common/common/__init__.py` | Package init |
| `common/common/db.py` | Async SQLAlchemy engine + session factory |
| `common/common/h3_utils.py` | H3 resolution constants, hex grid helpers |
| `common/common/models.py` | Shared declarative base + model stubs |
| `services/api/Dockerfile` | API service container |
| `services/api/pyproject.toml` | API deps (fastapi, uvicorn, sqlalchemy, asyncpg, h3, pytest) |
| `services/api/app/__init__.py` | Package init |
| `services/api/app/main.py` | FastAPI app factory, router registration |
| `services/api/app/config.py` | Pydantic Settings for DB URL, H3 resolution, etc. |
| `services/api/app/routers/analyze.py` | POST /analyze stub endpoint |
| `services/api/app/routers/health.py` | GET /health endpoint |
| `services/api/app/schemas/analyze.py` | Request/response Pydantic models for /analyze |
| `services/api/app/schemas/hex.py` | HexCell Pydantic model |
| `services/api/app/services/osm_query.py` | PostGIS query stub (Phase 1 placeholder) |
| `services/api/app/scorers/__init__.py` | Scorers package init |
| `services/api/app/scorers/rule_based.py` | Rule-based scorer stub (Phase 1 placeholder) |
| `services/api/app/tests/__init__.py` | Tests package init |
| `services/api/app/tests/test_scorers.py` | Placeholder scorer tests |
| `services/api/app/tests/test_analyze.py` | Placeholder analyze endpoint tests |
| `services/annotator/Dockerfile` | Annotator service container |
| `services/annotator/pyproject.toml` | Annotator deps (fastapi, uvicorn, sqlalchemy, asyncpg) |
| `services/annotator/app/__init__.py` | Package init |
| `services/annotator/app/main.py` | FastAPI app + static file mounting |
| `services/annotator/app/static/index.html` | Annotator UI shell |
| `services/annotator/app/static/app.js` | Annotator JS stub |
| `services/annotator/app/routers/spots.py` | CRUD stub for annotations |
| `services/annotator/app/routers/health.py` | GET /health endpoint |
| `services/frontend/Dockerfile` | Nginx container for frontend |
| `services/frontend/nginx.conf` | Nginx config serving static files |
| `services/frontend/index.html` | Leaflet map UI stub |
| `scripts/osm-loader/Dockerfile` | osm2pgsql + wget container |
| `scripts/osm-loader/entrypoint.sh` | Download + load OSM extract script |

### API Contracts

#### GET /health (api service)
Request: none
Response:
```json
{
  "status": "ok",
  "service": "api",
  "version": "0.1.0"
}
```

#### POST /analyze (api service)
Request:
```json
{
  "lat": 45.4408,
  "lon": 12.3155,
  "radius_km": 5.0
}
```
Response:
```json
{
  "cells": [
    {
      "h3_index": "8b1fb46622dffff",
      "score": 0.75,
      "centroid": { "lat": 45.4408, "lon": 12.3155 }
    }
  ],
  "data_version": "unknown",
  "query_time_ms": 0
}
```

#### GET /health (annotator service)
Request: none
Response:
```json
{
  "status": "ok",
  "service": "annotator",
  "version": "0.1.0"
}
```

### Database Changes
- Table: None created in this scaffold (models.py contains only declarative base stubs)
- Migration required: no (Alembic setup deferred to a later issue)
- Changes: `common/models.py` defines `Base = DeclarativeBase` for future model inheritance

### External Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115,<0.116 | API framework |
| uvicorn | >=0.32,<0.33 | ASGI server |
| sqlalchemy | >=2.0,<3.0 | ORM |
| asyncpg | >=0.30,<0.31 | Async Postgres driver |
| h3 | >=4.1,<5.0 | H3 hex grid library |
| pydantic-settings | >=2.6,<3.0 | Settings management |
| pytest | >=8.3,<9.0 | Test framework |
| pytest-asyncio | >=0.24,<0.25 | Async test support |
| postgis | 3.4 (via pg16) | Spatial extensions |
| h3-pg | latest | H3 PostGIS extension |
| nginx | 1.27-alpine | Frontend static server |

## Implementation Plan

| # | Sub-task | Complexity (1–5) | Depends On |
|---|----------|------------------|------------|
| 1 | Create root config files: `pyproject.toml` (uv workspace), `docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore`, `README.md` | 2 | — |
| 2 | Create `common/` package: `pyproject.toml`, `__init__.py`, `db.py`, `h3_utils.py`, `models.py` | 2 | 1 |
| 3 | Create `services/api/`: Dockerfile, pyproject.toml, app structure, routers, schemas, scorers stubs, services stub | 3 | 2 |
| 4 | Create `services/annotator/`: Dockerfile, pyproject.toml, app structure, routers, static UI stubs | 3 | 2 |
| 5 | Create `services/frontend/`: Dockerfile, nginx.conf, index.html with Leaflet stub | 2 | 1 |
| 6 | Create `scripts/osm-loader/`: Dockerfile, entrypoint.sh | 2 | 1 |
| 7 | Wire up tests: pytest config, placeholder tests for scorers and analyze endpoint | 2 | 3 |

### Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| uv workspace member paths incorrect | medium | Validate with `uv sync` after creation |
| Docker Compose service networking misconfigured | medium | Use explicit service names and depends_on with healthchecks |
| H3 library version incompatibility with Python version | low | Pin h3>=4.1,<5.0 which supports Python 3.12+ |
| osm-loader entrypoint script permissions | low | Set executable bit in Dockerfile with chmod |
| Port conflicts on developer machine | low | Use non-standard ports (8000, 8001, 8080) documented in .env.example |

## Test Strategy

### Unit Tests
- [ ] `test_scorers.py`: Verify rule-based scorer stub returns a dict with expected keys (`score`, `h3_index`)
- [ ] `test_analyze.py`: Verify POST /analyze returns 200 with valid request body and correct response schema
- [ ] `test_health.py` (api): Verify GET /health returns `{"status": "ok", "service": "api"}`
- [ ] `test_health.py` (annotator): Verify GET /health returns `{"status": "ok", "service": "annotator"}`
- [ ] `test_h3_utils.py`: Verify H3 resolution constant is set to 11 and hex helper functions return valid types
- [ ] `test_db.py`: Verify engine creation returns an AsyncEngine and session factory returns async_session

### Integration Tests
- [ ] `docker compose up` exits cleanly with all 5 services running
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] `curl http://localhost:8001/health` returns 200
- [ ] `curl http://localhost:8080` returns the Leaflet HTML page
- [ ] `curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d '{"lat":45.44,"lon":12.31,"radius_km":5}'` returns 200 with cells array

### E2E Scenarios
- [ ] Full stack bootstrap: `make up` → all services healthy → `make test` passes
- [ ] Analyze flow: POST /analyze with Veneto coordinates → returns non-empty cells array with scores in [0,1]

### Edge Cases
- [ ] POST /analyze with missing fields → returns 422 validation error
- [ ] POST /analyze with radius_km > 10 → returns 422 or clamps to 10
- [ ] POST /analyze with invalid lat/lon (out of range) → returns 422
- [ ] Services started without DATABASE_URL set → app fails fast with clear error
- [ ] uv workspace resolves `common` package correctly from both api and annotator services

## Definition of Done
- [ ] All acceptance criteria satisfied
- [ ] Unit test coverage ≥ 80% for changed files
- [ ] Integration tests passing in CI
- [ ] API documentation updated
- [ ] No performance regressions
- [ ] Code review approved
