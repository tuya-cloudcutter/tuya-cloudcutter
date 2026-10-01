#!/usr/bin/env bash
#
# In-container workflow for tuya-cloudcutter.
#
# Everything that used to run on the host (adapter detection, scanning for and
# joining the Tuya device AP, safety checks, and running the exploit) now runs
# here, inside the container's own network namespace.  The physical WiFi adapter
# has been moved into this namespace by the launcher (tuya-cloudcutter.sh).
#
# Configuration arrives entirely through environment variables set by the launcher:
#   METHOD_DETACH, METHOD_FLASH, PROFILE, FIRMWARE, FLASH_TIMEOUT, VERBOSE_OUTPUT,
#   DEVICEID, LOCALKEY, AUTHKEY, PSKKEY, UUID, OVERRIDE_AP_SSID, DISABLE_RESCAN,
#   RESETNM, HAVE_SSID, SSID, SSID_PASS, PHY

set -o pipefail

# Suppress blessed's XTGETTCAP terminal probe (used by inquirer's menus).
#
# blessed (>=~1.21, a dependency of inquirer - still current in 1.50) probes the
# terminal at init by writing XTGETTCAP DCS sequences (ESC P + q ...). Terminals that
# do not implement XTGETTCAP, such as PuTTY, print the raw payload as visible text
# ("+q544e+q524742...") AND the probe blocks for its full ~5s timeout waiting for a
# reply that never comes. This is a blessed behaviour, not a TERM/terminfo issue, so no
# TERM value fixes it (and inquirer 3.4.1 is already the newest release).
#
# blessed skips the probe entirely when ANSICON is set (its own built-in opt-out, kept
# for the ansicon/ConEmu terminals). Setting it here is harmless elsewhere - on Linux
# colorama ignores ANSICON - and it both removes the garbage and the 5s stall.
export ANSICON=1

# Pick a terminal type that exists in the image and matches the client reasonably.
# (Only affects rendering now that the probe is disabled above.)
_pick_term() {
    local candidate
    for candidate in "${CLOUDCUTTER_TERM:-}" putty-256color putty xterm; do
        [ -z "${candidate}" ] && continue
        if infocmp "${candidate}" >/dev/null 2>&1; then
            echo "${candidate}"
            return 0
        fi
    done
    echo "xterm"
}
export TERM="$(_pick_term)"

cd /src || exit 1

WPA_CONF="/tmp/wpa_supplicant-cloudcutter.conf"
AP_MATCHED_NAME=""
AP_CONNECTED_ENDING=""
AP_GATEWAY=""

run_python() {
    python3 "$@"
}

run_helper_script() {
    if [ -f "/work/scripts/${1}.sh" ]; then
        echo "Running helper script '${1}'"
        source "/work/scripts/${1}.sh"
    fi
}

# ---------------------------------------------------------------------------
# Locate the WiFi interface that lives on our phy.  Only our adapter was moved
# into this namespace, so there is exactly one wireless interface here.  If the
# phy arrived without a netdev, create one.
# ---------------------------------------------------------------------------
find_wifi_interface() {
    local iface
    iface=$(iw dev 2>/dev/null | awk '/Interface/ {print $2; exit}')
    if [ -z "${iface}" ]; then
        if [ -n "${PHY}" ]; then
            iw phy "${PHY}" interface add wlan0 type managed >/dev/null 2>&1
            iface="wlan0"
        fi
    fi
    echo "${iface}"
}

# Wait until the adapter has been handed to us (the launcher moves it in shortly
# after starting the container).
echo "Waiting for WiFi adapter to appear inside the container..."
for _ in $(seq 1 30); do
    WIFI_ADAPTER=$(find_wifi_interface)
    [ -n "${WIFI_ADAPTER}" ] && break
    sleep 1
done

if [ -z "${WIFI_ADAPTER}" ]; then
    echo "[!] No WiFi interface is available inside the container."
    echo "    The adapter may not have been moved into the container namespace correctly."
    exit 1
fi

