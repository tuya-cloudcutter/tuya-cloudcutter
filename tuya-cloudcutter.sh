#!/usr/bin/env bash
TIMESTAMP=`date +%s`
LOGFILE="logs/log-${TIMESTAMP}.log"
FLASH_TIMEOUT=15

function getopts-extra () {
    declare i=1
    # if the next argument is not an option, then append it to array OPTARG
    while [[ ${OPTIND} -le $# && ${!OPTIND:0:1} != '-' ]]; do
        OPTARG[i]=${!OPTIND}
        let i++ OPTIND++
    done
}

while getopts "hrntvw:p:f:d:l:s::a:k:u:" flag; do
	case "$flag" in
		r)	RESETNM="true";;
		n)  DISABLE_RESCAN="true";;
		v)  VERBOSE_OUTPUT="true";;
		w)	WIFI_ADAPTER=${OPTARG};;
		p)	PROFILE=${OPTARG};;
		f)	FIRMWARE=${OPTARG}
            METHOD_FLASH="true"
            ;;
		t)  FLASH_TIMEOUT=${OPTARG};;
		d)	DEVICEID=${OPTARG};;
		l)	LOCALKEY=${OPTARG};;
		a)  AUTHKEY=${OPTARG};;
		k)  PSKKEY=${OPTARG};;
		u)  UUID=${OPTARG};;
		s)	getopts-extra "$@"
            METHOD_DETACH="true"
			HAVE_SSID="true"
			SSID_ARGS=( "${OPTARG[@]}" )
			SSID=${SSID_ARGS[0]}
			SSID_PASS=${SSID_ARGS[1]}
			;;
		h)
			echo "usage: $0 [OPTION]..."
            echo "  -h                Show this message"
            echo "  -r                Reset NetworkManager"
			echo "  -n				  No Rescan (for older versions of nmcli that don't support it)"
			echo "  -v				  Verbose log output"
            echo "  -w TEXT           WiFi adapter name (optional, auto-selected if not supplied)"
            echo "  -p TEXT           Device profile name, AKA Device Slug (optional)"
			echo "  -a TEXT           AuthKey of the device (optional, requires UUID and PSKKey accompanied with it)"
			echo "  -k TEXT           PSKKey of the device (optinal, requires AuthKey and UUID accompanied with it)"
			echo "  -u TEXT           UUID of the device (optional, requires AuthKey and PSKKey accompanied with it)"
			echo ""
            echo "==== Detaching Only: ===="
            echo "  -s SSID PASSWORD  Wifi SSID and Password to use for detaching.  Use quotes if either value contains spaces.  Certain special characters may need to be escaped with '\\'"
            echo "  -d TEXT           New device id (optional)"
			echo "  -l TEXT           New local key (optional)"
			echo ""
            echo "==== 3rd Party Firmware Flashing Only: ===="
            echo "  -f TEXT           Firmware file name without path as it exists in /custom-firmware/ (optional)"
			echo "  -t SECONDS        Timeout in seconds for how long to wait before exiting after receiving firmware update information.  Default is 15"
			
			exit 0
	esac
done

if [ $METHOD_DETACH ] && [ $METHOD_FLASH ]; then
    echo "You have supplied arguments for both detaching and flashing.  Please only include the arguments for your desired action."
    echo "Please see '${0} -h' for more information."
    exit 1
fi

source common.sh

run_helper_script "pre-setup"

if [ ! $METHOD_DETACH ] && [ ! $METHOD_FLASH ]; then
    PS3="[?] Select your desired operation [1/2]: "
    select method in "Detach from the cloud and run Tuya firmware locally" "Flash 3rd Party Firmware"; do
        case $REPLY in
            1)		METHOD_DETACH="true"
                    break
                    ;;
            2)		METHOD_FLASH="true"
                    break
                    ;;
        esac
    done
fi

if [ $METHOD_DETACH ] && [ ! $HAVE_SSID ]; then
    echo "Detaching requires an SSID and Password, please enter each at the following prompt"
	echo "In order to provide secure logging, the values you type for your password will not show on screen"
	echo "If you make a mistake, you can run the detach process again"
	echo "You can also pass credentials via the -s command line option, see '${0} -h' for more information'"
    read -p "Please enter your SSID: " SSID
    read -p "Please enter your Password: "$'\n' -s SSID_PASS
fi

echo "Loading options, please wait..."

source common_run.sh

if [ $METHOD_DETACH ]; then
	# Cutting device from cloud, allowing local-tuya access still
	echo "Cutting device off from cloud..."
	echo ""
	echo "================================================================================"
	echo "Wait for up to 10-120 seconds for the device to connect to 'cloudcutterflash'. This script will then show the activation requests sent by the device, and tell you whether local activation was successful."
	echo "================================================================================"
	echo ""

	nmcli device set ${WIFI_ADAPTER} managed no; service NetworkManager stop;
	trap "service NetworkManager start; nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
	INNER_SCRIPT=$(xargs -0 <<- EOF
		# This janky looking string substitution is because of double evaluation.
		# Once in the parent shell script, and once in this heredoc used as a shell script.
		# First evaluate the value from the parent shell script while escaping ' chars
		# with this janky substitutions so that it doesn't break this heredoc script.
		SSID='${SSID/\'/\'\"\'\"\'}'
		SSID_PASS='${SSID_PASS/\'/\'\"\'\"\'}'
		bash /src/setup_apmode.sh ${WIFI_ADAPTER} ${VERBOSE_OUTPUT}
		pipenv run python3 -m cloudcutter configure_local_device --ssid "\${SSID}" --password "\${SSID_PASS}" "${PROFILE}" "/work/device-profiles/schema" "${CONFIG_DIR}" ${FLASH_TIMEOUT} "${VERBOSE_OUTPUT}"
	EOF
	)
	run_in_docker bash -c "$INNER_SCRIPT"
	if [ ! $? -eq 0 ]; then
		echo "Oh no, something went wrong with detaching from the cloud! Try again I guess..."
		if [ ! $VERBOSE_OUTPUT ]; then
			echo "If you need to report an issue, please run with the -v flag and supply the full log of that attempt."
		fi
		exit 1
	fi
fi

if [ $METHOD_FLASH ]; then
	# Flash custom firmware to device
	echo "Flashing custom firmware..."
	echo ""
	echo "================================================================================"
	echo "Wait for up to 10-120 seconds for the device to connect to 'cloudcutterflash'. This script will then show the firmware upgrade requests sent by the device."
	echo "================================================================================"
	echo ""
	nmcli device set "${WIFI_ADAPTER}" managed no
	trap "nmcli device set ${WIFI_ADAPTER} managed yes" EXIT  # Set WiFi adapter back to managed when the script exits
	run_in_docker bash -c "bash /src/setup_apmode.sh ${WIFI_ADAPTER} ${VERBOSE_OUTPUT} && pipenv run python3 -m cloudcutter update_firmware \"${PROFILE}\" \"/work/device-profiles/schema\" \"${CONFIG_DIR}\" \"/work/custom-firmware/\" \"${FIRMWARE}\" \"${FLASH_TIMEOUT}\" \"${VERBOSE_OUTPUT}\""
	if [ ! $? -eq 0 ]; then
		echo "Oh no, something went wrong with updating firmware! Try again I guess..."
		if [ ! $VERBOSE_OUTPUT ]; then
			echo "If you need to report an issue, please run with the -v flag and supply the full log of that attempt."
		fi
		exit 1
	fi
fi

run_helper_script "post-flash"