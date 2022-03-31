## Disabling cloud connection & running locally
Here we describe how to use tuya-cloudcutter to jailbreak Tuya IoT devices by replacing their security keys. This prevents them from communicating with Tuya cloud servers, and allows you to control them via your local network instead.

### Prerequisites
* A laptop or computer with a WiFi adapter
* Running (non-virtualized) Ubuntu (other distros with NetworkManager might also work, untested. VMs might work if you passthrough WiFi adapter.)
* Docker should be installed, and your user should be part of the "docker" group (reboot if you've just installed Docker, to reload the user groups.)

### Running the toolchain
* Download or git clone this repository
* Open a terminal and `cd` into the repository to make it your working directory
* Run `./run_detach.sh <SSID> <SSID password> [wifi adapter name]`, where SSID/password is the name of the access point you want the Tuya device to join, and wifi adapter is optional (if not set, it will use the first detected adapter in your computer)
* When instructed, put your Tuya device in _AP Mode_ by toggling it off and on again 6 times, with around 1 second in between each toggle. If it's a light bulb, it will blink _slowly_. If it blinks _quickly_, power cycle it 3 more times.
* The script will automatically connect to your light (assuming it creates a "SmartLife-*" SSID. If not, let us know.) and run the exploit that replaces the security keys (now it can't connect to the cloud anymore)
* The exploit freezes the light. It will reboot back into AP mode if left alone, and you can speed this up by power cycling it yourself one time
* The script will start up an access point of its own called "cloudcutter-flash", using your WiFi adapter
* Turn the device off and on again once. It will enter AP mode again. If it doesn't, power cycle it 6 times to enter AP mode. The script will now make the device connect to our "cloudcutter-flash" AP.
* Once the device connects (can take up to half a minute), the script will set up your device's local access keys, and configure it to join the SSID you passed as an argument to `run_detach.sh`
* Your Tuya device should now be completely cut off from the cloud, and be locally controllable on your network using e.g. `tinytuya`
* The randomly generated keys you need to connect to your device can be found in the `configured-devices` folder
* Enjoy!



-------


## Flashing custom firmware
WIP: we're still polishing this part of tuya-cloudcutter. It uses a similar flow to how custom flashing was done before by e.g. `tuya-convert`, which runs after our exploit has replaced the security keys of your device. Check back here in a bit to see if this is finished then!
