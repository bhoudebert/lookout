# Lookout in one image: the API, the built dashboard and the scheduler. One data volume.
# Build:  docker build -t lookout .
# Run:    see deploy/docker-compose.yml and docs/guide/self-hosting.md

# Stage 1: the dashboard, built once.
FROM node:24-bookworm-slim AS dashboard
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

# Stage 2: what runs.
FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    LOOKOUT_CONFIG=/config/lookout.yaml \
    LOOKOUT_DATABASE=/data/lookout.db \
    LOOKOUT_DASHBOARD_DIR=/app/dashboard \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.1

WORKDIR /app
# Dependencies first, so a code change does not reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

COPY --from=dashboard /ui/dist /app/dashboard

RUN useradd --system --create-home --uid 10001 lookout \
    && mkdir -p /data /config \
    && chown -R lookout:lookout /data /app
USER lookout
VOLUME /data
EXPOSE 8899

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8899/api/health', timeout=4).status == 200 else 1)"

# `docker compose exec lookout lookout doctor` runs the checks inside.
CMD ["lookout", "serve", "--host", "0.0.0.0", "--port", "8899"]
