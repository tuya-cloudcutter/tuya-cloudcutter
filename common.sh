#!/usr/bin/env bash

source safety_checks.sh

AP_MATCHED_NAME=""
AP_CONNECTED_ENDING=""
FIRST_WIFI=$(nmcli device status | grep " wifi " | head -n1 | awk -F ' ' '{print $1}')

if [ "${WIFI_ADAPTER}" == "" ]; then
  WIFI_ADAPTER="${FIRST_WIFI}"
fi

if [ "${WIFI_ADAPTER}" == "" ]; then
	echo "[!] Unable to auto-detect wifi adapter.  Please use the '-w' argument to pass in a wifi adapter."
	echo "See '{$0} -h' for more information."
	return 0
fi

SUPPORTS_AP=$(nmcli -f wifi-properties device show ${WIFI_ADAPTER} | grep WIFI-PROPERTIES.AP | awk -F ' ' '{print $2}')

# We don't want to hard stop here because localization could lead to false positives, but warn if AP mode does not appear supported.
if [ "${SUPPORTS_AP}" != "yes" ]; then
	echo "[!] WARNING: Selected wifi AP support: ${SUPPORTS_AP}"
	echo "AP support is manditory for tuya-cloudcutter to work.  If this is blank or 'no' your adapter doesn't support this feature."
	read -n 1 -s -r -p "Press any key to continue, or CTRL+C to exit"
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
                echo "Scanning for open Tuya SmartLife AP"
                FIRST_RUN=false
            else
                echo -n "."
            fi
            
            RESCAN_ARG="--rescan yes"
            if [ ${DISABLE_RESCAN} == true ]; then
                RESCAN_ARG=""
            fi

            # Search for an AP ending with - and 4 hexidecimal characters that has no security mode, unless we've already connected to one, in which case we look for that specific one
            SSID_REGEX="-[A-F0-9]{4}"
            if [ "${AP_CONNECTED_ENDING}" != "" ]; then
                SSID_REGEX="${AP_CONNECTED_ENDING}"
            fi

            AP_MATCHED_NAME=$(nmcli -t -f SSID,SECURITY dev wifi list ${RESCAN_ARG} ifname ${WIFI_ADAPTER} | grep -E ^.*${SSID_REGEX}:$ | awk -F ':' '{print $1}' | head -n1)
        done

        echo -e "\nFound access point name: \"${AP_MATCHED_NAME}\", trying to connect.."
        nmcli dev wifi connect "${AP_MATCHED_NAME}" ifname ${WIFI_ADAPTER} name "${AP_MATCHED_NAME}"

        # Check if successfully connected
        # Note, we were previously checking GENERAL.STATE and comparing to != "activated" but that has internationalization problems
        # There does not appear to be a numeric status code we can check
        # This may need updating if Tuya or one of their sub-vendors ever change their AP mode gateway IP
        AP_GATEWAY=$(nmcli -f IP4.GATEWAY con show "${AP_MATCHED_NAME}" | awk -F ' ' '{print $2}')
        if [ "${AP_GATEWAY}" != "192.168.175.1" ]; then
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
    docker run --network=host -ti --privileged -v "$(pwd):/work" cloudcutter "${@}"
}

# Docker prep
echo "Building cloudcutter docker image.."
build_docker
echo "Successfully built docker image"
