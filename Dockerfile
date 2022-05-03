# syntax=docker/dockerfile:1
FROM tiangolo/uvicorn-gunicorn:python3.8-slim

ENV HOME="/root"
WORKDIR /root

# install apt dependencies
ARG APT_MIRROR
RUN if [ -n "$APT_MIRROR" ]; then sed -i "s@http://deb.debian.org@$APT_MIRROR@g" /etc/apt/sources.list; fi
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends git rclone && \
    rm -rf /var/lib/apt/lists/*

# install poetry
ARG PYPI_MIRROR
RUN if [ -n "$PYPI_MIRROR" ]; then pip config set global.index-url $PYPI_MIRROR; fi
RUN --mount=type=cache,target=/root/.cache pip install poetry

# create virtualenv
ENV VIRTUAL_ENV=/root/.venv
RUN python3 -m virtualenv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install dependencies
ARG PYTEST
COPY pyproject.toml poetry.lock README.md /root/
COPY joj/horse/__init__.py /root/joj/horse/
RUN --mount=type=cache,target=/root/.cache if [ -n "$PYTEST" ]; then poetry install -E test; else poetry install --no-dev; fi
COPY . /root

ENV HOST="localhost" \
    PORT=34765 \
    JWT_SECRET="secret" \
    DSN="" \
    TRACES_SAMPLE_RATE=0

EXPOSE $PORT

CMD alembic upgrade head && python3 -m joj.horse
