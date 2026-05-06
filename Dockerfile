FROM python:3.9.18-slim-bullseye AS base

RUN apt-get -qq update && apt-get install -qy --no-install-recommends git hostapd rfkill dnsmasq build-essential libssl-dev iproute2 mosquitto iw fzf

FROM base AS python-deps

RUN pip install --upgrade pipenv

COPY src/Pipfile /src/
COPY src/Pipfile.lock /src/
RUN cd /src && PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM python-deps AS cloudcutter

COPY src /src

WORKDIR /src
