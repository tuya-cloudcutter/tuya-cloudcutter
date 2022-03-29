# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - Example script that uses the snapshot.json to manage Tuya Devices

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya
"""

import tinytuya
import json
import time

with open('snapshot.json') as json_file:
     data = json.load(json_file)

# Print a table with all devices
print("%-25s %-24s %-16s %-17s %-5s" % ("Name","ID", "IP","Key","Version"))
for item in data["devices"]:
    print("%-25.25s %-24s %-16s %-17s %-5s" % (
        item["name"],
        item["id"],
        item["ip"],
        item["key"],
        item["ver"]))

# Print status of everything
for item in data["devices"]:
    print("\nDevice: %s" % item["name"])
    d = tinytuya.OutletDevice(item["id"], item["ip"], item["key"])
    d.set_version(float(item["ver"]))
    status = d.status()  
    print(status)

# Turn on a device by name
def turn_on(name):
    # find the right item that matches name
    for item in data["devices"]:
        if item["name"] == name:
            break
    print("\nTurning On: %s" % item["name"])
    d = tinytuya.OutletDevice(item["id"], item["ip"], item["key"])
    d.set_version(float(item["ver"]))
    d.set_status(True)

# Turn off a device by name
def turn_off(name):
    # find the right item that matches name
    for item in data["devices"]:
        if item["name"] == name:
            break
    print("\nTurning Off: %s" % item["name"])
    d = tinytuya.OutletDevice(item["id"], item["ip"], item["key"])
    d.set_version(float(item["ver"]))
    d.set_status(False)

# Test it
turn_off('Dining Room')
time.sleep(2)
turn_on('Dining Room')