echo "Using WiFi adapter: ${WIFI_ADAPTER}"
rfkill unblock all >/dev/null 2>&1
ip link set "${WIFI_ADAPTER}" up >/dev/null 2>&1

# Warn (do not hard-stop) if AP mode is not advertised by the adapter.
if ! iw phy "${PHY}" info 2>/dev/null | grep -A20 "Supported interface modes" | grep -qw "AP"; then
    echo "[!] WARNING: adapter does not appear to advertise AP mode support."
    echo "AP support is mandatory for tuya-cloudcutter to work."
    read -n 1 -s -r -p "Press any key to continue, or CTRL+C to exit"
    echo ""
fi

if [ "${RESETNM}" == "true" ]; then
    echo "Wiping any saved WiFi state"
    rm -f "${WPA_CONF}"
    pkill -f "wpa_supplicant.*${WIFI_ADAPTER}" >/dev/null 2>&1
fi

# ---------------------------------------------------------------------------
# WiFi client helpers.
# ---------------------------------------------------------------------------
disconnect_wifi() {
    pkill -f "wpa_supplicant.*${WIFI_ADAPTER}" >/dev/null 2>&1
    pkill -f "dhclient.*${WIFI_ADAPTER}" >/dev/null 2>&1
    # Explicitly drop any station association + keys. Killing wpa_supplicant does not
    # always deauthenticate, and a lingering association later blocks hostapd AP mode.
    iw dev "${WIFI_ADAPTER}" disconnect >/dev/null 2>&1
    ip addr flush dev "${WIFI_ADAPTER}" >/dev/null 2>&1
}

# Scan and return the SSIDs of matching OPEN access points, strongest first.
#
# The second argument selects how results are sourced:
#   fresh="" (default) - a normal scan that may return cached results. Used for the first
#       connect, where the device AP is already up: cache accumulates across sweeps so a
#       present SSID is matched reliably and immediately.
#   fresh="1"          - 'scan flush' clears the cache before every scan so ONLY APs
#       broadcasting right now are returned. Used after the exploit: this guarantees a
#       stale cached SSID (the pre-exploit AP that has since rebooted away) can never be
#       matched, even though it may still sit in the cache for ~30s.
scan_for_ap() {
    local regex="$1"
    local fresh="$2"
    ip link set "${WIFI_ADAPTER}" up >/dev/null 2>&1

    local scan_args="scan"
    [ "${fresh}" == "1" ] && scan_args="scan flush"

    # Parse `iw scan` into per-BSS blocks, keeping only open networks (no RSN/WPA
    # information elements and no Privacy capability bit) whose SSID matches.
    # shellcheck disable=SC2086
    iw dev "${WIFI_ADAPTER}" ${scan_args} 2>/dev/null | awk -v re="${regex}" '
        function flush() { if (inbss && open && ssid ~ re) print ssid }
        /^BSS /                        { flush(); inbss=1; open=1; ssid=""; next }
        /^[[:space:]]*capability:/     { if ($0 ~ /Privacy/) open=0; next }
        /^[[:space:]]*RSN:/            { open=0; next }
        /^[[:space:]]*WPA:/            { open=0; next }
        /^[[:space:]]*SSID: /          { ssid=substr($0, index($0, ": ") + 2); next }
        END                            { flush() }
    '
}

