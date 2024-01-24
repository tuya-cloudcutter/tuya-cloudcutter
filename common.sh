#!/usr/bin/env bash

AP_MATCHED_NAME=""
AP_CONNECTED_ENDING=""

if [ "${WIFI_ADAPTER}" == "" ]; then
  WIFI_ADAPTER=$(sudo iw dev | grep -m 1 -oP "Interface \K.*")
  if [ "${WIFI_ADAPTER}" == "" ]; then
	echo "[!] Unable to auto-detect wifi adapter.  Please use the '-w' argument to pass in a wifi adapter."
	echo "See '$0 -h' for more information."
	exit 1
  fi
fi

SUPPORTS_AP=$(iw phy phy$(iw dev ${WIFI_ADAPTER} info | grep -oP "wiphy \K\d+") info | grep -q "AP" && echo "yes")

# We don't want to hard stop here because localization could lead to false positives, but warn if AP mode does not appear supported.
if [ "${SUPPORTS_AP}" != "yes" ]; then
	echo "[!] WARNING: Selected wifi AP support: ${SUPPORTS_AP}"
	echo "AP support is manditory for tuya-cloudcutter to work.  If this is blank or 'no' your adapter doesn't support this feature."
	read -n 1 -s -r -p "Press any key to continue, or CTRL+C to exit"
fi

function run_helper_script () {
    if [ -f "scripts/${1}.sh" ]; then
        echo "Running helper script '${1}'"
        source "scripts/${1}.sh"
    fi
}

reset_nm () {

if [ -z ${RESETNM+x} ]; then
    return 0
else
    echo "Wiping NetworkManager configs"
    rm -f /etc/NetworkManager/system-connections/*.nmconnection*
    service NetworkManager restart
    return 0
fi

}

wifi_connect () {
    FIRST_RUN=true

    for i in {1..5}
    do
        AP_MATCHED_NAME=""

        # Turn on WiFi, and wait for SSID to show up
        reset_nm
        sleep 1

        sudo ip link set dev ${WIFI_ADAPTER} down
        sleep 1
        sudo ip link set dev ${WIFI_ADAPTER} up
        while [ "${AP_MATCHED_NAME}" == "" ]
        do
            if [ ${FIRST_RUN} == true ]; then
                echo "Scanning for open Tuya SmartLife AP"
                FIRST_RUN=false
            else
                echo -n "."
            fi

            # Search for an AP ending with - and 4 hexidecimal characters that has no security mode, unless we've already connected to one, in which case we look for that specific one
            SSID_REGEX="-[A-F0-9]{4}"
            if [ "${AP_CONNECTED_ENDING}" != "" ]; then
                SSID_REGEX="${AP_CONNECTED_ENDING}"
            fi

            AP_MATCHED_NAME=$(sudo iw ${WIFI_ADAPTER} scan | grep -oP "SSID: \K.*$SSID_REGEX")
        done

        echo -e "\nFound access point name: \"${AP_MATCHED_NAME}\", trying to connect..."
        sudo iw dev ${WIFI_ADAPTER} connect "${AP_MATCHED_NAME}"
        until iw dev ${WIFI_ADAPTER} link | grep -qP "SSID: ${AP_MATCHED_NAME}"; do
             echo -n "."
             sleep 2
        done
        echo ""
        sudo dhclient -v -1 ${WIFI_ADAPTER}

        # Check if successfully connected
        # Note, we were previously checking GENERAL.STATE and comparing to != "activated" but that has internationalization problems
        # There does not appear to be a numeric status code we can check
        # This may need updating if Tuya or one of their sub-vendors ever change their AP mode gateway IP
        AP_GATEWAY=$(ip route show dev ${WIFI_ADAPTER} | grep -oP "default via \K\S+")
        if [ "${AP_GATEWAY}" != "192.168.175.1" ] && [ "${AP_GATEWAY}" != "192.168.176.1" ]; then
            if [ "${AP_GATEWAY}" != "" ]; then
                echo "Expected AP gateway = 192.168.175.1 or 192.168.176.1 but got ${AP_GATEWAY}"
            fi
            if [[ "${i}" == "5" ]]; then
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

build_docker () {
    docker build --network=host -t cloudcutter .
    if [ ! $? -eq 0 ]; then
        echo "Failed to build Docker image, stopping script"
        exit 1
    fi
}

run_in_docker () {
    docker rm cloudcutter >/dev/null 2>&1
    docker run --rm --name cloudcutter --network=host -ti --privileged -v "$(pwd):/work" cloudcutter "${@}"
}

# Docker prep
echo "Building cloudcutter docker image"
build_docker
echo "Successfully built docker image"
