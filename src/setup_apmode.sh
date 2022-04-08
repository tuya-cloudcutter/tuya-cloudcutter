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
	--log-dhcp \
	--log-queries \
	--log-facility=/work/logs/dnsmasq.log \
	--dhcp-range=10.42.42.10,10.42.42.40,12h \
	--address=/#/${GATEWAY} -x $(pwd)/dnsmasq.pid

mkdir /run/mosquitto
chown mosquitto /run/mosquitto
echo -e "listener 1883 0.0.0.0\nallow_anonymous true\n" >> /etc/mosquitto/mosquitto.conf
/usr/sbin/mosquitto -d -c /etc/mosquitto/mosquitto.conf

# Fixes WiFi softblock issues
rfkill unblock all

# Run in 802.11g on fixed chan 1 for consistency across setups
printf "ssid=cloudcutter-flash\nchannel=1\nhw_mode=g\nlogger_stdout=-1\nlogger_stdout_level=4\ninterface=$WLAN" | hostapd /dev/stdin -P $(pwd)/hostapd.pid -B -dd -t -f /work/logs/hostapd.log
