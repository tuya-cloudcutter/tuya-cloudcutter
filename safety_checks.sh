#!/bin/bash

check_port () {
	protocol="$1"
	port="$2"
	reason="$3"
	echo -n "Checking ${protocol^^} port $port... "
	process_pid=$(sudo ss -lnp -A "$protocol" "sport = :$port" | grep -Po "(?<=pid=)(\d+)" | head -n1)
	if [ -n "$process_pid" ]; then
		process_name=$(ps -p "$process_pid" -o comm=)
		echo "Occupied by $process_name with PID $process_pid."
		echo "Port $port is needed to $reason"
		read -p "Do you wish to terminate $process_name? [y/N] " -n 1 -r
		echo
		if [[ "$REPLY" =~ ^[Ss]$ ]]; then
			echo "Skipping..."
			return
		fi
		if [[ ! $REPLY =~ ^[Yy]$ ]]; then
			echo "Aborting due to occupied port"
			exit 1
		else
			service=$(ps -p "$process_pid" -o unit= | grep .service | grep -Ev ^user)
			if [ -n "$service" ]; then
				echo "Attempting to stop $service"
				sudo systemctl stop "$service"
			else
				echo "Attempting to terminate $process_name"
				sudo kill "$process_pid"
				if ! sudo timeout 10 tail --pid="$process_pid" -f /dev/null; then
					echo "$process_name is still running after 10 seconds, sending SIGKILL"
					sudo kill -9 "$process_pid"
					sudo tail --pid="$process_pid" -f /dev/null
				fi
			fi
			sleep 1
		fi
	else
		echo "Available."
	fi
}

check_firewall () {
	if sudo systemctl stop firewalld.service &>/dev/null; then
		echo "Attempting to stop firewalld.service"
		echo "When done, enable with: ${bold}sudo systemctl start firewalld.service${normal}"
	fi
	if command -v ufw >/dev/null && sudo ufw status | grep -qw active; then
		sudo ufw disable
		echo "When done, enable with: ${bold}sudo ufw enable${normal}"
	fi
}

check_blacklist () {
	if [ -e /etc/modprobe.d/blacklist-rtl8192cu.conf ]; then
		echo "Detected /etc/modprobe.d/blacklist-rtl8192cu.conf"
		echo "This has been known to cause kernel panic in hostapd"
		echo "See https://github.com/ct-Open-Source/tuya-convert/issues/373"
		read -p "Do you wish to remove this file? [y/N] " -n 1 -r
		echo
		if [[ $REPLY =~ ^[Yy]$ ]]; then
			sudo rm /etc/modprobe.d/blacklist-rtl8192cu.conf
		fi
	fi
}

check_port udp 53 "resolve DNS queries"
check_port udp 67 "offer DHCP leases"
check_port tcp 80 "answer HTTP requests"
check_port tcp 443 "answer HTTPS requests"
check_port udp 6666 "detect unencrypted Tuya firmware"
check_port udp 6667 "detect encrypted Tuya firmware"
check_port tcp 1883 "run MQTT"
check_port tcp 8886 "run MQTTS"
check_firewall
check_blacklist
