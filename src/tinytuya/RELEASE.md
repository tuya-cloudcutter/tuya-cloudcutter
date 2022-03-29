# RELEASE NOTES

## Potential Future Release Features

* IPv6 Support - Use socket.getaddrinfo() for AF_INET & AF_INET6
* Add socket.shutdown(socket.SHUT_RDWR)
* Add function to send multiple DPS index updates with one call

## v1.3.2 - TBD

* Debug - Updated debug output for payloads to formatted hexadecimal (pull request #98)
* Scan - Terminal color fix for 3.1 devices.
* Error Handling added for `set_timer()` function (Issue #87)

## v1.3.1 - TuyaCloud API Support

* PyPi Version 1.3.1
* Added TuyaCloud token expiration detection and renewal logic (Issue #94)

## v1.3.0 - TuyaCloud API Support

* PyPi Version 1.3.0
* Code format cleanup and readability improvements (pull request #91)
* Upgrade - Add TuyaCloud API support and functions (#87 #95)

```python
import tinytuya

c = tinytuya.Cloud(
        apiRegion="us", 
        apiKey="xxxxxxxxxxxxxxxxxxxx", 
        apiSecret="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", 
        apiDeviceID="xxxxxxxxxxxxxxxxxxID")

# Display list of devices
devices = c.getdevices()
print("Device List: %r" % devices)

# Select a Device ID to Test
id = "xxxxxxxxxxxxxxxxxxID"

# Display DPS IDs of Device
result = c.getdps(id)
print("DPS IDs of device:\n", result)

# Display Status of Device
result = c.getstatus(id)
print("Status of device:\n", result)

# Send Command - This example assumes a basic switch
commands = {
	'commands': [{
		'code': 'switch_1',
		'value': True
	}, {
		'code': 'countdown_1',
		'value': 0
	}]
}
print("Sending command...")
result = c.sendcommand(id,commands)
print("Results\n:", result)
```

## v1.2.11 - Updated Scan and Wizard Retry Logic

* PyPi Version 1.2.11
* Added retries logic to `wizard` and `scan` to honor value set by command line or default to a value based on the number of devices (if known):

```bash
# Explicit value set via command line
python3 -m tinytuya wizard 50   # Set retry to 50 
python3 -m tinytuya scan 50     

# Use automatic computed value
python3 -m tinytuya wizard      # Compute a default
python3 -m tinytuya scan        

# Example output
TinyTuya (Tuya device scanner) [1.2.11]

[Loaded devices.json - 32 devices]

Scanning on UDP ports 6666 and 6667 for devices (47 retries)...
```

## v1.2.10 - Wizard Update for New Tuya Regions 

* PyPi Version 1.2.10
* Added ability to disable device auto-detect (default vs device22) via `d.disabledetect=True`.
* Wizard: Added new data center regions for Tuya Cloud: (Issues #66 #75)

Code | Region | Endpoint
-- | -- | --
cn | China Data Center | https://openapi.tuyacn.com
us | Western America Data Center | https://openapi.tuyaus.com
us-e | Eastern America Data Center | https://openapi-ueaz.tuyaus.com
eu | Central Europe Data Center | https://openapi.tuyaeu.com
eu-w | Western Europe Data Center | https://openapi-weaz.tuyaeu.com
in | India Data Center | https://openapi.tuyain.com

## v1.2.9 - Edge Case Device Support

* PyPi Version 1.2.9
* Added Error Handling in class Device(XenonDevice) for conditions where response is None (Issue #68)
* Added edge-case handler in `_decode_payload()` to decode non-string type decrypted payload (Issue #67)

## v1.2.8 - BulbDevice

* PyPi Version 1.2.8
* Added additional error checking for BulbDevice type selection
* Added TinyTuya version logging for debug mode
* Fix bug in scan when color=False (Issue #63)

## v1.2.7 - New Tuya Cloud IoT Setup Wizard

* PyPi Version 1.2.7
* Updated setup `wizard` to support new Tuya Cloud signing method (Issue #57)
* Added Bulb type C and manual setting function `set_bulb_type(type)` (PR #54)
* Wizard creates `tuya-raw.json` to record raw response from Tuya IoT Platform
* Fixed device22 bug on retry - Now returns ERR_DEVTYPE error, status() includes auto-retry (#56)

## v1.2.6 - Improved Error Handling

* PyPi Version 1.2.6
* Added `wizard` handling to capture and display Tuya API server error responses (PR #45)
* Added better error handling for BulbDevice `state()` function to not crash when dps values are missing in response (PR #46)
* Added async examples using `send()` and `receive()`
* Updated scan output to include device Local Key if known (PR #49 #50)
* Fixed print typo in examples/devices.py (PR #51)

## v1.2.5 - Send and Receive Functions

* PyPi Version 1.2.5
* Added raw mode `send()` and `receive()` function to allow direct control of payload transfers. Useful to monitor constant state changes via threads or continuous loops.  This example opens a Tuya device and watches for state changes (e.g. switch going on and off):

```python
import tinytuya

d = tinytuya.OutletDevice('DEVICEID', 'DEVICEIP', 'DEVICEKEY')
d.set_version(3.3)
d.set_socketPersistent(True)

print(" > Send Initial Query for Status < ")
payload = d.generate_payload(tinytuya.DP_QUERY)
d.send(payload)

while(True):
    # See if any data is available
    data = d.receive()
    print('Received Payload: %r' % data)

    # Send a keyalive heartbeat ping
    print(" > Send Heartbeat Ping < ")
    payload = d.generate_payload(tinytuya.HEART_BEAT)
    d.send(payload)
```

## v1.2.4 - DPS Detection and Bug Fixes

* PyPi Version 1.2.4
* Added detect_available_dps() function
* Fixed bug in json_error() function
* Updated instruction for using Tuya iot.tuya.com to run Wizard
* Added option to disable deviceScan() automatic device polling
* Added better error handling processing Tuya messages (responses) Issue #39
* Fixed display bug in Wizard device polling to show correct On/Off state

## v1.2.3 - Dimmer and Brightness Functions

* PyPi Version 1.2.3
* Added `set_dimmer()` to OutletDevice class.
* Added `set_hsv()` to BulbDevice class.
* Updated `set_brightness()` in BulbDevice to handle *white* and *colour* modes. Issue #30
* BulbDevice determines features of device and presents boolean variables `has_colour`, `has_brightness` and `has_colourtemp` to ignore requests that do not exist (returns error).

## v1.2.2 - Bug Fix for Bulb Functions

* PyPi Version 1.2.2
* Fix bug in set_white_percentage(): added missing self. PR #32
* Fixed set_white_percentage: colour temp was incorrectly computed for B type Bulbs. PR #33
* Moved setup **Wizard** out of module init to standalone import to save import load.

Command line mode is still the same:
```python
python3 -m tinytuya wizard
```

Import now requires additional import to run Wizard programmatically:
```python
import tinytuya
import tinytuya.wizard

tinytuya.wizard.wizard()

```

## v1.2.1 - Bug Fix for Command 0x12 UpdateDPS

* PyPi Version 1.2.1
* Fixed header for 0x12 Update DPS Command (see issue #8)

## v1.2.0 - Error Handling and Bug Fixes

* PyPi Version 1.2.0
* Now decrypting all TuyaMessage responses (not just status)
* Fixed `set_colour(r, g, b)` to work with python2
* Fixed `set_debug()` to toggle on debug logging (with color)
* Added handler for `device22` to automatically detect and `set_dpsUsed()` with available DPS values. 
* Added `set_socketTimeout(s)` for adjustable connection timeout setting (defaults to 5s)
* Added `set_sendWait(s)` for adjustable wait time after sending device commands
* Improved and added additional error handling and retry logic
* Instead of Exceptions, tinytuya responds with Error response codes (potential breaking change):

Example

```python
import tinytuya

tinytuya.set_debug(toggle=False, color=True)

d = tinytuya.OutletDevice('<ID>','<IP>','<KEY>')
d.set_version(3.3)
d.status()
```
```
{u'Payload': None, u'Err': u'905', u'Error': u'Network Error: Device Unreachable'}
```


## v1.1.4 - Update DPS (Command 18)

* PyPi Version 1.1.4
* Added `updatedps()` command 18 function to request device to update DPS values (Issue #8)
* Added `set_debug()` function to activate debug logging 
```python
import tinytuya
import time

tinytuya.set_debug(True)

d = tinytuya.OutletDevice('DEVICEID', 'IP', 'LOCALKEY')
d.set_version(3.3)

print(" > Fetch Status < ")
data = d.status()
time.sleep(5)

print(" > Request Update for DPS indexes 18, 19 and 20 < ")
result = d.updatedps([18, 19, 20])

print(" > Fetch Status Again < ")
data2 = d.status()

print("Before %r" % data)
print("After  %r" % data2)
```

## v1.1.3 - Automatic IP Lookup

* PyPi Version 1.1.3
* Updated device read retry logic for minimum response payload (28 characters) (Issue #17)
* Feature added to do automatic IP address lookup via network scan if _None_ or '0.0.0.0' is specified.  Example:
```python
    import tinytuya
    ID = "01234567890123456789"
    IP = None
    KEY = "0123456789012345"
    d = tinytuya.OutletDevice(ID,IP,KEY)
    d.status()
```

## v1.1.2 - Bug Fix or 3.1 Devices

* PyPi Version 1.1.2
* Bug Fix for 3.1 Devices using CONTROL command - updated to hexdigest[8:][:16]
* See Issue: #11


## v1.1.1 - BulbDevice Class Update

* PyPi Version 1.1.1
* Updated BulbDevice Class to support two types of bulbs with different DPS mappings and functions:
        - Type A - Uses DPS index 1-5 and represents color with RGB+HSV
        - Type B - Uses DPS index 20-27 (no index 1)
* Updated Colour Support -  Index (DPS_INDEX_COLOUR) is assumed to be in the format:
         - (Type A) Index: 5 in hex format: rrggbb0hhhssvv 
         - (Type B) Index: 24 in hex format: hhhhssssvvvv 
* New Functions to help abstract Bulb Type:
        - `set_white_percentage(brightness=100, colourtemp=0):`
        - `set_brightness_percentage(brightness=100):`
        - `set_colourtemp_percentage(colourtemp=100):`
        - `set_mode(mode='white'):`       # white, colour, scene, music
* Example Script https://github.com/jasonacox/tinytuya/blob/master/examples/bulb.py 

## v1.1.0 - Setup Wizard

* PyPi Version 1.1.0
* Added TinyTuya Setup Wizard to help users grab device *LOCAL_KEY* from the Tuya Platform.
* Added formatted terminal color output (optionally disabled with `-nocolor`) for interactive **Wizard** and **Scan** functions.

```python
python3 -m tinytuya wizard
```
s
## v1.0.5 - Persistent Socket Connections

* PyPi Version 1.0.5
* Updated cipher json payload to mirror TuyAPI - hexdigest from `[8:][:16]` to `[8:][:24]`
* Added optional persistent socket connection, NODELAY and configurable retry limit (@elfman03) #5 #6 #7
```python
    set_socketPersistent(False/True)   # False [default] or True
    set_socketNODELAY(False/True)      # False or True [default]	    
    set_socketRetryLimit(integer)      # retry count limit [default 5]
```
* Add some "scenes" supported by color bulbs (@elfman03) 
```python
    set_scene(scene):             # 1=nature, 3=rave, 4=rainbow
```

## v1.0.4 - Network Scanner

* PyPi Version 1.0.4
* Added `scan()` function to get a list of Tuya devices on your network along with their device IP, ID and VERSION number (3.1 or 3.3):
```
python3 -m tinytuya
```

## v1.0.3 - Device22 Fix

* PyPi Version 1.0.3
* Removed automatic device22 type selection.  The assumption that 22 character ID meant it needed dev_type device22 was discovered to be incorrect and there are Tuya devices with 22 character ID's that behave similar to default devices.  Device22 type is now available via a dev_type specification on initialization:
```
    OutletDevice(dev_id, address, local_key=None, dev_type='default')
    CoverDevice(dev_id, address, local_key=None, dev_type='default')
    BulbDevice(dev_id, address, local_key=None, dev_type='default')
```
* Added Tuya Command Types framework to definitions and payload dictionary per device type.
* Bug fixes (1.0.2):
    * Update SET to CONTROL command
    * Fixed BulbDevice() `__init__`

## v1.0.0 - Initial Release

* PyPi Version 1.0.0