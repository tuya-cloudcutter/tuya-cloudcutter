import tinytuya
import colorsys
import time

# Set these values for your device
id = DEVICEID
cmd_code = 'colour_data_v2'  # look at c.getstatus(id) to see what code should be used

# Connect to Tuya Cloud - uses tinytuya.json 
c = tinytuya.Cloud()

# Function to set color via RGB values - Bulb type B
def set_color(rgb):
    hsv = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    commands = {
        'commands': [{
            'code': cmd_code,
            'value': {
                "h": int(hsv[0] * 360),
                "s": int(hsv[1] * 1000),
                "v": int(hsv[2] * 1000)
            }
        }]
    }
    c.sendcommand(id, commands)

# Rainbow values
rainbow = {"red": (255, 0, 0), "orange": (255, 127, 0), "yellow": (255, 200, 0),
           "green": (0, 255, 0), "blue": (0, 0, 255), "indigo": (46, 43, 95),
           "violet": (139, 0, 255)}

# Rotate through the rainbow
for color in rainbow:
    print("Changing color to %s" % color)
    set_color(rainbow[color])
    time.sleep(5)
