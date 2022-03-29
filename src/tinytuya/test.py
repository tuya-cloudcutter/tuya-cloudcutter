#!/usr/bin/env python3
"""
 TinyTuya test for OutletDevice

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya
"""
import sys
import os
import time
import tinytuya

# Read command line options or set defaults
if (len(sys.argv) < 2) and not (("PLUGID" in os.environ) or ("PLUGIP" in os.environ)):
    print("TinyTuya (Tuya Interface) [%s]"%tinytuya.__version__)
    print("Usage: %s <DEVICEID> <DEVICEIP> <DEVICEKEY> <DEVICEVERS>\n" % sys.argv[0])
    print("    Required: <DEVICEID> is the Device ID e.g. 01234567891234567890")
    print("              <DEVICEIP> is the IP address of the smart plug e.g. 10.0.1.99")
    print("    Optional: <DEVICEKEY> is the Local Device Key (default 0123456789abcdef)")
    print("              <DEVICEVERS> is the Protocol Version 3.1 (default) or 3.3\n")
    print("    Note: You may also send values via Environmental variables: ")
    print("              DEVICEID, DEVICEIP, DEVICEKEY, DEVICEVERS\n")
    exit()
DEVICEID = sys.argv[1] if len(sys.argv) >= 2 else "01234567891234567890"
DEVICEIP = sys.argv[2] if len(sys.argv) >= 3 else "10.0.1.99"
DEVICEKEY = sys.argv[3] if len(sys.argv) >= 4 else "0123456789abcdef"
DEVICEVERS = sys.argv[4] if len(sys.argv) >= 5 else "3.1"

# Check for environmental variables and always use those if available 
DEVICEID = os.getenv("DEVICEID", DEVICEID)
DEVICEIP = os.getenv("DEVICEIP", DEVICEIP)
DEVICEKEY = os.getenv("DEVICEKEY", DEVICEKEY)
DEVICEVERS = os.getenv("DEVICEVERS", DEVICEVERS)

print("TinyTuya (Tuya Interface) [%s]\n"%tinytuya.__version__)
print('TESTING: Device %s at %s with key %s version %s' % (DEVICEID, DEVICEIP, DEVICEKEY,DEVICEVERS))

# Connect to device and fetch state
RETRY = 2
watchdog = 0
while True:
    try:
        d = tinytuya.OutletDevice(DEVICEID, DEVICEIP, DEVICEKEY)
        if DEVICEVERS == "3.3":
            d.set_version(3.3)
        data = d.status()
        if data:
            print("\nREADING TEST: Response %r" % data)
            print("State (bool, True is ON) %r\n" % data['dps']['1'])  
            break
        else:
            print("Incomplete response from device %s [%s]." % (DEVICEID,DEVICEIP))
    except:
        watchdog += 1
        if watchdog > RETRY:
            print(
                "TIMEOUT: No response from plug %s [%s] after %s attempts."
                % (DEVICEID,DEVICEIP, RETRY)
            )

# Toggle switch state
print("CONTROL TEST: Attempting to toggle power state of device")
switch_state = data['dps']['1']
for x in [(not switch_state), switch_state]:
    try:
        print("Setting state to: %r" % x)
        data = d.set_status(x)  # This requires a valid key
        time.sleep(2)
    except:
        print("TIMEOUT trying to toggle device power.")




