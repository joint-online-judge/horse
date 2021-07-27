# syntax=docker/dockerfile:1
FROM ubuntu:20.04

ENV HOME="/root"
WORKDIR /root

RUN --mount=type=cache,target=/var/cache/apt \
    mv /etc/apt/sources.list /etc/apt/sources.list.bak && \
    echo "deb http://mirrors.163.com/ubuntu/ focal main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb-src http://mirrors.163.com/ubuntu/ focal main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.163.com/ubuntu/ focal-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.163.com/ubuntu/ focal-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.163.com/ubuntu/ focal-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.163.com/ubuntu/ focal-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.163.com/ubuntu/ focal-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.163.com/ubuntu/ focal-security main restricted universe multiverse" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends python python3-dev python3-pip curl git vim && \
#    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


RUN pip3 install --upgrade pip wheel --no-cache-dir&& \
    pip3 install git+https://github.com/joint-online-judge/elephant@master#egg=joj-elephant --no-cache-dir

COPY requirements.txt /root/
RUN --mount=type=cache,target=/root/.cache/pip pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

COPY . /root
RUN --mount=type=cache,target=/root/.cache/pip pip3 install . -i https://pypi.tuna.tsinghua.edu.cn/simple/

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
