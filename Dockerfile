# Python is pinned to 3.11 (the newest slim available) ON PURPOSE. The exploit relies
# on PSK TLS with a BINARY psk identity. Python 3.12 removed ssl.wrap_socket() and, more
# fundamentally, CPython 3.12+ enforces UTF-8 psk identities in _ssl.c (native PSK
# callbacks and sslpsk3 2.x both reject Tuya's binary identity before our code runs).
# sslpsk3 1.1.1 on Python <=3.11 passes the identity as raw bytes, which is required.
FROM python:3.11-slim AS base

# All work now happens inside the container, including scanning for and joining the
# device's WiFi AP, hosting the cloudcutter AP, DHCP/DNS/MQTT and the exploit itself.
# The WiFi adapter is moved into this container's network namespace by the launcher,
# so every wireless tool below drives the adapter directly (no host NetworkManager).
#
# 'apt-get update' is required: the slim base image ships with the package index
# removed, so an install cannot resolve packages without it. It is combined with the
# install into a single RUN layer, so Docker caches it and only re-runs this step when
# this line itself changes - not on every build.
#
# Only the packages actually used are installed:
#   build-essential, libssl-dev  - build the sslpsk3 C extension during pip install
#   iproute2 (ip, ss)            - interface config and port checks
#   iw, rfkill, wpasupplicant    - scan/join the device AP
#   isc-dhcp-client (dhclient)   - obtain a lease from the device AP
#   hostapd, dnsmasq, mosquitto  - host the cloudcutterflash AP / DHCP+DNS / MQTT
#   procps (pkill, ps)           - tear down background wifi processes
#   ncurses-bin, ncurses-term    - infocmp + putty terminfo for clean prompts
RUN apt-get -qq update \
    && apt-get install -qy --no-install-recommends \
        build-essential \
        libssl-dev \
        iproute2 \
        iw \
        rfkill \
        wpasupplicant \
        hostapd \
        dnsmasq \
        mosquitto \
        isc-dhcp-client \
        procps \
        ncurses-bin \
        ncurses-term \
    && rm -rf /var/lib/apt/lists/*

FROM base AS python-deps

COPY src/requirements.txt /src/
RUN pip install --no-cache-dir -r /src/requirements.txt

FROM python-deps AS cloudcutter

COPY src /src

# Normalize shell scripts to LF. If the build context was checked out / copied on a
# system that uses CRLF line endings (e.g. Windows, or git with autocrlf), the shells
# inside the container would otherwise fail with errors like "$'\r': command not found".
RUN find /src -type f -name '*.sh' -exec sed -i 's/\r$//' {} +

WORKDIR /src