wifi_connect() {
    local fresh="$1"   # "1" => flush the scan cache every scan (post-exploit); else cached
    local FIRST_RUN=true
    local i
    for i in $(seq 1 5); do
        AP_MATCHED_NAME=""
        disconnect_wifi
        sleep 1
        ip link set "${WIFI_ADAPTER}" up

        local SSID_REGEX="-[A-F0-9]{4}$"
        if [ "${OVERRIDE_AP_SSID}" != "" ]; then
            SSID_REGEX="${OVERRIDE_AP_SSID}$"
        fi
        if [ "${AP_CONNECTED_ENDING}" != "" ]; then
            SSID_REGEX="${AP_CONNECTED_ENDING}$"
        fi

        while [ "${AP_MATCHED_NAME}" == "" ]; do
            if [ "${FIRST_RUN}" == true ]; then
                local SCAN_MESSAGE="Scanning for open Tuya SmartLife AP"
                if [ "${OVERRIDE_AP_SSID}" != "" ]; then
                    SCAN_MESSAGE="${SCAN_MESSAGE} ${OVERRIDE_AP_SSID}"
                fi
                echo "${SCAN_MESSAGE}"
                FIRST_RUN=false
            else
                echo -n "."
            fi
            AP_MATCHED_NAME=$(scan_for_ap "${SSID_REGEX}" "${fresh}" | head -n1)
            [ "${AP_MATCHED_NAME}" == "" ] && sleep 2
        done

        echo -e "\nFound access point name: \"${AP_MATCHED_NAME}\", trying to connect..."

        # Build an open-network wpa_supplicant config and associate.
        cat > "${WPA_CONF}" <<-EOF
		network={
		    ssid="${AP_MATCHED_NAME}"
		    key_mgmt=NONE
		    scan_ssid=1
		}
		EOF

        local WPA_LOG="/tmp/wpa_supplicant-cloudcutter.log"
        : > "${WPA_LOG}"
        AP_GATEWAY=""

        if ! wpa_supplicant -B -i "${WIFI_ADAPTER}" -c "${WPA_CONF}" -Dnl80211 -f "${WPA_LOG}" >/dev/null 2>&1; then
            echo ""
            echo "[!] wpa_supplicant failed to start on ${WIFI_ADAPTER}."
            [ "${VERBOSE_OUTPUT}" == "true" ] && cat "${WPA_LOG}"
        else
            # Wait for the adapter to actually associate before requesting a lease.
            local associated="false"
            local s
            for s in $(seq 1 15); do
                if iw dev "${WIFI_ADAPTER}" link 2>/dev/null | grep -qi "Connected to"; then
                    associated="true"
                    break
                fi
                sleep 1
            done

            if [ "${associated}" != "true" ]; then
                echo ""
                echo "[!] Could not associate with \"${AP_MATCHED_NAME}\" within 15s."
                [ "${VERBOSE_OUTPUT}" == "true" ] && tail -n 20 "${WPA_LOG}"
            else
                # Request a DHCP lease from the device.
                ip addr flush dev "${WIFI_ADAPTER}" >/dev/null 2>&1
                if [ "${VERBOSE_OUTPUT}" == "true" ]; then
                    timeout 30 dhclient -1 -v "${WIFI_ADAPTER}" || echo "[!] dhclient did not obtain a lease."
                else
                    timeout 30 dhclient -1 "${WIFI_ADAPTER}" >/dev/null 2>&1
                fi

                # Determine the gateway the device handed us.
                #
                # The Tuya SoftAP's DHCP server typically does NOT send a router
                # (default route) option, so we cannot rely on `ip route default`.
                # Resolve the gateway in order of preference:
                #   1. an actual default route, if one was installed
                #   2. the DHCP server identifier from the lease file
                #   3. the .1 address of our own assigned /24 (the AP gateway)
                AP_GATEWAY=$(ip route show dev "${WIFI_ADAPTER}" 2>/dev/null | awk '/^default/ {print $3; exit}')

                if [ -z "${AP_GATEWAY}" ]; then
                    AP_GATEWAY=$(awk '/dhcp-server-identifier/ {gw=$NF} END {gsub(/;/, "", gw); print gw}' \
                        /var/lib/dhcp/dhclient.leases 2>/dev/null)
                fi

                if [ -z "${AP_GATEWAY}" ]; then
                    local ipaddr
                    ipaddr=$(ip -4 -o addr show dev "${WIFI_ADAPTER}" 2>/dev/null | awk '{print $4}' | head -n1 | cut -d/ -f1)
                    [ -n "${ipaddr}" ] && AP_GATEWAY="${ipaddr%.*}.1"
                fi

                AP_GATEWAY=$(echo "${AP_GATEWAY}" | grep -oE "192\.168\.(43|175|176)\.1")
            fi
        fi

        if [ "${AP_GATEWAY}" != "192.168.175.1" ] && [ "${AP_GATEWAY}" != "192.168.176.1" ] && [ "${AP_GATEWAY}" != "192.168.43.1" ]; then
            if [ "${AP_GATEWAY}" != "" ]; then
                echo "Expected AP gateway = 192.168.175.1/192.168.176.1/192.168.43.1 but got ${AP_GATEWAY}"
            fi
            if [ "${i}" == "5" ]; then
                echo "Error, could not connect to SSID."
                return 1
            fi
        else
            AP_CONNECTED_ENDING=${AP_MATCHED_NAME: -5}
            break
        fi
        sleep 1
    done

    echo "Connected to access point."
    return 0
}

