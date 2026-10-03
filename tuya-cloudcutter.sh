#!/usr/bin/env bash
#
# Thin launcher for tuya-cloudcutter.
#
# This script no longer performs any of the actual work (scanning, connecting,
# safety checks, hosting the AP, or running the exploit).  Its only jobs are:
#   1. Parse the command line options.
#   2. Build the Docker image.
#   3. Move the requested WiFi adapter *fully* into the container's own network
#      namespace, so that everything wireless-related runs inside the container.
#   4. Hand control to the in-container workflow (src/container/run.sh).
#
# Because the adapter is moved into the container's namespace, a WiFi adapter
# MUST be supplied with -w.  It should be a stand-alone adapter that is not your
# primary source of networking (use ethernet for that), because it will disappear
# from the host for the duration of the run.

set -o pipefail

IMAGE_NAME="cloudcutter"      # docker image tag (build / run)
CONTAINER_NAME="cloudcutter"  # running container name (run --name / exec / inspect / rm)
FLASH_TIMEOUT=15

function getopts-extra () {
    declare i=1
    # if the next argument is not an option, then append it to array OPTARG
    while [[ ${OPTIND} -le $# && ${!OPTIND:0:1} != '-' ]]; do
        OPTARG[i]=${!OPTIND}
        let i++ OPTIND++
    done
}

while getopts "hrnt:vw:p:f:d:l:s::a:k:u:o:" flag; do
    case "$flag" in
        r)  RESETNM="true";;
        n)  DISABLE_RESCAN="true";;
        v)  VERBOSE_OUTPUT="true";;
        w)  WIFI_ADAPTER=${OPTARG};;
        p)  PROFILE=${OPTARG};;
        f)  FIRMWARE=${OPTARG}
            METHOD_FLASH="true"
        ;;
        t)  FLASH_TIMEOUT=${OPTARG};;
        d)  DEVICEID=${OPTARG};;
        l)  LOCALKEY=${OPTARG};;
        a)  AUTHKEY=${OPTARG};;
        k)  PSKKEY=${OPTARG};;
        u)  UUID=${OPTARG};;
        o)  OVERRIDE_AP_SSID=${OPTARG};;
        s)  getopts-extra "$@"
            METHOD_DETACH="true"
            HAVE_SSID="true"
            SSID_ARGS=( "${OPTARG[@]}" )
            SSID=${SSID_ARGS[0]}
            SSID_PASS=${SSID_ARGS[1]}
        ;;
        h)
            echo "usage: $0 [OPTION]..."
            echo "  -h                Show this message"
            echo "  -w TEXT           WiFi adapter name (default: wlan0 - it is passed fully into the container, and must exist)"
            echo "  -r                Reset saved WiFi state inside the container before running"
            echo "  -n                No Rescan (accepted for backwards compatibility)"
            echo "  -o TEXT           Override specific device AP name to connect to"
            echo "  -v                Verbose log output"
            echo "  -p TEXT           Device profile name, AKA Device Slug (optional)"
            echo "  -a TEXT           AuthKey of the device (optional, requires UUID and PSKKey accompanied with it)"
            echo "  -k TEXT           PSKKey of the device (optinal, requires AuthKey and UUID accompanied with it)"
            echo "  -u TEXT           UUID of the device (optional, requires AuthKey and PSKKey accompanied with it)"
            echo ""
            echo "==== Detaching Only: ===="
            echo "  -s SSID PASSWORD  Wifi SSID and Password to use for detaching.  Use quotes if either value contains spaces.  Certain special characters may need to be escaped with '\\'"
            echo "  -d TEXT           New device id (optional)"
            echo "  -l TEXT           New local key (optional)"
            echo ""
            echo "==== 3rd Party Firmware Flashing Only: ===="
            echo "  -f TEXT           Firmware file name without path as it exists in /custom-firmware/ (optional)"
            echo "  -t SECONDS        Timeout in seconds for how long to wait before exiting after receiving firmware update information.  Default is 15"

            exit 0
    esac
done

if [ "${METHOD_DETACH}" ] && [ "${METHOD_FLASH}" ]; then
    echo "You have supplied arguments for both detaching and flashing.  Please only include the arguments for your desired action."
    echo "Please see '${0} -h' for more information."
    exit 1
fi

# ---------------------------------------------------------------------------
# Basic host requirements
# ---------------------------------------------------------------------------
for cmd in docker iw; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "[!] Required host command '${cmd}' was not found."
        if [ "${cmd}" == "iw" ]; then
            echo "    Install it (e.g. 'sudo apt install iw') - it is used to move the WiFi adapter into the container."
        fi
        exit 1
    fi
done

if [ "${WIFI_ADAPTER}" == "" ]; then
    WIFI_ADAPTER="wlan0"
    echo "No WiFi adapter supplied with -w; defaulting to '${WIFI_ADAPTER}'."
fi

