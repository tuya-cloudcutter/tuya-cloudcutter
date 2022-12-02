#!/usr/bin/env bash

while getopts "hrw:p:f:" flag; do
	case "$flag" in
		r) RESETNM="true";;
		w) WIFI_ADAPTER=${OPTARG};;
		p) PROFILE=${OPTARG};;
		f) FIRMWARE=${OPTARG};;
		h)
			echo "usage: $0 [OPTION]..."
			echo "  -r          reset NetworkManager"
			echo "  -w TEXT     WiFi adapter name"
			echo "  -p TEXT     device profile name"
			echo "  -f TEXT     firmware file name"
			echo "  -h          show this message"
			exit 0
	esac
done

source common.sh

# Select the right device
if [ "${FIRMWARE}" == "" ]; then
	run_in_docker pipenv run python3 get_input.py -w /work -o /work/firmware.txt choose-firmware
	if [ ! $? -eq 0 ]; then
		exit 1
	fi
	FIRMWARE=$(cat firmware.txt)
	rm -f firmware.txt
fi

source common_run.sh

# Flash custom firmware to device
echo "Flashing custom firmware .."
echo "==> Wait for 20-30 seconds for the device to connect to 'cloudcutterflash'. This script will then show the firmware upgrade requests sent by the device."
nmcli device set "${WIFI_ADAPTER}" managed no
trap "nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
run_in_docker bash -c "bash /src/setup_apmode.sh ${WIFI_ADAPTER} && pipenv run python3 -m cloudcutter update_firmware \"${PROFILE}\" \"/work/device-profiles/schema\" \"${CONFIG_DIR}\" \"/work/custom-firmware/\" \"${FIRMWARE}\""
if [ ! $? -eq 0 ]; then
	echo "Oh no, something went wrong with updating firmware! Try again I guess.."
	exit 1
fi