# ---------------------------------------------------------------------------
# Choose an operation if one was not specified.
# ---------------------------------------------------------------------------
if [ ! "${METHOD_DETACH}" ] && [ ! "${METHOD_FLASH}" ]; then
    PS3="[?] Select your desired operation [1/2]: "
    select method in "Detach from the cloud and run Tuya firmware locally" "Flash 3rd Party Firmware"; do
        case $REPLY in
            1) METHOD_DETACH="true"; break;;
            2) METHOD_FLASH="true"; break;;
        esac
    done
fi

if [ "${METHOD_DETACH}" ] && [ ! "${HAVE_SSID}" ]; then
    echo "Detaching requires an SSID and Password, please enter each at the following prompt"
    echo "In order to provide secure logging, the values you type for your password will not show on screen"
    echo "If you make a mistake, you can run the detach process again"
    read -p "Please enter your SSID: " SSID
    read -p "Please enter your Password: "$'\n' -s SSID_PASS
    echo ""
fi

echo "Loading options, please wait..."

# ---------------------------------------------------------------------------
# Select the right device profile.
# ---------------------------------------------------------------------------
if [ "${PROFILE}" == "" ]; then
    if [ "${METHOD_FLASH}" ]; then
        run_python get_input.py -w /work -o /tmp/profile.txt choose-profile -f
    else
        run_python get_input.py -w /work -o /tmp/profile.txt choose-profile
    fi
else
    run_python get_input.py -w /work -o /tmp/profile.txt write-profile "${PROFILE}"
fi
if [ ! $? -eq 0 ]; then
    echo "Failed to choose a profile, please run this script again"
    exit 1
fi

PROFILE=$(cat /tmp/profile.txt)
rm -f /tmp/profile.txt

SLUGS=($(grep -oP '(?<="slug": ")[^"]*' "${PROFILE}"))
if ! [ -z "${SLUGS}" ]; then
    DEVICESLUG="${SLUGS[0]}"
    if [ "${#SLUGS[@]}" -eq 1 ]; then
        PROFILES_GREP=($(grep -A1 '"profiles": \[' "${PROFILE}" | tr -d "\t" | tr -d "\"" | tr -d " " | tr -d "["))
        PROFILESLUG="${PROFILES_GREP[1]}"
    else
        PROFILESLUG="${SLUGS[1]}"
    fi
fi
CHIP=$(grep -o '"chip": "[^"]*' "${PROFILE}" | grep -o '[^"]*$')

# ---------------------------------------------------------------------------
# Safety checks (ports, tooling) - now evaluated inside our isolated namespace.
# ---------------------------------------------------------------------------
run_helper_script "pre-safety-checks"
source /src/container/safety_checks.sh

# ---------------------------------------------------------------------------
# Select firmware when flashing.
# ---------------------------------------------------------------------------
if [ "${METHOD_FLASH}" ]; then
    if [ "${FIRMWARE}" == "" ]; then
        run_python get_input.py -w /work -o /tmp/firmware.txt choose-firmware -c "${CHIP}"
    else
        run_python get_input.py -w /work -o /tmp/firmware.txt validate-firmware-file "${FIRMWARE}" -c "${CHIP}"
    fi
    if [ ! $? -eq 0 ]; then
        exit 1
    fi
    FIRMWARE=$(cat /tmp/firmware.txt)
    rm -f /tmp/firmware.txt
