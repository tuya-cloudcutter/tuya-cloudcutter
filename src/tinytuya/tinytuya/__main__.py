# TinyTuya Module
# -*- coding: utf-8 -*-
"""
 Python module to interface with Tuya WiFi smart devices

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

 Run TinyTuya Setup Wizard:
    python -m tinytuya wizard
 This network scan will run if calling this module via command line:  
    python -m tinytuya <max_retry>

"""

# Modules
import tinytuya
import sys
from . import wizard

retries = tinytuya.MAXCOUNT
state = 0
color = True
retriesprovided = False

for i in sys.argv:
    if(i==sys.argv[0]):
        continue
    if(i.lower() == "wizard"):
        state = 1
    elif(i.lower() == "scan"):
        state = 0
    elif(i.lower() == "-nocolor"):
        color = False
    else:
        try:
            retries = int(i)
            retriesprovided = True
        except:
            state = 2

# State 0 = Run Scan
if(state == 0):
    if(retriesprovided):
        tinytuya.scan(retries, color)
    else:
        tinytuya.scan(color=color)

# State 1 = Run Setup Wizard
if(state == 1):
    if(retriesprovided):
        wizard.wizard(color, retries)
    else:
        wizard.wizard(color)

# State 2 = Show Usage
if(state == 2):
    print("TinyTuya [%s]\n" % (tinytuya.version))
    print("Usage:\n")
    print("    python -m tinytuya [command] [<max_retry>] [-nocolor] [-h]")
    print("")
    print("      command = scan        Scan local network for Tuya devices.")
    print("      command = wizard      Launch Setup Wizard to get Tuya Local KEYs.")
    print("      max_retry             Maximum number of retries to find Tuya devices [Default=15]")
    print("      -nocolor              Disable color text output.")
    print("      -h                    Show usage.")
    print("")

# End
