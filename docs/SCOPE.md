# Parkour Spotter

> A geospatial service that finds promising outdoor parkour training spots in a given area, by scoring built-environment features extracted from OpenStreetMap.

## Problem

Finding good outdoor parkour spots requires scanning satellite and street imagery for specific combinations of features — low walls, stair sets, rails, gaps, ledges, varied paved surfaces. Doing this manually over a city-sized area is tedious. This project automates the candidate-discovery step: given a center point and a radius, it returns ranked areas worth visiting in person.

## What it does

The user opens a map interface, enters a coordinate and radius (up to 10 km), and the system analyses the area and highlights scored hexagonal cells on the map. Clicking a cell opens Google Street View at that location for visual confirmation.

## UX flow

1. User opens the web interface and sees an empty map.
2. User pastes a coordinate (or clicks on the map) and sets a radius (max 10 km).
3. User clicks **Analyse**.
4. Backend scores all H3 hexagons within the radius; response returns within ~5 seconds for typical queries.
5. Hexagons are rendered as a heatmap — colour intensity reflects parkour-suitability score.
6. Clicking a hexagon opens Google Street View at its centroid in a new tab.

## Architecture

Five containerised services orchestrated with Docker Compose:

- **postgis** — Postgres with the PostGIS and H3 extensions; persistent volume holds the OSM data and annotations.
- **osm-loader** — one-shot container that downloads a Geofabrik regional extract and loads it via `osm2pgsql`. Idempotent; can be re-run manually to refresh the snapshot.
- **api** — FastAPI service exposing `POST /analyze`. Stateless. Computes scores per H3 cell within the requested area and returns GeoJSON.
- **annotator** — separate FastAPI + static UI for labelling spots. Reads OSM features, writes labels to the `spots_annotated` table. Used to generate training data for Phase 2.
- **frontend** — nginx serving the static map UI (Leaflet or MapLibre, vanilla JS).

The whole stack runs on a developer laptop or a €5/month VPS without modification.

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Geospatial DB | PostGIS + h3-pg | Standard for spatial queries; H3 extension lets the DB do hex aggregation natively |
| OSM ingestion | osm2pgsql + Geofabrik extracts | Geofabrik publishes free, regularly-updated regional extracts; osm2pgsql is the canonical loader |
| Backend | Python + FastAPI | Fast to write, async-friendly, plays well with PostGIS via SQLAlchemy/asyncpg |
| Frontend | Leaflet (or MapLibre) + vanilla JS | The interaction is simple; a framework would be overhead |
| Containerisation | Docker Compose | Right level of abstraction for this scale; portable to any VPS |
| Migrations | Alembic | Schema changes in git; clean bootstrap on fresh clones |
| Dependency management | uv with lockfile | Reproducible Python envs |
| Model (Phase 2) | XGBoost on engineered features | Strong baseline, interpretable, fast to train and serve |

## Phased roadmap

**Phase 1 — rule-based scorer (MVP)**

Hand-crafted rules over OSM tags. Score each H3 cell at resolution 11 by the presence and density of features such as `barrier=wall`, `highway=steps`, `leisure=playground`, `amenity=parking` (multi-level), open paved areas, and the absence of `access=private`. Simple weighted sum, normalised to 0–1.

This gives a working end-to-end system on day one, and serves as the candidate generator for the annotation tool.

**Phase 2 — learned scorer**

Once ~300+ labels are collected via the annotator, train an XGBoost classifier on engineered features (counts and densities of OSM tags within and around each cell). Compare against the rule-based baseline; ship whichever performs better. The README will document both, with the comparison itself as a deliverable.

**Future work (explicitly out of scope for v1)**

- Street-level CV via Mapillary.
- Coverage outside the chosen pilot region.
- User accounts, saved searches, sharing.
- Mobile app.
- Real-time OSM updates (weekly snapshot is fine).

## Reproducibility commitments

- Pinned base image digests, pinned Python deps via lockfile, pinned OSM extract URL.
- OSM snapshot date stored in a `data_version` table; returned in API responses so scores are traceable to a data version.
- Seed annotations (~10–20 hand-labelled spots in the pilot region) committed to the repo so a fresh clone runs end-to-end with no manual labelling.
- Trained model artifacts (Phase 2) versioned separately from the api image; loaded as a mounted volume with a `metadata.json` capturing training data hash, feature list, and metrics.
- Single `make` interface: `make up`, `make load-osm`, `make annotate`, `make train`, `make test`.

## Pilot region

Veneto, Italy. Geofabrik extract is small (~200–400 MB compressed), fits comfortably on any dev machine, and matches the developer's location for ground-truth validation.

## Non-functional requirements

- A 10 km radius query returns within ~5 seconds on a 4-core / 8 GB machine.
- The full stack starts from a clean machine via `docker compose up`, with only Docker as a prerequisite.
- All external data dependencies are fetchable from public sources; no API keys required for v1.
- API logs request latency, candidate cell count, and score distribution per request.

## How to run

**First run (local):**

```bash
git clone <repo>
cd parkour-spotter
make up           # starts postgis, runs migrations
make load-osm     # downloads Veneto extract, loads into postgis (~10 min)
make seed         # loads seed annotations
# open http://localhost:8080
```

**Deploy to VPS:**

Same steps, on a Hetzner CX22 or equivalent. No code changes.

## Scaling notes

The single-VPS Docker Compose setup is appropriate for the project's scale and for portfolio purposes. If the project ever needs to scale beyond one machine, the natural progression is:

1. Compose on a single VPS — the default.
2. Compose with an external managed Postgres (Supabase, Hetzner managed Postgres) if the DB outgrows the box.
3. Container orchestration (Kubernetes, Nomad) only if multi-tenant or multi-region is needed.

Kubernetes is deliberately not used in v1 — it would be over-engineering at this scale.

## Open questions to resolve before building

- Which H3 resolution best matches a "parkour spot" footprint? Resolution 11 (~25 m edge) feels right but worth validating against a few labelled spots.
- Initial weights for the rule-based scorer — derive from intuition or from a small pilot annotation round?
- Frontend library: Leaflet (mature, simple) vs MapLibre (modern, vector tiles). Leaning Leaflet for v1.
