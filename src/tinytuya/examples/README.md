# TinyTuya - Examples

Code examples using `tinytuya` module to control various Tuya devices.

## Read Tuya Device Status

[getstatus.py](getstatus.py) - This script will read the status of a Tuya device. 

## Smart Bulb (RGB) 

[bulb.py](bulb.py) - This script tests controlling Smart Bulb with RGB capabilities.  

[bulb-scenes.py](bulb-scenes.py) - This script tests out setting Scenes for the smart bulb 

Tested devices:  Peteme Smart Light Bulbs, Wi-Fi - [link](https://www.amazon.com/gp/product/B07MKDLV1V/)

[galaxy_projector.py](galaxy_projector.py) This script tests controlling a Galaxy Projector from [galaxylamps.co](https://eu.galaxylamps.co/collections/all/products/galaxy-projector)

## Continuous Monitor

[monitor.py](monitor.py) - This script uses a loop to listen to a Tuya device for any state changes.  

## Async Send and Receive

[async_send_receive.py](async_send_receive.py) - This demonstrates how you can make a persistent connection to a Tuya device, send commands and monitor for responses in an async way.

## Send Raw DPS Values

[send_raw_dps.py](send_raw_dps.py) - This script show how to send and set raw DPS values on a Tuya device. 

## Scan all Devices

[devices.py](devices.py) - Poll status of all devices in `devices.json`.

## Use snapshot.json to Manage Devices

[snapshot.py](snapshot.py) - Example of using `snapshot.json` to manage Tuya Devices

```python
# Load in snapshot.py and control by name
turn_off('Dining Room')
time.sleep(2)
turn_on('Dining Room')
```

## Tuya Cloud API Examples

[cloud.py](cloud.py) -  Example that uses the Tinytuya `Cloud` class and functions to access the Tuya Cloud API to pull device information and control the device via the cloud.