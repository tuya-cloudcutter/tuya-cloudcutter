#!/usr/bin/env bash

CLOUDCUTTER_AP_PREAMBLE="A-"
TUYA_AP_PREAMBLE="SmartLife-"
IHOME_AP_PREAMBLE="iHome-"
COMBINED_AP_PREAMBLE="(${CLOUDCUTTER_AP_PREAMBLE})|(${TUYA_AP_PREAMBLE})|(${IHOME_AP_PREAMBLE})"

AP_MATCHED_NAME=""
FIRST_WIFI=$(nmcli device status | grep " wifi " | head -n1 | awk -F ' ' '{print $1}')

SSID=${1:-$SSID}
SSID_PASS=${2:-$SSID_PASS}
WIFI_ADAPTER=${3:-$FIRST_WIFI}

wifi_connect () {
    AP_SEARCH_STRING=${1:-$COMBINED_AP_PREAMBLE}
    AP_PASS=${2:-""}


    for i in {1..5}
    do
        AP_MATCHED_NAME=""

        # Turn on WiFi, and wait for SSID to show up
        nmcli device set ${WIFI_ADAPTER} managed yes  # Make sure we turn on managed mode again in case we didn't recover it in the trap below
        nmcli radio wifi off
        sleep 1
        nmcli radio wifi on
        while [ "${AP_MATCHED_NAME}" == "" ]
        do
            echo "Scanning for "${AP_SEARCH_STRING}" SSID..."
            AP_MATCHED_NAME=$(nmcli -t -f SSID dev wifi list --rescan yes | grep -E "${AP_SEARCH_STRING}"
        done

        echo "Found access point name: ${AP_MATCHED_NAME}, trying to connect.."
        nmcli dev wifi connect ${AP_MATCHED_NAME} ${AP_PASS}

        # Check if successfully connected
        AP_STATUS=$(nmcli -f GENERAL.STATE con show "${AP_MATCHED_NAME}" | awk -F ' ' '{print $2}')
        if [ "${AP_STATUS}" != "activated" ]; then
            if [[ "${i}" == "5" ]]; then
                echo "Error, could not connect to SSID."
                return 1
            fi
        else
            break
        fi

        sleep 1
    done

    echo "Connected to access point."
    return 0
}

build_docker () {
    docker build -t cloudcutter .
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
echo "==> Toggle Tuya device's power off and on again 6 times, with ~1 sec pauses in between, to enable AP mode. Repeat if your device's SSID doesn't show up within ~30 seconds."
wifi_connect ${COMBINED_AP_PREAMBLE}
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


# Connect to Tuya device's WiFi again, to make it connect to our hostapd AP later
echo "==> Turn the device off and on again once. Repeat 6 more times if your device's SSID doesn't show up within ~5 seconds."
sleep 1
wifi_connect ${COMBINED_AP_PREAMBLE}
if [ ! $? -eq 0 ]; then
    echo "Failed to connect, please run this script again"
    exit 1
fi
OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter configure_wifi "cloudcutter-flash" "")
RESULT=$?
echo "${OUTPUT}"
if [ ! $RESULT -eq 0 ]; then
    echo "Oh no, something went wrong with making the device connect to our hostapd AP! Try again I guess.."
    exit 1
fi
echo "Device is connecting to 'cloudcutter-flash' access point"


# Cutting device from cloud, allowing local-tuya access still
echo "Cutting device off from cloud.."
echo "==> Wait for 20-30 seconds for the device to connect to 'cloudcutter-flash'. This script will then show the activation requests sent by the device, and tell you whether local activation was successful."
nmcli device set ${WIFI_ADAPTER} managed no
trap "nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
run_in_docker bash -c "bash /src/setup_apmode.sh ${WIFI_ADAPTER} && pipenv run python3 -m cloudcutter configure_local_device --ssid \"${SSID}\" --password \"${SSID_PASS}\" \"/src/cloudcutter/device-profiles/${PROFILE}\" \"${OUTPUT_DIR}\""
if [ ! $? -eq 0 ]; then
    echo "Oh no, something went wrong with detaching from the cloud! Try again I guess.."
    exit 1
fi
