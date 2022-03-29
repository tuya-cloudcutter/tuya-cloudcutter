# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - Example to send raw DPS values to Tuya devices

 You could also use set_value(dps_index,value) but would need to do that for each DPS value. 
 To send it in one packet, you build the payload yourself and send it using something simliar
 to this example.

 Note: Some devices will not accept multiple commands and require you to send two separate commands. 
 My Gosund dimmer switch is one of those and requires that I send two commands, 
 one for '1' for on/off and one for '3' for the dimmer. 

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

""" 
import tinytuya

# Connect to the device - replace with real values
d=tinytuya.OutletDevice(DEVICEID, DEVICEIP, DEVICEKEY)
d.set_version(3.3)

# Generate the payload to send - add all the DPS values you want to change here
payload=d.generate_payload(tinytuya.CONTROL, {'1': True, '2': 50})

# Optionally you can set separate gwId, devId and uid values 
# payload=d.generate_payload(tinytuya.CONTROL, data={'1': True, '2': 50}, gwId=DEVICEID, devId=DEVICEID, uid=DEVICEID)

# Send the payload to the device
d._send_receive(payload)