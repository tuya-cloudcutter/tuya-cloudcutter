#!/usr/bin/env bash

while getopts "hrd:l:" flag; do
case "$flag" in
    r) RESETNM="true";;
    d) DEVICEID=${OPTARG};;
    l) LOCALKEY=${OPTARG};;
	h) echo "usage: $0 [-hr] <SSID> <password> [wifi adapter name] [device name] [-d new_device_id] [-l new_local_key]"
       echo "  -r      reset NetworkManager"
       echo "  -h      show this message"
       exit 0
esac
done

SSID=${@:$OPTIND:1}
SSID_PASS=${@:$OPTIND+1:1}
WIFI_ADAPTER=${@:$OPTIND+2:1}
PROFILE=${@:$OPTIND+3:1}

echo "Using ${DEVICEID} and ${LOCALKEY}"

source common.sh
source common_run.sh

# Cutting device from cloud, allowing local-tuya access still
echo "Cutting device off from cloud.."
echo "==> Wait for 20-30 seconds for the device to connect to 'cloudcutterflash'. This script will then show the activation requests sent by the device, and tell you whether local activation was successful."
nmcli device set ${WIFI_ADAPTER} managed no; service NetworkManager stop;
trap "service NetworkManager start; nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
INNER_SCRIPT=$(xargs -0 <<- EOF
	# This janky looking string substitution is because of double evaluation.
	# Once in the parent shell script, and once in this heredoc used as a shell script.
	# First evaluate the value from the parent shell script while escaping ' chars
	# with this janky substitutions so that it doesn't break this heredoc script.
	SSID='${SSID/\'/\'\"\'\"\'}'
	SSID_PASS='${SSID_PASS/\'/\'\"\'\"\'}'
	bash /src/setup_apmode.sh ${WIFI_ADAPTER}
	pipenv run python3 -m cloudcutter configure_local_device --ssid "\${SSID}" --password "\${SSID_PASS}" "${PROFILE}" "/work/device-profiles/schema" "${CONFIG_DIR}"
EOF
)
run_in_docker bash -c "$INNER_SCRIPT"
if [ ! $? -eq 0 ]; then
    echo "Oh no, something went wrong with detaching from the cloud! Try again I guess.."
    exit 1
fi
