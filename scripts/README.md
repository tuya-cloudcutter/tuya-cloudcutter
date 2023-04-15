# Helper Scripts

Scripts can be placed in this directory that will be run during the flashing process.

This can be used to automate flashing or configure things specific for your environment.

Scripts should be bash scripts, ending with a `.sh` extension, and have the execute bit set (`chmod +x *.sh`). If you want to call something that's not bash, call it from within the bash script (see `post-flash.sh-example` for an example).

## Available Scripts

The full list of available helper scripts is listed below. If a script is not included, it's skipped (ie: it's OK to just include the scripts you require).

### pre-setup.sh

If this script exists, it is called before the main script is run, after some initial basic checks have been performed.

### pre-wifi-exploit.sh

Called before the initial WiFi exploit (the first time the device is put into AP mode).

### pre-wifi-config.sh

Called before the device is configured to update to use the local server / get flashed (the second time the device is put into AP mode).

### pre-safety-checks.sh

Runs before the `tuya-cloudcutter` safety checks are performed before flashing custom firmware (configuring the local PC to be in AP mode).

### post-flash.sh

Called after the device has been successfully flashed.

# Example scripts

This directory includes a full set of example scripts to show what could be done. **These must be customized** for your specific use case and are not generic.

The example scripts, if renamed to remove the `-example`, could be called with:

```
sudo MQTT_HOST=10.0.0.1 SWITCH_TOPIC=cmnd/flashing/power1 ./tuya-cloudcutter.sh
```

Or, for something more automatic, include the full configuration, eg:

```
sudo MQTT_HOST=10.0.0.1 SWITCH_TOPIC=cmnd/flashing/power1 ./tuya-cloudcutter.sh -f <3rd-party-firmware.bin> -p <device-slug> -r
```

The script could also be called from another script to flash several devices at once, eg:

```
#!/usr/bin/env bash

# Flash 4 devices at once
echo Flashing via port 1
MQTT_HOST=10.0.0.1 SWITCH_TOPIC=cmnd/flashing/power1 ./tuya-cloudcutter.sh -f <3rd-party-firmware.bin> -p <device-slug> -r

echo Flashing via port 2
MQTT_HOST=10.0.0.1 SWITCH_TOPIC=cmnd/flashing/power2 ./tuya-cloudcutter.sh -f <3rd-party-firmware.bin> -p <device-slug> -r

echo Flashing via port 3
MQTT_HOST=10.0.0.1 SWITCH_TOPIC=cmnd/flashing/power3 ./tuya-cloudcutter.sh -f <3rd-party-firmware.bin> -p <device-slug> -r

echo Flashing via port 4
MQTT_HOST=10.0.0.1 SWITCH_TOPIC=cmnd/flashing/power4 ./tuya-cloudcutter.sh -f <3rd-party-firmware.bin> -p <device-slug> -r
```
