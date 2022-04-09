#!/usr/bin/env bash

while getopts "r" flag; do
case "$flag" in
    r) RESETNM="true";;
esac
done

WIFI_ADAPTER=${@:$OPTIND:1}
PROFILE=${@:$OPTIND+1:1}
FIRMWARE=${@:$OPTIND+2:1}
source common.sh

# Select the right device
if [ "${FIRMWARE}" == "" ]; then
  run_in_docker pipenv run python3 get_input.py firmware /work/firmware.txt
  FIRMWARE=$(cat firmware.txt)
  rm -f firmware.txt
fi

source common_run.sh

# Flash custom firmware to device
echo "Flashing custom firmware .."
echo "==> Wait for 20-30 seconds for the device to connect to 'cloudcutterflash'. This script will then show the firmware upgrade requests sent by the device."
nmcli device set "${WIFI_ADAPTER}" managed no
trap "nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
run_in_docker bash -c "bash /src/setup_apmode.sh ${WIFI_ADAPTER} && pipenv run python3 -m cloudcutter update_firmware \"/work/device-profiles/${PROFILE}\" \"${CONFIG_DIR}\" \"${FIRMWARE}\""
if [ ! $? -eq 0 ]; then
    echo "Oh no, something went wrong with updating firmware! Try again I guess.."
    exit 1
fi
