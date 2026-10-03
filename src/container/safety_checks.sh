#!/usr/bin/env bash
#
# Container-side safety checks.
#
# The exploit runs inside the container's own network namespace, so the required
# ports are essentially always free and there is no host firewall/AppArmor to fight
# with.  These checks are therefore mostly informational: confirm the tooling we
# rely on is present, and warn if something inside the namespace has already taken
# a port we need.

check_tooling () {
    local missing=""
    for tool in iw ip rfkill wpa_supplicant dhclient hostapd dnsmasq mosquitto; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing="${missing} ${tool}"
        fi
    done
    if [ -n "${missing}" ]; then
        echo "[!] Missing required tools inside the container:${missing}"
        echo "    The Docker image may be out of date - rebuild it and try again."
        exit 1
    fi
}

check_port () {
    local protocol="$1"
    local port="$2"
    local reason="$3"
    echo -n "Checking ${protocol^^} port $port... "
    if ss -lnH -A "$protocol" "sport = :$port" 2>/dev/null | grep -q .; then
        local process_name
        process_name=$(ss -lnpH -A "$protocol" "sport = :$port" 2>/dev/null | grep -Po '(?<=users:\(\(")[^"]+' | head -n1)
        echo "Occupied by ${process_name:-another process}."
        echo "Port $port is needed to $reason"
        echo "This is unexpected inside the container namespace; continuing anyway."
    else
        echo "Available."
    fi
}

echo ""
echo "Performing safety checks to make sure all required tooling and ports are available"
check_tooling
check_port udp 53 "resolve DNS queries"
check_port udp 67 "offer DHCP leases"
check_port tcp 80 "answer HTTP requests"
check_port tcp 443 "answer HTTPS requests"
check_port tcp 1883 "run MQTT"
check_port tcp 8886 "run MQTTS"
echo "Safety checks complete."
echo ""
