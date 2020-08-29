FROM        python:3.8-alpine

ENV         LANG C.UTF-8

RUN         apk update \
            && apk add --virtual build-deps gcc g++ musl-dev python3 python3-dev autoconf automake linux-headers make libffi-dev \
            && apk add --no-cache bash zip

RUN         mkdir -p /opt/async/app

WORKDIR     /opt/async/app

ADD         requirements.txt /opt/async/app/
RUN         pip install --no-cache-dir -r /opt/async/app/requirements.txt

RUN         apk del --purge build-deps \
            && rm -rf /root/.cache /tmp/*

ADD         . /opt/async/app