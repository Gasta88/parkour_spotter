# Parkour Spotter

A platform for analyzing and annotating parkour spots using OpenStreetMap data and H3 hexagonal grid indexing.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- uv (Python package manager)

### Development

```bash
# Start all services
make up

# Run tests
make test

# Run linter
make lint

# View logs
make logs

# Stop all services
make down

# Load OSM data (one-time)
make load-osm
```

### Services

| Service     | Port | Description                    |
|-------------|------|--------------------------------|
| postgis     | 5432 | PostgreSQL with PostGIS        |
| api         | 8000 | FastAPI backend for analysis   |
| annotator   | 8001 | FastAPI annotation UI backend  |
| frontend    | 8080 | Leaflet map frontend           |
| osm-loader  | -    | One-shot OSM data loader       |

## Project Structure

```
parkour_spotter/
├── common/              # Shared Python package
├── services/
│   ├── api/            # Analysis API service
│   ├── annotator/      # Annotation UI service
│   └── frontend/       # Leaflet map frontend
├── scripts/
│   └── osm-loader/     # OSM data loading script
└── docs/               # Documentation
```

## API Endpoints

### Analysis API (port 8000)

- `GET /health` - Health check
- `POST /analyze` - Analyze area for parkour spots

### Annotator API (port 8001)

- `GET /health` - Health check
- `GET /spots` - List annotation spots
- `POST /spots` - Create annotation

## License

MIT
