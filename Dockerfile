FROM debian:bullseye-slim

RUN apt-get -qq update && apt-get install -qy --no-install-recommends \
	git hostapd rfkill dnsmasq python3 python3-dev python3-pip build-essential \
    libssl-dev iproute2 mosquitto

RUN pip install --upgrade pipenv
ADD src /src
WORKDIR /src
RUN pipenv install
