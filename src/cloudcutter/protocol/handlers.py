import base64
import datetime
import json
import os
import sys
import time
from typing import List

import tornado

from cloudcutter.protocol import mqtt

from ..crypto.tuyacipher import TuyaCipher, TuyaCipherKeyChoice
from ..device import DeviceConfig
from ..utils import object_to_json
from .transformers import ResponseTransformer

device_mac = ""
file_send_finished = False


def log_request(endpoint, request, decrypted_request_body, verbose_output: bool = False):
    clean_request_body: str = ""
    if len(request.body) > 0 or len(decrypted_request_body) > 0:
        if (decrypted_request_body is not None):
            clean_request_body = decrypted_request_body
        else:
            clean_request_body = request.body
        if type(clean_request_body) == bytes:
            clean_request_body = clean_request_body.decode()
        try:
            body_json = json.loads(clean_request_body)
            if body_json['hid'] is not None:
                mac_str = body_json['hid']
                mac_iter = iter(mac_str)
                global device_mac
                device_mac = ':'.join(a+b for a, b in zip(mac_iter, mac_iter))
        except:
            pass

    if verbose_output:
        # print a blank line for easier reading
        print("")
        print(f'[{datetime.datetime.now().time()} Log (Client)] Request: {request}')

        if len(clean_request_body) > 0:
            print(f'[{datetime.datetime.now().time()} LOG (Client)] ==== Request body ===')
            print(clean_request_body)
            print(f'[{datetime.datetime.now().time()} LOG (Client)] ==== End request body ===')
    else:
        print(f"Processing endpoint {endpoint}")


def log_response(response, verbose_output: bool = False):
    if verbose_output:
        print(f'[{datetime.datetime.now().time()} LOG (Server)] Response: ', response)


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
    def initialize(self, ipaddr: str, verbose_output: bool):
        self.ipaddr = ipaddr
        self.verbose_output = verbose_output

    def post(self):
        log_request(self.request.uri, self.request, self.request.body, self.verbose_output)
        response = {"caArr": None, "httpUrl": {"addr": f"http://{self.ipaddr}/d.json", "ips": [self.ipaddr]}, "mqttUrl": {"addr": f"{self.ipaddr}:1883", "ips": [self.ipaddr]}, "ttl": 600}
        response = object_to_json(response)
        log_response(response, self.verbose_output)
        self.finish(response)


class OldSDKGetURLHandler(TuyaHeadersHandler):
    def initialize(self, ipaddr: str, verbose_output: bool):
        self.ipaddr = ipaddr
        self.verbose_output = verbose_output

    def post(self):
        log_request(self.request.uri, self.request, self.request.body, self.verbose_output)
        response = {"caArr": None, "httpUrl": f"http://{self.ipaddr}/d.json", "mqttUrl": f"{self.ipaddr}:1883"}
        response = object_to_json(response)
        log_response(response, self.verbose_output)
        self.finish(response)


class OTAFilesHandler(tornado.web.StaticFileHandler):
    def initialize(self, path: str, graceful_exit_timeout: int, verbose_output: bool):
        self.root = self.path = self.absolute_path = path
        self.graceful_exit_timeout = graceful_exit_timeout
        self.verbose_output = verbose_output

    def prepare(self):
        log_request(self.request.uri, self.request, self.request.body, self.verbose_output)
        range_value = self.request.headers.get("Range", "bytes=0-0")
        # get_content_size() is not available in prepare without a lot of overriding work
        # total = self.get_content_size()
        log_response(range_value, self.verbose_output)

    def on_finish(self):
        range_value = self.request.headers.get("Range", "bytes=0-0")
        if range_value[:8].startswith('bytes=0-'):
            global file_send_finished
            file_send_finished = True
            # File send will always finish before mqtt sends a status of nearly complete
            # Leave all logic for shutting down in the mqtt progress check
        total = self.get_content_size()
        timestamp = ""
        if self.verbose_output:
            timestamp = str(datetime.datetime.now().time()) + " "
        print(f"[{timestamp}Firmware Upload] {self.request.uri} send complete, request range: {range_value}/{total}")


class DetachHandler(TuyaServerHandler):
    AUTHKEY_ENDPOINTS = ["tuya.device.active", "tuya.device.uuid.pskkey.get"]

    def initialize(self, schema_directory: os.PathLike, config: DeviceConfig, response_transformers: List[ResponseTransformer], endpoint_hooks, verbose_output: bool):
        super().initialize(config=config)
        self.schema_directory = schema_directory
        self.endpoint_hooks = endpoint_hooks
        self.response_transformers = response_transformers
        self.verbose_output = verbose_output

    def post(self):
        endpoint = self.get_query_argument("a")
        key_choice = TuyaCipherKeyChoice.AUTHKEY if endpoint in self.AUTHKEY_ENDPOINTS else TuyaCipherKeyChoice.SECKEY
        request_body = self.__decrypt_request_body(key_choice)
        log_request(endpoint, self.request, request_body, self.verbose_output)
        request_body = json.dumps(request_body)
        response = self.__rework_endpoint_response(endpoint, request_body)
        default_response = {"success": True, "t": int(time.time())}
        if not response:
            response = default_response
        log_response(response, self.verbose_output)
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
            # Default process, read the response from the base schema directory and return None if it doesn't exist
            endpoint_response_path = os.path.join(self.schema_directory, f"{endpoint}.json")
            if os.path.exists(endpoint_response_path):
                with open(endpoint_response_path, "r") as responsefs:
                    response = json.load(responsefs)
            else:
                print(f"!!! Endpoint response not found, using default response - {endpoint} (This is usually okay and safe to ignore unless something isn't working)")

        if response is None:
            return None

        for transformer in self.response_transformers:
            response = transformer.apply(response)

        return response

    def __decrypt_request_body(self, key_choice: TuyaCipherKeyChoice):
        try:
            body = self.get_argument('data')
            body = bytes.fromhex(body)
            decrypted = self.cipher.decrypt(body, key_choice).decode('utf-8')
        except:
            print(f"[!] Unable to decrypt device reponse.  PSKKEY/AUTHKEY do not match device.")
            exit(90)
        return decrypted
