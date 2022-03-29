#!/usr/bin/env bash

GATEWAY=10.42.42.1
WLAN=${1:-UNKNOWN}

echo "Using WLAN adapter: ${WLAN}"

ip addr flush dev $WLAN
ip link set dev $WLAN down
ip addr add $GATEWAY/24 dev $WLAN
ip link set dev $WLAN up

dnsmasq --no-resolv --interface=$WLAN --bind-interfaces \
	--listen-address=$GATEWAY --except-interface=lo \
	--dhcp-range=10.42.42.10,10.42.42.40,12h \
	--address=/#/${GATEWAY} -x $(pwd)/dnsmasq.pid

/usr/sbin/mosquitto -d -c /etc/mosquitto/mosquitto.conf

printf "ssid=cloudcutter-flash\nchannel=1\nlogger_stdout_level=4\ninterface=$WLAN" | hostapd /dev/stdin -P $(pwd)/hostapd.pid -B