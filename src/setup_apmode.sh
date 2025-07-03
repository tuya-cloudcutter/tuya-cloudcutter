#!/usr/bin/env bash

GATEWAY=10.42.42.1
WLAN=${1:-UNKNOWN}
VERBOSE_OUTPUT=${2:-"false"}

get_channel() {
        iw dev "$1" info 2>/dev/null | awk '/channel/ {if ($2 ~ /^[0-9]+$/) print $2}'
}
get_wiphy() {
        iw dev "$1" info | awk '/wiphy/ {print $2}'
}
get_ap_channel() {
        local iface="$1"
        local channel=$(get_channel "$iface" 2>/dev/null) 
        if [[ -n "$channel" ]]; then
                # Found channel directly from the wanted interface info
                echo "$channel"
                return 0
        fi

		# Find the "parent" interface i.e. the one for which this is an additional virtual interface
        # to get channel.
        local wiphy=$(get_wiphy "$iface") || return 1

        for other_iface in $(iw dev | awk '/Interface/ {print $2}'); do
                [[ "$other_iface" == "$iface" ]] && continue
                local other_wiphy=$(get_wiphy "$other_iface")
                if [[ "$other_wiphy" == "$wiphy" ]]; then
                        channel=$(get_channel "$other_iface")
                        if [[ -n "$channel" ]]; then
                                echo "$channel"
                                return 0
                        fi
                fi
        done

        echo "Unable to find channel for $iface"
        return 1
}

echo "Using WLAN adapter: ${WLAN}"

ip addr flush dev $WLAN
ip link set dev $WLAN down
ip addr add $GATEWAY/24 dev $WLAN
ip link set dev $WLAN up

LOG_OPTIONS=""
if [ "${VERBOSE_OUTPUT}" == "true" ]; then
        LOG_OPTIONS="--log-dhcp --log-queries --log-facility=/dev/stdout"
fi
dnsmasq --no-resolv --interface=$WLAN --bind-interfaces --listen-address=$GATEWAY --except-interface=lo --dhcp-range=10.42.42.10,10.42.42.40,12h --address=/#/${GATEWAY} -x $(pwd)/dnsmasq.pid $LOG_OPTIONS

mkdir /run/mosquitto
chown mosquitto /run/mosquitto
echo -e "listener 1883 0.0.0.0\nallow_anonymous true\n" >> /etc/mosquitto/mosquitto.conf
/usr/sbin/mosquitto -d -c /etc/mosquitto/mosquitto.conf

rfkill unblock wifi

# Set up hostapd with
# 1. 802.11n in 2.4GHz (hw_mode=g) - some devices scan for it
# 2. WPA2-PSK - some devices do not connect otherwise
# 3. Enforced WPA2 - same as above
# 4. Channel parsed from wlan device info or 1 as fallback
AP_CHANNEL=$(get_ap_channel "$WLAN")
if [[ $? -eq 0 ]]; then
        echo "Using hostapd channel $AP_CHANNEL parsed from wlan info."
else
        AP_CHANNEL="6"
        echo "Unable to get channel from wlan info. Using $AP_CHANNEL as fallback."
fi
echo "Waiting 5 seconds before starting access point on ${WLAN}"
for i in {1..5}; do
  sleep 1
  echo -n "."
done
echo
hostapd /dev/stdin -P $(pwd)/hostapd.pid -B <<- EOF
ssid=cloudcutterflash
channel=$AP_CHANNEL
logger_stdout_level=4
hw_mode=g
wmm_enabled=1
interface=$WLAN
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_passphrase=abcdabcd
rsn_pairwise=CCMP
EOF

echo "If your device gets stuck here with no progress after several (at least two) minutes, see https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/FAQ#my-device-gets-stuck-after-dhcp-what-can-i-do for additional steps"
