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

# Load OSM data from a local PBF file (recommended for development)
# First, place your city's .osm.pbf file in the data/ directory
make load-local OSM_LOCAL_FILE=city.osm.pbf
```

### Local PBF Workflow (Recommended for Development)

For faster development cycles, you can store the OSM PBF file locally instead of downloading it every time:

1. **Download the PBF file once** (from any source) and place it in the `data/` directory:
   ```bash
   mkdir -p data
   wget -O data/city.osm.pbf "$OSM_URL"
   # Or download from Geofabrik, BBBike, etc.
   ```

2. **Load from the local file** — near-instant, no network download:
   ```bash
   make load-local OSM_LOCAL_FILE=city.osm.pbf
   ```

3. **Subsequent loads** are fast because the idempotency check skips re-importing the same data.

The `data/` directory is git-ignored, so PBF files won't be tracked. You can switch cities by placing different `.osm.pbf` files in `data/` and changing the `OSM_LOCAL_FILE` value.

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
