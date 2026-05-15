# Parkour Spotter

A platform for analyzing and annotating parkour spots using OpenStreetMap data and H3 hexagonal grid indexing.

## Project Structure

```
parkour_spotter/
├── common/              # Shared Python package (models, DB utils, H3 utils)
├── services/
│   ├── api/            # Analysis API service (port 8000)
│   ├── annotator/      # Annotation UI service (port 8001)
│   └── frontend/       # Leaflet map frontend (port 8080)
├── scripts/
│   ├── osm-loader/     # OSM data loading script
│   ├── init-db.sql     # Database initialization
│   └── seed-data.sql   # Seed data for development
├── data/               # Local OSM PBF files (git-ignored)
├── docker-compose.yml  # Service orchestration
├── Makefile            # Common dev commands
└── pyproject.toml      # Python workspace config
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- uv (Python package manager)

### Setup

```bash
# 1. Clone and configure
git clone <repository>
cp .env.example .env

# 2. Start all services
make up

# 3. Load OSM data (required before using the platform)
make load-local OSM_LOCAL_FILE=city.osm.pbf

# 4. Verify services are running
make logs
```

### Common Commands

```bash
make up              # Start all services
make down            # Stop all services
make restart         # Restart services
make test            # Run tests
make lint            # Lint and format check
make logs            # View all logs
make status          # Check database status
make clean           # Full clean (removes volumes)
```

## Getting OSM Data

### Option 1: Geofabrik (Recommended)

Geofabrik provides free OSM extracts for regions worldwide:

1. Visit [https://download.geofabrik.de/](https://download.geofabrik.de/)
2. Navigate to your region (e.g., Europe → Italy → Veneto)
3. Download the `.osm.pbf` file
4. Place it in the `data/` directory

```bash
mkdir -p data
wget -O data/padova.osm.pbf https://download.geofabrik.de/europe/italy/veneto/padova-latest.osm.pbf
```

### Option 2: BBBike

BBBike allows custom area extracts:

1. Visit [https://extract.bbbike.org/](https://extract.bbbike.org/)
2. Select your area on the map
3. Choose PBF format
4. Download and place in `data/` directory

### Option 3: Overpass Turbo

For small custom areas:

1. Visit [https://overpass-turbo.eu/](https://overpass-turbo.eu/)
2. Draw your area and export as PBF
3. Place in `data/` directory

### Loading OSM Data

```bash
# Load from local PBF file
make load-local OSM_LOCAL_FILE=city.osm.pbf

# Force reload (ignores idempotency check)
make load-osm-force

# Check loaded data status
make status
```

## Local Development

### Environment Setup

1. **Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` as needed (defaults work for most cases).

2. **Start services:**

```bash
make up
```

3. **Load OSM data:**

```bash
make load-local OSM_LOCAL_FILE=your_city.osm.pbf
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest services/api/app/tests/test_health.py
```

### Linting and Formatting

```bash
# Check lint and format
make lint

# Auto-fix issues
uv run ruff check . --fix

# Auto-format code
uv run ruff format .
```

### Viewing Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-annotator
make logs-frontend
make logs-db
```

### Database Access

```bash
# Shell into database
make shell-db

# Query loaded data
make status
```

### Switching Cities

To analyze a different city:

1. Download the new city's `.osm.pbf` file to `data/`
2. Update `OSM_LOCAL_FILE` in `.env`
3. Clean existing data: `make clean-osm`
4. Load new data: `make load-local OSM_LOCAL_FILE=new_city.osm.pbf`

### Service Ports

| Service     | Port | URL                      |
|-------------|------|--------------------------|
| postgis     | 5432 | localhost:5432           |
| api         | 8000 | http://localhost:8000    |
| annotator   | 8001 | http://localhost:8001    |
| frontend    | 8080 | http://localhost:8080    |

### API Endpoints

**Analysis API (port 8000)**

- `GET /health` - Health check
- `POST /analyze` - Analyze area for parkour spots

**Annotator API (port 8001)**

- `GET /health` - Health check
- `GET /spots` - List annotation spots
- `POST /spots` - Create annotation

## License

MIT
