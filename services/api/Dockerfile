FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY common/pyproject.toml ./common/pyproject.toml
COPY common/common ./common/common

RUN uv pip install --system -e ./common

COPY services/api/pyproject.toml .

RUN uv pip install --system .

COPY services/api/app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
