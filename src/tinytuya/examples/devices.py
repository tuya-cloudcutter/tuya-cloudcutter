# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - Example to poll status of all devices in Devices.json

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

""" 
import tinytuya
import json
import time

DEVICEFILE = 'devices.json'
SNAPSHOTFILE = 'snapshot.json'
havekeys = False
tuyadevices = []

# Terminal Color Formatting
bold = "\033[0m\033[97m\033[1m"
subbold = "\033[0m\033[32m"
normal = "\033[97m\033[0m"
dim = "\033[0m\033[97m\033[2m"
alert = "\033[0m\033[91m\033[1m"
alertdim = "\033[0m\033[91m\033[2m"

# Lookup Tuya device info by (id) returning (name, key)
def tuyaLookup(deviceid):
    for i in tuyadevices:
        if (i['id'] == deviceid):
            return (i['name'], i['key'])
    return ("", "")

# Read Devices.json 
try:
    # Load defaults
    with open(DEVICEFILE) as f:
        tuyadevices = json.load(f)
        havekeys = True
except:
    # No Device info
    print(alert + "\nNo devices.json file found." + normal)
    exit()

# Scan network for devices and provide polling data
print(normal + "\nScanning local network for Tuya devices...")
devices = tinytuya.deviceScan(False, 30)
print("    %s%s local active devices discovered%s" %
        (dim, len(devices), normal))
print("")

def getIP(d, gwid):
    for ip in d:
        if (gwid == d[ip]['gwId']):
            return (ip, d[ip]['version'])
    return (0, 0)

polling = []
print("Polling local devices...")
for i in tuyadevices:
    item = {}
    name = i['name']
    (ip, ver) = getIP(devices, i['id'])
    item['name'] = name
    item['ip'] = ip
    item['ver'] = ver
    item['id'] = i['id']
    item['key'] = i['key']
    if (ip == 0):
        print("    %s[%s] - %s%s - %sError: No IP found%s" %
                (subbold, name, dim, ip, alert, normal))
    else:
        try:
            d = tinytuya.OutletDevice(i['id'], ip, i['key'])
            if ver == "3.3":
                d.set_version(3.3)
            data = d.status()
            if 'dps' in data:
                item['dps'] = data
                state = alertdim + "Off" + dim
                try:
                    if '1' in data['dps'] or '20' in data['dps']:
                        state = bold + "On" + dim
                        print("    %s[%s] - %s%s - %s - DPS: %r" %
                            (subbold, name, dim, ip, state, data['dps']))
                    else:
                        print("    %s[%s] - %s%s - DPS: %r" %
                            (subbold, name, dim, ip, data['dps']))
                except:
                    print("    %s[%s] - %s%s - %sNo Response" %
                            (subbold, name, dim, ip, alertdim))
            else:
                print("    %s[%s] - %s%s - %sNo Response" %
                        (subbold, name, dim, ip, alertdim))
        except:
            print("    %s[%s] - %s%s - %sNo Response" %
                    (subbold, name, dim, ip, alertdim))
    polling.append(item)
# for loop

# Save polling data snapshot.json
current = {'timestamp' : time.time(), 'devices' : polling}
output = json.dumps(current, indent=4) 
print(bold + "\n>> " + normal + "Saving device snapshot data to " + SNAPSHOTFILE)
with open(SNAPSHOTFILE, "w") as outfile:
    outfile.write(output)