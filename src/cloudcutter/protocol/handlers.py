import base64
import json
import os
import time
from typing import List

import tornado

from ..crypto.tuyacipher import TuyaCipher, TuyaCipherKeyChoice
from ..device import DeviceConfig
from .transformers import ResponseTransformer
from ..utils import object_to_json


class TuyaHeadersHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "text/plain; charset=utf-8")
        self.set_header("Connection", "keep-alive")
        self.set_header("Server", "Tuya-Sec")

class TuyaServerHandler(TuyaHeadersHandler):
    def initialize(self, config: DeviceConfig):
        self.cipher = TuyaCipher(config.get_bytes(DeviceConfig.AUTH_KEY))
        self.cipher.set_seckey(config.get_bytes(DeviceConfig.SEC_KEY))
        self.config = config

    def reply(self, key_choice, response: dict):
        encrypted = self.cipher.encrypt(response, key_choice)
        encrypted = base64.b64encode(encrypted).decode("utf-8")

        timestamp = int(time.time())
        response = {"result": encrypted, "t": timestamp}
        signature = self.cipher.sign_server(response, key_choice)

        response["sign"] = signature
        response = object_to_json(response) + "\n"

        self.finish(response)


class GetURLHandler(TuyaHeadersHandler):
    def initialize(self, ipaddr: str):
        self.ipaddr = ipaddr

    def post(self):
        response = {"caArr":None,"httpUrl":{"addr":f"http://{self.ipaddr}/d.json","ips":[self.ipaddr]},"mqttUrl":{"addr":f"{self.ipaddr}:1883","ips":[self.ipaddr]},"ttl":600}
        response = object_to_json(response)

        self.finish(response)


class OldSDKGetURLHandler(TuyaHeadersHandler):
    def initialize(self, ipaddr: str):
        self.ipaddr = ipaddr

    def post(self):
        response = {"caArr":None,"httpUrl":f"http://{self.ipaddr}/d.json","mqttUrl":f"{self.ipaddr}:1883"}
        response = object_to_json(response)

        self.finish(response)


class FilesHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        if not url_path or url_path.endswith('/'):
            url_path = url_path + str('index.html')
        return url_path


class DetachHandler(TuyaServerHandler):
    AUTHKEY_ENDPOINTS = ["tuya.device.active", "tuya.device.uuid.pskkey.get"]

    def initialize(self, profile_directory: os.PathLike, config: DeviceConfig, response_transformers: List[ResponseTransformer], endpoint_hooks=None):
        super().initialize(config=config)
        self.profile_directory = profile_directory
        self.endpoint_hooks = endpoint_hooks
        self.response_transformers = response_transformers

    def post(self):
        endpoint = self.get_query_argument("a")
        key_choice = TuyaCipherKeyChoice.AUTHKEY if endpoint in self.AUTHKEY_ENDPOINTS else TuyaCipherKeyChoice.SECKEY
        request_body = self.__decrypt_request_body(key_choice)
        response = self.__rework_endpoint_response(endpoint, request_body)

        default_response = {"success": True, "t": int(time.time())}
        if not response:
            response = default_response

        print(f'{endpoint} - response:', response)

        self.reply(key_choice, response)
        
    def __rework_endpoint_response(self, endpoint, request_body):
        response = None
        endpoint_hook_response = None
        if self.endpoint_hooks is not None:
            # Check if any endpoint hook has a response and if so, use it as a response
            # while applying transformations anyway.
            # Otherwise, load the response from a file as usual.
            endpoint_hook = self.endpoint_hooks.get(endpoint, None)
            if endpoint_hook is not None:
                endpoint_hook_response = endpoint_hook(self, endpoint, request_body)

        if endpoint_hook_response is not None:
            response = endpoint_hook_response
        else:
            # Default process, read the response from the profile directory and return None if it doesn't exist
            endpoint_response_path = os.path.join(self.profile_directory, f"{endpoint}.json")
            if os.path.exists(endpoint_response_path):
                with open(endpoint_response_path, "r") as responsefs:
                    response = json.load(responsefs)

        if response is None:
            return None
            
        for transformer in self.response_transformers:
            response = transformer.apply(response)

        return response

    def __decrypt_request_body(self, key_choice: TuyaCipherKeyChoice):
        body = self.get_argument('data')
        body = bytes.fromhex(body)
        decrypted = self.cipher.decrypt(body, key_choice).decode('utf-8')
        return json.loads(decrypted)
