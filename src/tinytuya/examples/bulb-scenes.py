# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - RGB SmartBulb - Scene Test for Bulbs with DPS Index 25

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

"""
import tinytuya
import time

DEVICEID = "01234567891234567890"
DEVICEIP = "10.0.1.99"
DEVICEKEY = "0123456789abcdef"
DEVICEVERS = "3.3"

print("TinyTuya - Smart Bulb String Scenes Test [%s]\n" % tinytuya.__version__)
print('TESTING: Device %s at %s with key %s version %s' %
      (DEVICEID, DEVICEIP, DEVICEKEY, DEVICEVERS))

# Connect to Tuya BulbDevice
d = tinytuya.BulbDevice(DEVICEID, DEVICEIP, DEVICEKEY)
if(DEVICEVERS == '3.3'):    # IMPORTANT to always set version 
    d.set_version(3.3)
else:
    d.set_version(3.1)
# Keep socket connection open between commands
d.set_socketPersistent(True)  

# Show status of device
data = d.status()
print('\nCurrent Status of Bulb: %r' % data)

# Set Mode to Scenes
print('\nSetting bulb mode to Scenes')
d.set_mode('scene')

# Determine bulb type - if it has index 25 it uses strings to set scene
if("dps" in data):
    if("25" in data["dps"]):
        print('\n   [Bulb Type B] String based scenes compatible smartbulb detected.')

        # Example: Color rotation 
        print('    Scene - Color Rotation')
        d.set_value(25, '07464602000003e803e800000000464602007803e803e80000000046460200f003e803e800000000464602003d03e803e80000000046460200ae03e803e800000000464602011303e803e800000000')
        time.sleep(10)

        # Example: Read scene
        print('    Scene - Reading Light')
        d.set_value(25, '010e0d0000000000000003e803e8')
        time.sleep(5)

        # You can pull the scene strings from your smartbulb by running the async_send_receive.py script
        # and using the SmartLife app to change between scenes.  

    else:
        print('\n   [Bulb Type A] Your smartbulb does not appear to support string based scenes.')

        # Rotate through numeric scenes
        for n in range(1, 4):
            print('    Scene - %d' % n)
            d.set_scene(n)
            time.sleep(5)

# Done
print('\nDone')
d.set_white()
