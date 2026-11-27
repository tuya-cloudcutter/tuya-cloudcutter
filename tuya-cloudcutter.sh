#!/usr/bin/env bash
#
# Thin launcher for tuya-cloudcutter.
#
# This script no longer performs any of the actual work (scanning, connecting,
# safety checks, hosting the AP, or running the exploit).  Its only jobs are:
#   1. Parse the command line options.
#   2. Build the container image (rootless podman when unprivileged).
#   3. Move the requested WiFi adapter *fully* into the container's own network
#      namespace, so that everything wireless-related runs inside the container.
#   4. Hand control to the in-container workflow (src/container/run.sh).
#
# Because the adapter is moved into the container's namespace, a WiFi adapter
# MUST be supplied with -w.  It should be a stand-alone adapter that is not your
# primary source of networking (use ethernet for that), because it will disappear
# from the host for the duration of the run.
#
# Privilege model: when run as a regular user the container runs under rootless
# podman, which gives it full capabilities inside its own user namespace - enough
# for hostapd and every wireless operation once the adapter is moved in.  Only
# real host root can move a physical device between network namespaces, so the
# namespace move (and rfkill unblock) go through sudo; NetworkManager toggles
# run unprivileged where polkit allows it, with a sudo fallback.

set -o pipefail

# Non-login shells (cron, 'ssh host command') often lack /usr/sbin in PATH,
# which is where iw and rfkill live on Debian-family systems.
PATH="${PATH}:/usr/sbin:/sbin"

IMAGE_NAME="cloudcutter"      # container image tag (build / run)
CONTAINER_NAME="cloudcutter"  # running container name (run --name / exec / inspect / rm)
FLASH_TIMEOUT=15

# ---------------------------------------------------------------------------
# Container engine and privilege model
# ---------------------------------------------------------------------------
# Rootless podman is the default when unprivileged; when root we keep the
# docker-compatible CLI, which may be real docker or the podman-docker shim.
if [ "$(id -u)" -eq 0 ]; then
    ENGINE="docker"
    SUDO=""
else
    ENGINE="podman"
    SUDO="sudo"
    if ! command -v sudo >/dev/null 2>&1; then
        echo "[!] Running unprivileged requires 'sudo' for the WiFi adapter handoff."
        exit 1
    fi
fi

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
for cmd in "${ENGINE}" iw; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "[!] Required host command '${cmd}' was not found."
        if [ "${cmd}" == "iw" ]; then
            echo "    Install it (e.g. 'sudo apt install iw') - it is used to move the WiFi adapter into the container."
        fi
        if [ "${cmd}" == "podman" ]; then
            echo "    Install podman (e.g. 'sudo apt install podman'), or run this script as root to use docker."
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
echo "Building ${IMAGE_NAME} container image"
export NO_COLOR=1
"${ENGINE}" build --network=host -t "${IMAGE_NAME}" .
if [ ! $? -eq 0 ]; then
    echo "Failed to build container image, stopping script"
    exit 1
fi
echo "Successfully built container image"

# ---------------------------------------------------------------------------
# Start an idle container with its OWN network namespace, then move the WiFi
# adapter into it.  All work then happens via container exec.
# ---------------------------------------------------------------------------
cleanup() {
    # Stopping/removing the container destroys its network namespace; the kernel
    # automatically returns the physical wiphy to the host's default namespace.
    "${ENGINE}" rm -f "${CONTAINER_NAME}" >/dev/null 2>&1

    # Best-effort: let NetworkManager manage the adapter again if it is around.
    # Toggling managed state is polkit's network-control action, which many
    # systems allow unprivileged; fall back to sudo for stricter policies.
    if command -v nmcli >/dev/null 2>&1; then
        nmcli device set "${WIFI_ADAPTER}" managed yes >/dev/null 2>&1 \
            || ${SUDO} nmcli device set "${WIFI_ADAPTER}" managed yes >/dev/null 2>&1
    fi
}
trap cleanup EXIT

# Remove any stale container from a previous run.
"${ENGINE}" rm -f "${CONTAINER_NAME}" >/dev/null 2>&1

# Best-effort: stop NetworkManager from grabbing the adapter during the move.
# Unprivileged first (polkit network-control), sudo only as a fallback.
if command -v nmcli >/dev/null 2>&1; then
    nmcli device set "${WIFI_ADAPTER}" managed no >/dev/null 2>&1 \
        || ${SUDO} nmcli device set "${WIFI_ADAPTER}" managed no >/dev/null 2>&1
fi
${SUDO} rfkill unblock wifi >/dev/null 2>&1

echo "Starting container and moving adapter '${WIFI_ADAPTER}' (${PHY}) into it..."
"${ENGINE}" run -d \
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

CONTAINER_PID=$("${ENGINE}" inspect -f '{{.State.Pid}}' "${CONTAINER_NAME}")
if [ -z "${CONTAINER_PID}" ] || [ "${CONTAINER_PID}" == "0" ]; then
    echo "Could not determine the container PID."
    exit 1
fi

# Move the entire physical WiFi device into the container's network namespace.
# This is the one operation that genuinely needs host root: a physical device
# can only be moved between network namespaces by the user namespace that owns
# the host's.  Inside the container no root is needed - it fully controls the
# adapter from its own user namespace.
if ! ${SUDO} iw phy "${PHY}" set netns "${CONTAINER_PID}"; then
    echo "[!] Failed to move '${PHY}' into the container namespace."
    echo "    Check that 'sudo iw' works for this user (password prompt or NOPASSWD)."
    exit 1
fi

# ---------------------------------------------------------------------------
# Run the actual workflow inside the container (interactive).
# ---------------------------------------------------------------------------
"${ENGINE}" exec -ti "${CONTAINER_NAME}" bash /src/container/run.sh
RESULT=$?

# Bring the adapter back before running the post-flash helper (LAN may be needed).
cleanup
trap - EXIT

run_helper_script "post-flash"

exit ${RESULT}