fi

echo "Selected Device Slug: ${DEVICESLUG}"
echo "Selected Profile: ${PROFILESLUG}"
if ! [ -z "${FIRMWARE}" ]; then
    echo "Selected Firmware: ${FIRMWARE}"
fi

# ---------------------------------------------------------------------------
# Acquire the device configuration, either from supplied keys or via the exploit.
# ---------------------------------------------------------------------------
if ! [ -z "${AUTHKEY}" ] && ! [ -z "${UUID}" ]; then
    echo "Using AuthKey ${AUTHKEY} , UUID ${UUID}"
    if ! [ -z "${DEVICEID}" ] && ! [ -z "${LOCALKEY}" ]; then
        echo "Using DeviceId ${DEVICEID} and LocalKey ${LOCALKEY}"
    fi
    echo "Writing deviceconfig file..."
    OUTPUT=$(run_python -m cloudcutter write_deviceconfig "${PROFILE}" "${VERBOSE_OUTPUT}" --deviceid "${DEVICEID}" --localkey "${LOCALKEY}" --authkey "${AUTHKEY}" --uuid "${UUID}" --pskkey "${PSKKEY}")
else
    echo ""
    echo "================================================================================"
    echo "Place your device in AP (slow blink) mode.  This can usually be accomplished by either:"
    echo "Power cycling off/on - 3 times and wait for the device to fast-blink, then repeat 3 more times.  Some devices need 4 or 5 times on each side of the pause"
    echo "Long press the power/reset button on the device until it starts fast-blinking, then release, and then hold the power/reset button again until the device starts slow-blinking."
    echo "See https://support.tuya.com/en/help/_detail/K9hut3w10nby8 for more information."
    echo "================================================================================"
    echo ""
    run_helper_script "pre-wifi-exploit"
    wifi_connect
    if [ ! $? -eq 0 ]; then
        echo "Failed to connect, please run this script again"
        exit 1
    fi

    echo "Waiting 1 sec to allow device to set itself up..."
    sleep 1
    echo "Running initial exploit toolchain..."
    if ! [ -z "${DEVICEID}" ] && ! [ -z "${LOCALKEY}" ]; then
        echo "Using DeviceId ${DEVICEID} and LocalKey ${LOCALKEY}"
    fi
    OUTPUT=$(run_python -m cloudcutter exploit_device "${PROFILE}" "${VERBOSE_OUTPUT}" --deviceid "${DEVICEID}" --localkey "${LOCALKEY}" --victim-ip "${AP_GATEWAY}")
fi

RESULT=$?
echo "${OUTPUT}"
if [ ! $RESULT -eq 0 ]; then
    echo "Oh no, something went wrong with running the exploit! Try again I guess..."
    exit 1
fi
CONFIG_DIR=$(echo "${OUTPUT}" | grep "output=" | awk -F '=' '{print $2}' | sed -e 's/\r//')
echo "Saved device config in ${CONFIG_DIR}"

# ---------------------------------------------------------------------------
# Reconnect so the device will later join our hostapd AP.
# ---------------------------------------------------------------------------
echo ""
echo "================================================================================"
echo "Power cycle and place your device in AP (slow blink) mode again.  This can usually be accomplished by either:"
echo "Power cycling off/on - 3 times and wait for the device to fast-blink, then repeat 3 more times.  Some devices need 4 or 5 times on each side of the pause"
echo "Long press the power/reset button on the device until it starts fast-blinking, then releasing, and then holding the power/reset button again until the device starts slow-blinking."
echo "See https://support.tuya.com/en/help/_detail/K9hut3w10nby8 for more information."
echo "================================================================================"
echo ""

