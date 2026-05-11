FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install uv

COPY common/pyproject.toml ./common/pyproject.toml
COPY common/common ./common/common

RUN uv pip install --system -e ./common

COPY common/alembic.ini ./common/alembic.ini
COPY common/alembic ./common/alembic

WORKDIR /app/common
