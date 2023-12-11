FROM python:3.9.18-slim-bullseye AS base

RUN apt-get -qq update && apt-get install -qy --no-install-recommends git hostapd rfkill dnsmasq build-essential libssl-dev iproute2 mosquitto

FROM base AS python-deps

RUN pip install --upgrade pipenv

COPY src/requirements.txt /src/
RUN cd /src && pip install -r requirements.txt

FROM python-deps AS cloudcutter

COPY src /src

WORKDIR /src
