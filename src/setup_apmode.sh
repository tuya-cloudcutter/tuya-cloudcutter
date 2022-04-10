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
        --log-facility=/dev/stdout \
        --dhcp-range=10.42.42.10,10.42.42.40,12h \
        --address=/#/${GATEWAY} -x $(pwd)/dnsmasq.pid

mkdir /run/mosquitto
chown mosquitto /run/mosquitto
echo -e "listener 1883 0.0.0.0\nallow_anonymous true\n" >> /etc/mosquitto/mosquitto.conf
/usr/sbin/mosquitto -d -c /etc/mosquitto/mosquitto.conf

rfkill unblock wifi

# Set up hostapd with
# 1. 802.11n in 2.4GHz (hw_mode=g) - some devices scan for it
# 2. WPA2-PSK - some devices do not connect otherwise
# 3. Enforced WPA2 - same as above
hostapd /dev/stdin -P $(pwd)/hostapd.pid -B <<- EOF
ssid=cloudcutterflash
channel=1
logger_stdout_level=4
hw_mode=g
ieee80211n=1
wmm_enabled=1
interface=$WLAN
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_passphrase=abcdabcd
rsn_pairwise=CCMP
EOF

