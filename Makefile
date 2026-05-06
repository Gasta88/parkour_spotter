.PHONY: up down test lint load-osm load-osm-force status clean-osm switch-city seed clean logs

up:
	docker compose up -d

down:
	docker compose down

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

load-osm:
	docker compose up --build osm-loader

load-osm-force:
	FORCE_RELOAD=true docker compose up --build osm-loader

status:
	docker compose exec -T postgis psql -U parkour -d parkour -c "SELECT id, loaded_at, osm_source_url, file_size_mb, row_counts, load_duration_seconds, success FROM data_version ORDER BY loaded_at DESC LIMIT 1;"

clean-osm:
	docker compose exec -T postgis psql -U parkour -d parkour -c "TRUNCATE TABLE planet_osm_point CASCADE; TRUNCATE TABLE planet_osm_line CASCADE; TRUNCATE TABLE planet_osm_polygon CASCADE; TRUNCATE TABLE planet_osm_roads CASCADE; DROP MATERIALIZED VIEW IF EXISTS parkour_features;"

switch-city:
ifndef OSM_URL
	$(error OSM_URL is not set. Usage: make switch-city OSM_URL=<url>)
endif
	OSM_URL=$(OSM_URL) docker compose up --build osm-loader

seed:
	@echo "Database seeding not yet implemented"

clean:
	docker compose down -v
	docker system prune -f

logs:
	docker compose logs -f