if [ "${CHIP^^}" == "RTL8720CF" ] || [ "${CHIP^^}" == "RTL8710BN" ]; then
    echo "${CHIP^^} *MUST* be rebooted before we even begin the next scan or you will receive false-positives about the status of the device."
    echo ""
    read -n 1 -s -r -p "Press any key to confirm you have completed power cycling the device and continue."
    echo ""
    echo "Continuing..."
fi

run_helper_script "pre-wifi-config"
# The device has just rebooted into its post-exploit SSID. Scan with cache-flush on every
# sweep (fresh=1) so a stale entry for the old, no-longer-broadcasting SSID can never be
# matched here - only an AP that is actually broadcasting right now will be picked up.
wifi_connect 1
if [ ! $? -eq 0 ]; then
    echo "Failed to connect, please run this script again"
    exit 1
fi

# If the AP prefix did not change, the exploit was not successful.
if [[ $AP_MATCHED_NAME != A-* ]] && [ -z "${AUTHKEY}" ]; then
    echo "================================================================================"
    echo "[!] The profile you selected did not result in a successful exploit."
    echo "================================================================================"
    exit 1
fi

echo "Device is connecting to 'cloudcutterflash' access point. Passphrase for the AP is 'abcdabcd' (without ')"
OUTPUT=$(run_python -m cloudcutter configure_wifi "cloudcutterflash" "abcdabcd" "${VERBOSE_OUTPUT}" --victim-ip "${AP_GATEWAY}")
RESULT=$?
echo "${OUTPUT}"
if [ ! $RESULT -eq 0 ]; then
    echo "Oh no, something went wrong with making the device connect to our hostapd AP! Try again I guess..."
    exit 1
fi

# ---------------------------------------------------------------------------
# Host the cloudcutterflash AP and perform the requested action.
# ---------------------------------------------------------------------------
# Tear down the client connection before switching the adapter into AP mode.
disconnect_wifi

if [ "${METHOD_DETACH}" ]; then
    echo "Cutting device off from cloud..."
    echo ""
    echo "================================================================================"
    echo "Wait for up to 10-120 seconds for the device to connect to 'cloudcutterflash'. This script will then show the activation requests sent by the device, and tell you whether local activation was successful."
    echo "================================================================================"
    echo ""
    bash /src/setup_apmode.sh "${WIFI_ADAPTER}" "${VERBOSE_OUTPUT}"
    run_python -m cloudcutter configure_local_device --ssid "${SSID}" --password "${SSID_PASS}" "${PROFILE}" "/work/device-profiles/schema" "${CONFIG_DIR}" "${FLASH_TIMEOUT}" "${VERBOSE_OUTPUT}"
    if [ ! $? -eq 0 ]; then
        echo "Oh no, something went wrong with detaching from the cloud! Try again I guess..."
        if [ ! "${VERBOSE_OUTPUT}" ]; then
            echo "If you need to report an issue, please run with the -v flag and supply the full log of that attempt."
        fi
        exit 1
    fi
fi

if [ "${METHOD_FLASH}" ]; then
    echo "Flashing custom firmware..."
    echo ""
    echo "================================================================================"
    echo "Wait for up to 10-120 seconds for the device to connect to 'cloudcutterflash'. This script will then show the firmware upgrade requests sent by the device."
    echo "================================================================================"
    echo ""
    bash /src/setup_apmode.sh "${WIFI_ADAPTER}" "${VERBOSE_OUTPUT}"
    run_python -m cloudcutter update_firmware "${PROFILE}" "/work/device-profiles/schema" "${CONFIG_DIR}" "/work/custom-firmware/" "${FIRMWARE}" "${FLASH_TIMEOUT}" "${VERBOSE_OUTPUT}"
    if [ ! $? -eq 0 ]; then
        echo "Oh no, something went wrong with updating firmware! Try again I guess..."
        if [ ! "${VERBOSE_OUTPUT}" ]; then
            echo "If you need to report an issue, please run with the -v flag and supply the full log of that attempt."
        fi
        exit 1
    fi
fi

echo "Done."
