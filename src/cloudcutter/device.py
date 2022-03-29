import json
import os
from typing import Dict

DEFAULT_AUTH_KEY = b'A' * 16
DEVICE_PROFILE_FILE_NAME = "profile"


class DeviceConfig(object):
    AUTH_KEY = 'auth_key'
    SEC_KEY = 'sec_key'
    LOCAL_KEY = 'local_key'
    UUID = 'uuid'
    DEVICE_ID = 'device_id'
    PSK = 'psk'
    CHIP_FAMILY = 'chip_family'

    def __init__(self, config: Dict):
        self.config = config.copy()

    def set(self, key: str, value):
        self.config[key] = value

    def get(self, key: str, default = None):
        return self.config.get(key, default)

    def get_bytes(self, key: str, encoding = 'utf-8', default = None):
        return self.get(key, default).encode(encoding)

    def write(self, config_file_path: os.PathLike):
        with open(config_file_path, "w") as fs:
            json.dump(self.config, fs)

    @classmethod
    def read(cls, config_file_path: os.PathLike):
        with open(config_file_path, "r") as fs:
            return cls(json.load(fs))