#!/usr/bin/env bash

source safety_checks.sh

COMBINED_AP_PREAMBLE=$(cat ap_preambles.txt | grep -v '#' | sort -u | awk '{print "-e \"^"$0"\"" }' | tr '\n' ' ')
AP_SEARCH_LIST=$(cat ap_preambles.txt | grep -v '#' | sort -u | awk '{print "-e \""$0"\""}' | tr '\n' ' ' | sed 's/-e //g')

AP_MATCHED_NAME=""
FIRST_WIFI=$(nmcli device status | grep " wifi " | head -n1 | awk -F ' ' '{print $1}')

if [ "${WIFI_ADAPTER}" == "" ]; then
  WIFI_ADAPTER="${FIRST_WIFI}"
fi

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
    AP_PASS=${1:-""}
    FIRST_RUN=true

    for i in {1..5}
    do
        AP_MATCHED_NAME=""

        # Turn on WiFi, and wait for SSID to show up
        reset_nm
        sleep 1

        service NetworkManager start; nmcli device set ${WIFI_ADAPTER} managed yes  # Make sure we turn on managed mode again in case we didn't recover it in the trap below
        nmcli radio wifi off
        sleep 1
        nmcli radio wifi on
        while [ "${AP_MATCHED_NAME}" == "" ]
        do
            if [ ${FIRST_RUN} == true ]; then
                echo "Scanning for known AP SSID prfixes: ${AP_SEARCH_LIST}"
                FIRST_RUN=false
            else
                echo -n "."
            fi
            
	    AP_MATCHED_NAME=$(nmcli -t -f SSID dev wifi list --rescan yes | eval grep $COMBINED_AP_PREAMBLE | sort -u)
        done

        echo "Found access point name: \"${AP_MATCHED_NAME}\", trying to connect.."
        nmcli dev wifi connect "${AP_MATCHED_NAME}" ${AP_PASS}

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
    docker build --network=host -t cloudcutter .
    if [ ! $? -eq 0 ]; then
        echo "Failed to build Docker image, stopping script"
        exit 1
    fi
}

run_in_docker () {
    docker run --network=host -ti --privileged -v "$(pwd):/work" cloudcutter "${@}"
}

# Docker prep
echo "Building cloudcutter docker image.."
build_docker
echo "Successfully built docker image"
