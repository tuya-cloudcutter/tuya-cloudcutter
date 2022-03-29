# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - Example script to monitor state changes with Tuya devices.

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

"""
import tinytuya

# tinytuya.set_debug(True)

d = tinytuya.OutletDevice('DEVICEID', 'DEVICEIP', 'DEVICEKEY')
d.set_version(3.3)
d.set_socketPersistent(True)

print(" > Send Request for Status < ")
payload = d.generate_payload(tinytuya.DP_QUERY)
d.send(payload)

print(" > Begin Monitor Loop <")
while(True):
    # See if any data is available
    data = d.receive()
    print('Received Payload: %r' % data)

    # Send keyalive heartbeat
    print(" > Send Heartbeat Ping < ")
    payload = d.generate_payload(tinytuya.HEART_BEAT)
    d.send(payload)

    # Uncomment if you want the monitor to constantly request status - otherwise you
    # will only get updates when state changes
    # print(" > Send Request for Status < ")
    # payload = d.generate_payload(tinytuya.DP_QUERY)
    # d.send(payload)

    # Uncomment if your device provides power monitoring data but it is not updating
    # Some devices require a UPDATEDPS command to force measurements of power.
    # print(" > Send DPS Update Request < ")
    # Most devices send power data on DPS indexes 18, 19 and 20
    # payload = d.generate_payload(tinytuya.UPDATEDPS,['18','19','20'])
    # Some Tuya devices will not accept the DPS index values for UPDATEDPS - try:
    # payload = d.generate_payload(tinytuya.UPDATEDPS)
    # d.send(payload)

    