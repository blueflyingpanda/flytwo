FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --extra api --no-dev --no-install-project

COPY alembic.ini .
COPY migrations/ migrations/
COPY src/ .

ENV PYTHONPATH="/app/src"
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

# Run the API
CMD ["uvicorn", "src.api.api:app", "--host", "0.0.0.0", "--port", "8080"]
