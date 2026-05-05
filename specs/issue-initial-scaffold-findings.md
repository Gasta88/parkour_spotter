# Initial Scaffold

## Project Structure

```
parkour-spotter/
├── docker-compose.yml
├── Makefile
├── .env.example
├── .gitignore
├── pyproject.toml              # uv workspace definition
│
├── common/
│   ├── pyproject.toml
│   └── common/
│       ├── __init__.py
│       ├── db.py               # async engine, session factory
│       ├── h3_utils.py         # H3 resolution, hex helpers
│       └── models.py           # shared SQLAlchemy models
│
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml      # depends on common
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py         # FastAPI app
│   │       ├── config.py       # settings
│   │       ├── routers/
│   │       │   ├── analyze.py  # POST /analyze
│   │       │   └── health.py   # GET /health
│   │       ├── schemas/
│   │       │   ├── analyze.py  # request/response models
│   │       │   └── hex.py      # hex cell schema
│   │       ├── services/
│   │       │   └── osm_query.py # PostGIS queries
│   │       └── scorers/
│   │           ├── __init__.py
│   │           └── rule_based.py # Phase 1 scorer
│   │       └── tests/
│   │           ├── test_scorers.py
│   │           └── test_analyze.py
│   │
│   ├── annotator/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml      # depends on common
│   │   └── app/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── static/
│   │       │   ├── index.html  # annotator UI
│   │       │   └── app.js
│   │       └── routers/
│   │           ├── spots.py    # CRUD for annotations
│   │           └── health.py
│   │
│   └── frontend/
│       ├── Dockerfile
│       ├── nginx.conf
│       └── index.html          # Leaflet map UI
│
├── scripts/
│   └── osm-loader/
│       ├── Dockerfile          # osm2pgsql + wget
│       └── entrypoint.sh       # download + load logic
│
└── docs/
    └── SCOPE.md
```

## Services (docker-compose)

- **postgis** — Postgres 16 + PostGIS + h3-pg
- **osm-loader** — one-shot, depends on postgis
- **api** — FastAPI on port 8000
- **annotator** — FastAPI + static UI on port 8001
- **frontend** — nginx on port 8080

## Key Decisions

| Concern | Decision | Rationale |
|---|---|---|
| Repo structure | Monorepo with `services/` subdirectories | Keeps orchestration simple |
| Dependency management | uv workspaces | Shared `common/` package, no manual copy steps |
| Frontend | Leaflet + vanilla JS, single `index.html` | Lightweight, no build step for v1 |
| DB migrations | Centralized `db/` directory | Both services share the same Postgres |
| OSM loader | Dockerfile with osm2pgsql + entrypoint script | All dependencies available in container |
| API routers | Flat structure (`routers/analyze.py`, `routers/health.py`) | Simple and explicit |
| Scorer logic | Inside `services/api/app/scorers/` | Only the API needs it for Phase 1 |
| Annotator | Separate FastAPI service | Clean separation of concerns |
| Testing | pytest | Standard, great async support, fixtures |
