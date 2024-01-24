#!/usr/bin/env bash

# Select the right device
if [ "${PROFILE}" == "" ]; then
	if [ $METHOD_FLASH ]; then
		run_in_docker pipenv run python3 get_input.py -w /work -o /work/profile.txt choose-profile -f
	else
		run_in_docker pipenv run python3 get_input.py -w /work -o /work/profile.txt choose-profile
	fi
else
	run_in_docker pipenv run python3 get_input.py -w /work -o /work/profile.txt write-profile $PROFILE
fi
if [ ! $? -eq 0 ]; then
	echo "Failed to choose a profile, please run this script again"
	exit 1
fi

PROFILE=$(cat profile.txt)
rm -f profile.txt
LOCAL_PROFILE=$(echo "${PROFILE}" | sed 's/\/work\///g')
SLUGS=($(cat ${LOCAL_PROFILE} | grep -oP '(?<="slug": ")[^"]*'))
if ! [ -z "${SLUGS}" ]; then
	DEVICESLUG="${SLUGS[0]}"
	if [ "${#SLUGS[@]}" -eq 1 ]; then
		PROFILES_GREP=($(cat ${LOCAL_PROFILE} | grep -A1 '"profiles": \[' | tr -d "\t" | tr -d "\"" | tr -d " " | tr -d "["))
		PROFILESLUG="${PROFILES_GREP[1]}"
	else
		PROFILESLUG="${SLUGS[1]}"
	fi
fi
CHIP=$(cat "${LOCAL_PROFILE}" | grep -o '"chip": "[^"]*' | grep -o '[^"]*$')

run_helper_script "pre-safety-checks"
source safety_checks.sh

if [ $METHOD_FLASH ]; then
	# Select the right firmware
	if [ "${FIRMWARE}" == "" ]; then
		run_in_docker pipenv run python3 get_input.py -w /work -o /work/firmware.txt choose-firmware -c "${CHIP}"
	else
		run_in_docker pipenv run python3 get_input.py -w /work -o /work/firmware.txt validate-firmware-file "${FIRMWARE}" -c "${CHIP}"
	fi
	if [ ! $? -eq 0 ]; then
		exit 1
	fi
	FIRMWARE=$(cat firmware.txt)
	rm -f firmware.txt
fi

echo "Selected Device Slug: ${DEVICESLUG}"
echo "Selected Profile: ${PROFILESLUG}"
if ! [ -z "${FIRMWARE}" ]; then
	echo "Selected Firmware: ${FIRMWARE}"
fi

if ! [ -z "${AUTHKEY}" ] && ! [ -z "${UUID}" ] && ! [ -z "${PSKKEY}" ]; then
	echo "Using AuthKey ${AUTHKEY} , UUID ${UUID} , and PSKKey ${PSKKEY}"
	if ! [ -z "${DEVICEID}" ] && ! [ -z "${LOCALKEY}" ]; then
		echo "Using DeviceId ${DEVICEID} and LocalKey ${LOCALKEY}"
	fi
	echo "Writing deviceconfig file..."
	OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter write_deviceconfig "${PROFILE}" "${VERBOSE_OUTPUT}" --deviceid "${DEVICEID}" --localkey "${LOCALKEY}" --authkey "${AUTHKEY}" --uuid "${UUID}" --pskkey "${PSKKEY}")
else
	# Connect to Tuya device's WiFi
	echo ""
	echo "================================================================================"
	echo "Place your device in AP (slow blink) mode.  This can usually be accomplished by either:"
	echo "Power cycling off/on - 3 times and wait for the device to fast-blink, then repeat 3 more times.  Some devices need 4 or 5 times on each side of the pause"
	echo "Long press the power/reset button on the device until it starts fast-blinking, then releasing, and then holding the power/reset button again until the device starts slow-blinking."
	echo "See https://support.tuya.com/en/help/_detail/K9hut3w10nby8 for more information."
	echo "================================================================================"
	echo ""
	run_helper_script "pre-wifi-exploit"
	wifi_connect
	if [ ! $? -eq 0 ]; then
		echo "Failed to connect, please run this script again"
		exit 1
	fi

	# Exploit chain
	echo "Waiting 1 sec to allow device to set itself up..."
	sleep 1
	echo "Running initial exploit toolchain..."
	if ! [ -z "${DEVICEID}" ] && ! [ -z "${LOCALKEY}" ]; then
		echo "Using DeviceId ${DEVICEID} and LocalKey ${LOCALKEY}"
	fi
	OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter exploit_device "${PROFILE}" "${VERBOSE_OUTPUT}" --deviceid "${DEVICEID}" --localkey "${LOCALKEY}")
fi

RESULT=$?
echo "${OUTPUT}"
if [ ! $RESULT -eq 0 ]; then
	echo "Oh no, something went wrong with running the exploit! Try again I guess..."
	exit 1
fi
CONFIG_DIR=$(echo "${OUTPUT}" | grep "output=" | awk -F '=' '{print $2}' | sed -e 's/\r//')
echo "Saved device config in ${CONFIG_DIR}"

# Connect to Tuya device's WiFi again, to make it connect to our hostapd AP later
echo ""
echo "================================================================================"
echo "Power cycle and place your device in AP (slow blink) mode again.  This can usually be accomplished by either:"
echo "Power cycling off/on - 3 times and wait for the device to fast-blink, then repeat 3 more times.  Some devices need 4 or 5 times on each side of the pause"
echo "Long press the power/reset button on the device until it starts fast-blinking, then releasing, and then holding the power/reset button again until the device starts slow-blinking."
echo "See https://support.tuya.com/en/help/_detail/K9hut3w10nby8 for more information."
echo "================================================================================"
echo ""
echo "Press ENTER when ready..." && read

run_helper_script "pre-wifi-config"
wifi_connect
if [ ! $? -eq 0 ]; then
	echo "Failed to connect, please run this script again"
	exit 1
fi

# If the AP prefix did not change, the exploit was not successful
# End the process now to end further confusion
if [[ $AP_MATCHED_NAME != A-* ]] && [ -z "${AUTHKEY}" ]; then
	echo "================================================================================"
	echo "[!] The profile you selected did not result in a successful exploit."
	echo "================================================================================"
	exit 1
fi

# Add a minor delay to stabilize after connection
sleep 1
OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter configure_wifi "cloudcutterflash" "abcdabcd" "${VERBOSE_OUTPUT}")
RESULT=$?
echo "${OUTPUT}"
if [ ! $RESULT -eq 0 ]; then
	echo "Oh no, something went wrong with making the device connect to our hostapd AP! Try again I guess..."
	exit 1
fi
echo "Device is connecting to 'cloudcutterflash' access point. Passphrase for the AP is 'abcdabcd' (without ')"
