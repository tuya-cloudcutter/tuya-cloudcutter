# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - Example showing async persistent connection to device with
 continual loop watching for device updates.

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

    # Option - Some plugs require an UPDATEDPS command to update their power data points

    # print(" > Send Request for Status < ")
    # payload = d.generate_payload(tinytuya.DP_QUERY)
    # d.send(payload)

    # # See if any data is available
    # data = d.receive()
    # print('Received Payload: %r' % data)

    # print(" > Send DPS Update Request < ")
    # payload = d.generate_payload(tinytuya.UPDATEDPS,['18','19','20'])
    # Some Tuya devices will not accept the DPS index values for UPDATEDPS - try:
    # payload = d.generate_payload(tinytuya.UPDATEDPS)
    # d.send(payload)
    
    # # See if any data is available
    # data = d.receive()
    # print('Received Payload: %r' % data)
    