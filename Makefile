.PHONY: up down test lint load-osm seed clean logs

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
	docker compose up osm-loader

seed:
	@echo "Database seeding not yet implemented"

clean:
	docker compose down -v
	docker system prune -f

logs:
	docker compose logs -f
