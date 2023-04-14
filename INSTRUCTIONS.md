## Disabling cloud connection & running locally
Here we describe how to use tuya-cloudcutter to jailbreak Tuya IoT devices by replacing their security keys. This prevents them from communicating with Tuya cloud servers, and allows you to control them via your local network instead.

### 🚨 ⚠️ WARNING⚠️ 🚨
**Using cloudcutter means that you will NO LONGER be able to use Tuya's apps and servers. Be absolutely sure that you are never going to use them again!**

### Prerequisites
* A laptop or computer with a WiFi adapter
* Running (non-virtualized) Ubuntu (other distros with NetworkManager might also work, untested. VMs might work if you passthrough WiFi adapter.)
* Docker should be installed, and your user should be part of the "docker" group (reboot if you've just installed Docker, to reload the user groups.)

**Note**: the script mentioned below can also be run in interactive mode, i.e. without any parameters, in which the user will be asked to choose one of available options.

### Finding your device

Find the device you have in the [list of available devices](https://github.com/tuya-cloudcutter/tuya-cloudcutter.github.io/tree/master/devices). Note the device name, i.e. a lowercase, alphanumeric string like `avatar-asl04-tv-backlight` (without the .json extension).

If you don't know the exact device model, or your device does not have any available profile, you can choose the device by firmware version:
- open the Tuya Smart/SmartLife app
- click on the device (even if it's offline)
- press the "edit" pencil (top-right corner)
- choose "Device Update"
- note the "Main Module" version number

Knowing this, you can run `sudo ./tuya-cloudcutter.sh` without any parameters. Then, use the `By firmware version and name` option and choose the version you found.

### Running the toolchain
* Download or git clone this repository
* Open a terminal and `cd` into the repository to make it your working directory
* Run `sudo ./tuya-cloudcutter.sh -s <SSID> <SSID password>`, where SSID/password is the name of the access point you want the Tuya device to join.
  * You can specify the device profile name using `-p my-device-name`; otherwise an interactive menu will be shown.
  * **If your SSID and/or password have special characters like $ ! or @, make sure to pass them with ' characters, e.g. 'P@$$W0rD!'. If it has the ' character then also make sure to escape that, with bash that'd be `'P@$$W0rD!'"'"' 1234'` to use the password `P@$$W0rD!' 1234`** **Optionally run with parameter -r to reset NetworkManager connections, which may help with some wifi adaptors ( sudo ./tuya-cloudcutter.sh -r -s <SSID> <SSID password> )**
  * If you wish to set a custom deviceid or localkey, prepend these parameters like so: `sudo ./tuya-cloudcutter.sh -d 20characterdeviceid -l 16characterlocalkey -s <SSID> <SSID password>`, Note, localtuya in homeassistant currently requires unique deviceid to work.
* When instructed, put your Tuya device in _AP Mode_ by toggling it off and on again 6 times, with around 1 second in between each toggle. If it's a light bulb, it will blink _slowly_. If it blinks _quickly_, power cycle it 3 more times.
* The script will automatically connect to your light (assuming it creates a "SmartLife-*" SSID. If not, let us know.) and run the exploit that replaces the security keys (now it can't connect to the cloud anymore)
* The exploit freezes the light. It will reboot back into AP mode if left alone, and you can speed this up by power cycling it yourself one time
* The script will start up an access point of its own called "cloudcutterflash", using your WiFi adapter
* Turn the device off and on again once. It will enter AP mode again. If it doesn't, power cycle it 6 times to enter AP mode. The script will now make the device connect to our "cloudcutterflash" AP.
* Once the device connects (can take up to a minute), the script will set up your device's local access keys, and configure it to join the SSID you passed as an argument to the script
* You should see the activation requests show up in the terminal as cloudcutter configures the device
* **Note:** If you don't see anything show up for longer than 2 minutes, power cycle the device to enter AP mode again and use one of the "SmartLife" compatible apps to instruct the device to connnect to the "cloudcutterflash" AP. The password for that AP is "abcdabcd" (without the " characters).
* Your Tuya device should now be completely cut off from the cloud, and be locally controllable on your network using e.g. `tinytuya`
* The randomly generated keys you need to connect to your device can be found in the `configured-devices` folder
* Enjoy!



-------


## Flashing custom firmware
* Copy your new firmware .bin file (UG only!) to ./custom-firmware
* Find your device name, as instructed in the steps above.
* Run `sudo ./tuya-cloudcutter.sh`. You can specify device profile name and firmware file using `-p` and `-f`, respectively (this is optional). Example: `sudo ./tuya-cloudcutter.sh -p avatar-asl04-tv-backlight -f custom_firmware_UG_file.bin`
* Follow the instructions from the script to turn off/on your device 6 times during 2 steps (similar to the steps above)
* If all goes well, your device is now running your custom firmware, enjoy!

### Custom firmware options

Please see the [wiki](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/FAQ#what-custom-firmware-options-are-available) for information about available 3rd party firmware.
