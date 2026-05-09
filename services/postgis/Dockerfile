FROM postgis/postgis:16-3.4

# Install h3-pg extension (PostgreSQL bindings for Uber's H3)
# Available via apt on Debian-based PostGIS images (Ubuntu 22.04+)
RUN apt-get update && \
    apt-get install -y postgresql-16-h3 && \
    rm -rf /var/lib/apt/lists/*
