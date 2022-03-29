# TinyTuya Example
# -*- coding: utf-8 -*-
"""
 TinyTuya - Smart Bulb RGB Test

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

"""
import tinytuya
import time
import os
import random

DEVICEID = "01234567891234567890"
DEVICEIP = "10.0.1.99"
DEVICEKEY = "0123456789abcdef"
DEVICEVERS = "3.3"

# Check for environmental variables and always use those if available
DEVICEID = os.getenv("DEVICEID", DEVICEID)
DEVICEIP = os.getenv("DEVICEIP", DEVICEIP)
DEVICEKEY = os.getenv("DEVICEKEY", DEVICEKEY)
DEVICEVERS = os.getenv("DEVICEVERS", DEVICEVERS)

print("TinyTuya - Smart Bulb RGB Test [%s]\n" % tinytuya.__version__)
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

# Set to full brightness warm white
print('\nWarm White Test')
d.set_white()
time.sleep(2)

# Power Control Test
print('\nPower Control Test')
print('    Turn off lamp')
d.turn_off()
time.sleep(2)
print('    Turn on lamp')
d.turn_on()
time.sleep(2)

# Dimmer Test
print('\nDimmer Control Test')
for level in range(11):
    print('    Level: %d%%' % (level*10))
    d.set_brightness_percentage(level*10)
    time.sleep(1)

# Colortemp Test
print('\nColortemp Control Test (Warm to Cool)')
for level in range(11):
    print('    Level: %d%%' % (level*10))
    d.set_colourtemp_percentage(level*10)
    time.sleep(1)

# Flip through colors of rainbow - set_colour(r, g, b):
print('\nColor Test - Cycle through rainbow')
rainbow = {"red": [255, 0, 0], "orange": [255, 127, 0], "yellow": [255, 200, 0],
           "green": [0, 255, 0], "blue": [0, 0, 255], "indigo": [46, 43, 95],
           "violet": [139, 0, 255]}
for x in range(2):
    for i in rainbow:
        r = rainbow[i][0]
        g = rainbow[i][1]
        b = rainbow[i][2]
        print('    %s (%d,%d,%d)' % (i, r, g, b))
        d.set_colour(r, g, b)
        time.sleep(2)
    print('')

# Turn off
d.turn_off()
time.sleep(1)

# Random Color Test
d.turn_on()
print('\nRandom Color Test')
for x in range(10):
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    print('    RGB (%d,%d,%d)' % (r, g, b))
    d.set_colour(r, g, b)
    time.sleep(2)

# Test Modes
print('\nTesting Bulb Modes')
print('    White')
d.set_mode('white')
time.sleep(2)
print('    Colour')
d.set_mode('colour')
time.sleep(2)
print('    Scene')
d.set_mode('scene')
time.sleep(2)
print('    Music')
d.set_mode('music')
time.sleep(2)

# Done
print('\nDone')
d.set_white()
