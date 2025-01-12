import base64
import json
import requests
import sys
import traceback
from hashlib import md5
from urllib.parse import urlparse

import Crypto.Util.Padding as padding
from Crypto.Cipher import AES


class TuyaAPIConnection(object):
    def __init__(self, uuid: str, auth_key: str):
        self.authkey = auth_key.encode('utf-8')
        self.uuid = uuid.encode('utf-8')

    def request(self, url: str, params: dict, data: dict, method: str = 'POST') -> dict:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        querystring = self._build_querystring(params)
        body = self._encrypt_data(data)

        # print(f"[+] Url: {url + querystring}")
        # print(f"[+] Parameters: {params}")
        # print(f"[+] Body: {body}")
        # print(f"[+] Unencrypted Body: {data}")

        try:
            response_body = None
            response_body_json = None
            user_agent = "TUYA_IOT_SDK" # Older alternate: ESP8266SDK
            headers = {"Host":f"{hostname}","User-Agent":f"{user_agent}","Connection":"keep-alive"}
            match method.upper():
                case "GET":
                    # print(f"[+] Headers: {headers}")
                    response = requests.get(url + querystring, headers=headers)
                case "POST":
                    headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
                    headers["Content-Length"] = str(len(body))
                    # print(f"[+] Headers: {headers}")
                    response = requests.post(url + querystring, data=body, headers=headers)
            response_body = response.text.strip()
            # print(response_body)
            response_body_json = json.loads(response_body)
            result = response_body_json["result"]
            result = base64.b64decode(result)
            result = self._decrypt_data(result)
            result = result.decode('utf-8')
            result = json.loads(result)
            # print(result)
            return result
        except Exception as exception:
            print(traceback.format_exc())
            print("[!] Unable to get a response from Tuya API, or response was malformed.")
            print(f"[!] {url} must not be blocked in order to pull data from the Tuya API.")
            if (response_body_json is not None and 'errorCode' in response_body_json):
                print(f"[!] Error message: {response_body_json['errorCode']}")
            else:
                print(f"[!] Response Body: {response_body}")
                print(f"[!] Exception: {exception}")
                # print(f"[!] Response: {response.text}")
            sys.exit(3)

    def _encrypt_data(self, data: dict):
        jsondata = json.dumps(data, separators=(",", ":"))
        jsondata = padding.pad(jsondata.encode("utf-8"), block_size=16)
        cipher = self._build_cipher()
        encrypted = cipher.encrypt(jsondata)
        return f"data={encrypted.hex().upper()}"

    def _decrypt_data(self, data: bytes):
        cipher = self._build_cipher()
        return padding.unpad(cipher.decrypt(data), block_size=16)

    def _build_cipher(self):
        return AES.new(self.authkey[:16], AES.MODE_ECB)

    def _build_querystring(self, params: dict):
        sorted_params = sorted(list(params.items()))
        query = "&".join([f"{k}={v}" for k, v in sorted_params])
        signature_body = query.replace("&", "||").encode("utf-8")
        signature_body += f"||{self.authkey.decode('utf-8')}".encode("utf-8")
        # print(signature_body)
        signature = md5(signature_body).hexdigest()
        query += "&sign=" + signature
        # print(query)
        return f"?{query}"
