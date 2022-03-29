import colorsys
from dataclasses import dataclass
from typing import Tuple, List, Literal

import tinytuya

HSV = Tuple[float, float, float]

SCENE_CHANGE_MODES = {'static': '00', 'flash': '01', 'breath': '02'}
SCENE_NAMES = {'sleep': '04', 'romantic': '05', 'party': '06', 'relaxing': '07'}
SCENE_SPEED_MIN, SCENE_SPEED_MAX = 0x2828, 0x6464


class GalaxyProjector:
    """
    Works with the Galaxy Projector from galaxylamps.co:
    https://eu.galaxylamps.co/collections/all/products/galaxy-projector
    """

    def __init__(self, tuya_device_id: str, device_ip_addr: str, tuya_secret_key: str):
        self.device = tinytuya.BulbDevice(tuya_device_id, device_ip_addr, tuya_secret_key)
        self.device.set_version(3.3)
        self.state = GalaxyProjectorState()
        self.update_state()

    def set_device_power(self, *, on: bool):
        self.state.update(self.device.set_status(switch=20, on=on))

    def set_stars_power(self, *, on: bool):
        self.state.update(self.device.set_status(switch=102, on=on))

    def set_nebula_power(self, *, on: bool):
        self.state.update(self.device.set_status(switch=103, on=on))

    def set_rotation_speed(self, *, percent: float):
        value = int(10 + (1000 - 10) * min(max(percent, 0), 100) / 100)
        self.state.update(self.device.set_value(101, value))

    def set_stars_brightness(self, *, percent: float):
        self.state.update(self.device.set_white_percentage(percent))

    def set_nebula_color(self, *, hsv: HSV):
        """scene mode needs to be off to set static nebula color"""
        self.state.update(self.device.set_hsv(*hsv))

    def set_scene_mode(self, *, on: bool):
        self.state.update(self.device.set_mode('scene' if on else 'colour'))
        # differentiation between 'white' and 'colour' not relevant for this device

    def set_scene(self, parts: List["SceneTransition"]):
        """scene mode needs to be on"""
        output = SCENE_NAMES['party']  # scene name doesn't seem to matter
        for part in parts:
            output += hex(int(
                part.change_speed_percent / 100 * (SCENE_SPEED_MAX - SCENE_SPEED_MIN) + SCENE_SPEED_MIN))[2:]
            output += str(SCENE_CHANGE_MODES[part.change_mode])
            output += hsv2tuyahex(*part.nebula_hsv) + '00000000'
        self.device.set_value(25, output)
        self.update_state()  # return value of previous command is truncated and not usable for state update

    def update_state(self):
        self.state.update(self.device.status())


@dataclass
class SceneTransition:
    change_speed_percent: int
    change_mode: Literal['static', 'flash', 'breath']
    nebula_hsv: HSV


class GalaxyProjectorState:
    """
    Data Points (dps):
    20 device on/off
    21 work_mode: white(stars), colour (nebula), scene, music
    22 stars brightness 10-1000
    24 nebula hsv
    25 scene value
    26 shutdown timer
    101 stars speed 10-1000
    102 stars on/off
    103 nebula on/off
    """

    def __init__(self, dps=None):
        self.dps = dps or {}

    def update(self, payload):
        payload = payload or {'dps': {}}
        if 'Err' in payload:
            raise Exception(payload)
        self.dps.update(payload['dps'])

    @property
    def device_on(self) -> bool:
        return self.dps['20']

    @property
    def stars_on(self) -> bool:
        return self.dps['102']

    @property
    def nebula_on(self) -> bool:
        return self.dps['103']

    @property
    def scene_mode(self) -> bool:
        return self.dps['21'] == 'scene'

    @property
    def scene(self) -> List["SceneTransition"]:
        output = []
        hex_scene = self.dps['25']
        hex_scene_name = hex_scene[0:2]  # scene name doesn't seem to matter
        i = 2
        while i < len(hex_scene):
            hex_scene_speed = int(hex_scene[i:i + 4], 16)
            hex_scene_change = hex_scene[i + 4:i + 6]
            hex_scene_color = hex_scene[i + 6:i + 18]
            for k, v in SCENE_CHANGE_MODES.items():
                if v == hex_scene_change:
                    scene_change = k
                    break
            else:
                raise Exception(f'unknown scene change value: {hex_scene_change}')

            output.append(SceneTransition(
                change_speed_percent=round(
                    (hex_scene_speed - SCENE_SPEED_MIN) * 100 / (SCENE_SPEED_MAX - SCENE_SPEED_MIN)),
                change_mode=scene_change,
                nebula_hsv=tuyahex2hsv(hex_scene_color)
            ))
            i += 26
        return output

    @property
    def stars_brightness_percent(self):
        return int((self.dps['22'] - 10) * 100 / (1000 - 10))

    @property
    def rotation_speed_percent(self):
        return int((self.dps['101'] - 10) * 100 / (1000 - 10))

    @property
    def nebula_hsv(self) -> HSV:
        return tuyahex2hsv(self.dps['24'])

    def __repr__(self):
        return f'GalaxyProjectorState<{self.parsed_value}>'

    @property
    def parsed_value(self):
        return {k: getattr(self, k) for k in (
            'device_on', 'stars_on', 'nebula_on', 'scene_mode', 'scene', 'stars_brightness_percent',
            'rotation_speed_percent', 'nebula_hsv')}


def tuyahex2hsv(val: str):
    return tinytuya.BulbDevice._hexvalue_to_hsv(val, bulb="B")


def hsv2tuyahex(h: float, s: float, v: float):
    (r, g, b) = colorsys.hsv_to_rgb(h, s, v)
    hexvalue = tinytuya.BulbDevice._rgb_to_hexvalue(
        r * 255.0, g * 255.0, b * 255.0, bulb='B'
    )
    return hexvalue


if __name__ == '__main__':
    proj = GalaxyProjector(tuya_device_id=input('Tuya Device ID: '), device_ip_addr=input('Device IP Addr: '),
                           tuya_secret_key=input('Tuya Device Secret/Local Key: '))
    print()
    print('Current state:', proj.state.parsed_value)
    print()

    print('Press enter to continue')
    print()

    input('Turn stars off')
    proj.set_device_power(on=True)
    proj.set_stars_power(on=False)

    input('Turn stars on')
    proj.set_stars_power(on=True)

    input('Set stars brightness to 100%')
    proj.set_stars_brightness(percent=100)

    input('Set stars brightness to 0% (minimal)')
    proj.set_stars_brightness(percent=0)

    input('Set rotation speed to 100%')
    proj.set_rotation_speed(percent=100)

    input('Set rotation speed to 0%')
    proj.set_rotation_speed(percent=0)

    input('Set nebula color to red')
    proj.set_nebula_color(hsv=(0, 1, 1))

    input('Reduce nebula brightness')
    proj.set_nebula_color(hsv=(0, 1, .3))

    input('Show Scene')
    proj.set_scene([SceneTransition(change_speed_percent=80, change_mode='breath', nebula_hsv=(.5, 1, 1)),
                    SceneTransition(change_speed_percent=80, change_mode='breath', nebula_hsv=(0, 0, 1))])
    proj.set_scene_mode(on=True)

    input('Turn device off')
    proj.set_device_power(on=False)
