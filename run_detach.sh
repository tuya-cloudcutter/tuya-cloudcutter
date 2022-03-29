#!/usr/bin/env bash

TUYA_AP_PREAMBLE="SmartLife-"
AP_MATCHED_NAME=""
FIRST_WIFI=$(nmcli device status | grep " wifi " | head -n1 | awk -F ' ' '{print $1}')

SSID=${1:-$SSID}
SSID_PASS=${2:-$SSID_PASS}
WIFI_ADAPTER=${3:-$FIRST_WIFI}

wifi_connect () {
    AP_SEARCH_STRING=${1:-$TUYA_AP_PREAMBLE}
    AP_PASS=${2:-""}

    # Turn on WiFi, and wait for SSID to show up
    nmcli radio wifi on
    while [ "${AP_MATCHED_NAME}" == "" ]
    do
        echo "Scanning for "${TUYA_AP_PREAMBLE}" SSID..."
        AP_MATCHED_NAME=$(nmcli dev wifi list --rescan yes | grep "${TUYA_AP_PREAMBLE}" | cut -c 2- | awk -F ' ' '{print $2}')
    done

    echo "Found access point name: ${AP_MATCHED_NAME}, trying to connect now."
    nmcli dev wifi connect ${AP_MATCHED_NAME}

    # Check if successfully connected
    AP_STATUS=$(nmcli -f GENERAL.STATE con show "${AP_MATCHED_NAME}" | awk -F ' ' '{print $2}')
    if [ "${AP_STATUS}" != "activated" ]; then
        echo "Error, could not connect to SSID."
        return 1
    fi

    echo "Connected to access point."
    return 0
}

build_docker () {
    docker build -q -t cloudcutter .
    if [ ! $? -eq 0 ]; then
        echo "Failed to build Docker image, stopping script"
        exit 1
    fi
}

run_in_docker () {
    docker run --network=host -ti --privileged -v $(pwd):/work cloudcutter "${@}"
}

# Docker prep
echo "Building cloudcutter docker image.."
build_docker
echo "Successfully built docker image"

# Select the right device
run_in_docker pipenv run python3 select_SKU.py /work/profile.txt
PROFILE=$(cat profile.txt)
rm -f profile.txt

# Connect to Tuya device's WiFi
echo "==> Toggle Tuya device's power off and on again 6 times, with ~1 sec pauses in between, to enable AP mode. Repeat if ${TUYA_AP_PREAMBLE} SSID doesn't show up within ~30 seconds."
nmcli device set ${WIFI_ADAPTER} managed yes  # Make sure we turn on managed mode again in case we didn't recover it in the trap below
nmcli radio wifi off
nmcli radio wifi on
wifi_connect ${TUYA_AP_PREAMBLE}
if [ ! $? -eq 0 ]; then
    echo "Failed to connect, please run this script again"
    exit 1
fi

# Exploit chain
echo "Waiting 1 sec to allow device to set itself up.."
sleep 1
echo "Running initial exploit toolchain.."
OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter exploit_device /src/cloudcutter/device-profiles/${PROFILE})
RESULT=$?
echo "${OUTPUT}"
if [ ! $RESULT -eq 0 ]; then
    echo "Oh no, something went wrong with running the exploit! Try again I guess.."
    exit 1
fi
OUTPUT_DIR=$(echo "${OUTPUT}" | grep "output=" | awk -F '=' '{print $2}' | sed -e 's/\r//')
echo "Saved device config in ${OUTPUT_DIR}"


# Cutting device from cloud, allowing local-tuya access still
echo "Cutting device off from cloud.."
nmcli device set ${WIFI_ADAPTER} managed no
trap "nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
echo "==> Connect your phone to 'cloudcutter-flash' WiFi, and follow AP Mode instructions in Tuya phone app."
run_in_docker bash -c "bash /src/setup_apmode.sh ${WIFI_ADAPTER} && pipenv run python3 -m cloudcutter configure_local_device --ssid \"${SSID}\" --password \"${SSID_PASS}\" \"/src/cloudcutter/device-profiles/${PROFILE}\" \"${OUTPUT_DIR}\""
if [ ! $? -eq 0 ]; then
    echo "Oh no, something went wrong with detaching from the cloud! Try again I guess.."
    exit 1
fi