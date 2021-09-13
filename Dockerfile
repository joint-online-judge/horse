# syntax=docker/dockerfile:1
FROM tiangolo/uvicorn-gunicorn:python3.8-slim

ENV HOME="/root"
WORKDIR /root

# install apt dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# install poetry
ARG PYPI_MIRROR
RUN if [[ ! -z "$PYPI_MIRROR" ]]; then pip config set global.index-url $PYPI_MIRROR; fi
RUN --mount=type=cache,target=/root/.cache/pip pip install poetry

# RUN poetry config virtualenvs.in-project true

# create virtualenv
ENV VIRTUAL_ENV=/root/.venv
RUN python3 -m virtualenv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install dependencies
# RUN pip install git+https://github.com/joint-online-judge/elephant@master#egg=joj-elephant --no-cache-dir
COPY pyproject.toml poetry.lock /root/
COPY joj/horse/__init__.py /root/joj/horse/
RUN --mount=type=cache,target=/root/.cache/pip poetry install --no-dev
COPY . /root
RUN --mount=type=cache,target=/root/.cache/pip poetry install --no-dev


#COPY requirements.txt setup.py setup.cfg README.md /root/
#RUN mkdir -p /root/joj/horse
#RUN --mount=type=cache,target=/root/.cache/pip PBR_VERSION=0.0.0 pip install .[test]

#COPY . /root
#RUN --mount=type=cache,target=/root/.cache/pip pip install .

ENV HOST="localhost" \
    PORT=34765 \
    OAUTH_JACCOUNT=true \
    OAUTH_JACCOUNT_ID="" \
    OAUTH_JACCOUNT_SECRET="" \
    JWT_SECRET="secret" \
    DSN="" \
    TRACES_SAMPLE_RATE=0

EXPOSE $PORT

CMD aerich upgrade && python3 -m joj.horse
