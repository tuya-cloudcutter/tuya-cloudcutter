#!/usr/bin/env bash

# Select the right device
if [ "${PROFILE}" == "" ]; then
  run_in_docker pipenv run python3 get_input.py -w /work -o /work/profile.txt choose-profile
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

{
	echo "Selected Device Slug: ${DEVICESLUG}"
	echo "Selected Profile: ${PROFILESLUG}"
	if ! [ -z "${FIRMWARE}" ]; then
		echo "Selected Firmware: ${FIRMWARE}"
	fi

	# Check if chip in profile mismatches a chip in the firmware name if there is one present.
	if ! [ -z "${FIRMWARE}" ]; then
	  CHIP=$(cat "${LOCAL_PROFILE}" | grep -o '"chip": "[^"]*' | grep -o '[^"]*$')
	  if grep -iq "BK7231" <<< "${FIRMWARE}"; then
		if ! grep -iq "${CHIP}" <<< "${FIRMWARE}"; then
		  echo "WARNING: Flashing a firmware for the wrong chip may soft-brick your device requiring a serial flash to recover."
		  echo "You have selected a profile for chip type ${CHIP} but the selected firmware filename (${FIRMWARE}) indicates it may be for another chip."
		  read -p "Are you sure want to proceed?  Type 'PROCEED' (case-sensitive) to continue or 'exit' to stop (exit/PROCEED): " doublecheck
		  case $doublecheck in 
			"PROCEED" ) echo "Proceding with selected profile for chip ${CHIP} and firmware ${FIRMWARE}";
			  break;;
			* ) exit;;
		  esac
		fi
	  fi
	fi

	# Connect to Tuya device's WiFi
	echo "==> Toggle Tuya device's power off and on again 6 times, with ~1 sec pauses in between, to enable AP mode. Repeat if your device's SSID doesn't show up within ~30 seconds. For smart plugs long press the reset button on the device for about 5 seconds. See https://support.tuya.com/en/help/_detail/K9hut3w10nby8 for more information."
	wifi_connect
	if [ ! $? -eq 0 ]; then
	  echo "Failed to connect, please run this script again"
	  exit 1
	fi

	# Exploit chain
	echo "Waiting 1 sec to allow device to set itself up.."
	sleep 1
	echo "Running initial exploit toolchain.."
	if ! [ -z "${DEVICEID}" ] && ! [ -z "${LOCALKEY}" ]; then
		echo "Using ${DEVICEID} and ${LOCALKEY}"
	fi
	OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter exploit_device "${PROFILE}" --deviceid "${DEVICEID}" --localkey "${LOCALKEY}")
	RESULT=$?
	echo "${OUTPUT}"
	if [ ! $RESULT -eq 0 ]; then
	  echo "Oh no, something went wrong with running the exploit! Try again I guess.."
	  exit 1
	fi
	CONFIG_DIR=$(echo "${OUTPUT}" | grep "output=" | awk -F '=' '{print $2}' | sed -e 's/\r//')
	echo "Saved device config in ${CONFIG_DIR}"


	# Connect to Tuya device's WiFi again, to make it connect to our hostapd AP later
	echo "==> Turn the device off and on again once. Repeat 6 more times if your device's SSID doesn't show up within ~5 seconds. For smart plugs long press the reset button on the device for about 5 seconds. See https://support.tuya.com/en/help/_detail/K9hut3w10nby8 for more information."
	sleep 1
	wifi_connect
	if [ ! $? -eq 0 ]; then
	  echo "Failed to connect, please run this script again"
	  exit 1
	fi

	# If the AP prefix did not change, the exploit was not successful
	# End the process now to end further confusion
	if [[ $AP_MATCHED_NAME != A-* ]]; then
	  echo "===================================================================="
	  echo "[!] The profile you selected did not result in a successful exploit."
	  echo "===================================================================="
	  exit 1
	fi

	# Add a minor delay to stabilize after connection
	sleep 1
	OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter configure_wifi "cloudcutterflash" "abcdabcd")
	RESULT=$?
	echo "${OUTPUT}"
	if [ ! $RESULT -eq 0 ]; then
	  echo "Oh no, something went wrong with making the device connect to our hostapd AP! Try again I guess.."
	  exit 1
	fi
	echo "Device is connecting to 'cloudcutterflash' access point. Passphrase for the AP is 'abcdabcd' (without ')"
} 2>&1 | tee -a ${LOGFILE}