if ! iw dev "${WIFI_ADAPTER}" info >/dev/null 2>&1; then
    echo "[!] '${WIFI_ADAPTER}' does not exist or is not a WiFi (nl80211) interface on this host."
    echo "    Pass a valid adapter with -w. Available WiFi interfaces:"
    iw dev | awk '/Interface/ {print "      " $2}'
    exit 1
fi

# Resolve the physical device (wiphy) that backs the interface.  We move the whole
# phy - not just the netdev - so the container has complete control of the radio.
PHY_INDEX=$(iw dev "${WIFI_ADAPTER}" info | awk '/wiphy/ {print $2; exit}')
if [ -z "${PHY_INDEX}" ]; then
    echo "[!] Could not determine the wiphy for '${WIFI_ADAPTER}'."
    exit 1
fi
PHY="phy${PHY_INDEX}"

# ---------------------------------------------------------------------------
# Helper scripts that bookend the run happen on the host, where normal LAN
# connectivity is still available (the adapter has not been handed off yet).
# ---------------------------------------------------------------------------
run_helper_script() {
    if [ -f "scripts/${1}.sh" ]; then
        echo "Running helper script '${1}'"
        source "scripts/${1}.sh"
    fi
}

run_helper_script "pre-setup"

# ---------------------------------------------------------------------------
# Build the image
# ---------------------------------------------------------------------------
echo "Building ${IMAGE_NAME} docker image"
export NO_COLOR=1
docker build --network=host -t "${IMAGE_NAME}" .
if [ ! $? -eq 0 ]; then
    echo "Failed to build Docker image, stopping script"
    exit 1
fi
echo "Successfully built docker image"

# ---------------------------------------------------------------------------
# Start an idle container with its OWN network namespace, then move the WiFi
# adapter into it.  All work then happens via 'docker exec'.
# ---------------------------------------------------------------------------
cleanup() {
    # Stopping/removing the container destroys its network namespace; the kernel
    # automatically returns the physical wiphy to the host's default namespace.
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1

    # Best-effort: let NetworkManager manage the adapter again if it is around.
    if command -v nmcli >/dev/null 2>&1; then
        nmcli device set "${WIFI_ADAPTER}" managed yes >/dev/null 2>&1
    fi
}
trap cleanup EXIT

# Remove any stale container from a previous run.
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1

# Best-effort: stop NetworkManager from grabbing the adapter during the move.
if command -v nmcli >/dev/null 2>&1; then
    nmcli device set "${WIFI_ADAPTER}" managed no >/dev/null 2>&1
fi
rfkill unblock wifi >/dev/null 2>&1

echo "Starting container and moving adapter '${WIFI_ADAPTER}' (${PHY}) into it..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --privileged \
    --cap-add NET_ADMIN \
    -v "$(pwd):/work" \
    -e METHOD_DETACH="${METHOD_DETACH}" \
    -e METHOD_FLASH="${METHOD_FLASH}" \
    -e PROFILE="${PROFILE}" \
    -e FIRMWARE="${FIRMWARE}" \
    -e FLASH_TIMEOUT="${FLASH_TIMEOUT}" \
    -e VERBOSE_OUTPUT="${VERBOSE_OUTPUT}" \
    -e DEVICEID="${DEVICEID}" \
    -e LOCALKEY="${LOCALKEY}" \
    -e AUTHKEY="${AUTHKEY}" \
    -e PSKKEY="${PSKKEY}" \
    -e UUID="${UUID}" \
    -e OVERRIDE_AP_SSID="${OVERRIDE_AP_SSID}" \
    -e DISABLE_RESCAN="${DISABLE_RESCAN}" \
    -e RESETNM="${RESETNM}" \
    -e HAVE_SSID="${HAVE_SSID}" \
    -e SSID="${SSID}" \
    -e SSID_PASS="${SSID_PASS}" \
    -e PHY="${PHY}" \
    "${IMAGE_NAME}" \
    tail -f /dev/null >/dev/null
if [ ! $? -eq 0 ]; then
    echo "Failed to start the container."
    exit 1
fi

CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' "${CONTAINER_NAME}")
if [ -z "${CONTAINER_PID}" ] || [ "${CONTAINER_PID}" == "0" ]; then
    echo "Could not determine the container PID."
    exit 1
fi

# Move the entire physical WiFi device into the container's network namespace.
if ! iw phy "${PHY}" set netns "${CONTAINER_PID}"; then
    echo "[!] Failed to move '${PHY}' into the container namespace."
    echo "    You may need to run this script with sufficient privileges (e.g. sudo)."
    exit 1
fi

# ---------------------------------------------------------------------------
# Run the actual workflow inside the container (interactive).
# ---------------------------------------------------------------------------
docker exec -ti "${CONTAINER_NAME}" bash /src/container/run.sh
RESULT=$?

# Bring the adapter back before running the post-flash helper (LAN may be needed).
cleanup
trap - EXIT

run_helper_script "post-flash"

exit ${RESULT}
