# syntax=docker/dockerfile:1
FROM ubuntu:20.04

ARG APT_MIRROR

ENV HOME="/root"
WORKDIR /root

# use apt mirror only if provided
RUN test ! -z "$APT_MIRROR" && \
    mv /etc/apt/sources.list /etc/apt/sources.list.bak && \
    echo "deb $APT_MIRROR focal main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb-src $APT_MIRROR focal main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb $APT_MIRROR focal-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src $APT_MIRROR focal-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb $APT_MIRROR focal-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src $APT_MIRROR focal-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb $APT_MIRROR focal-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src $APT_MIRROR focal-security main restricted universe multiverse" >> /etc/apt/sources.list || :

# install apt dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends python3-dev python3-pip curl git vim && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip wheel --no-cache-dir&& \
    pip3 install git+https://github.com/joint-online-judge/elephant@master#egg=joj-elephant --no-cache-dir

ARG PYPI_MIRROR

RUN test ! -z "$PYPI_MIRROR" && pip config set global.index-url $PYPI_MIRROR || :

COPY requirements.txt /root/
RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r requirements.txt

COPY . /root
RUN --mount=type=cache,target=/root/.cache/pip pip3 install .

ENV HOST="localhost" \
    PORT=34765 \
    OAUTH_JACCOUNT=true \
    OAUTH_JACCOUNT_ID="" \
    OAUTH_JACCOUNT_SECRET="" \
    JWT_SECRET="" \
    DSN="" \
    TRACES_SAMPLE_RATE=0

EXPOSE $PORT

CMD python3 -m joj.horse
