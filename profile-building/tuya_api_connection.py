import base64
import json
import random
import socket
import ssl
import sys
from hashlib import md5, sha256
from urllib.parse import urlparse

import Cryptodome.Util.Padding as padding
import sslpsk3 as sslpsk
from Cryptodome.Cipher import AES


class TuyaAPIConnection(object):
    def __init__(self, uuid: str, auth_key: str, psk: str = None):
        self.psk = psk.encode('utf-8') if psk else b''
        self.authkey = auth_key.encode('utf-8')
        self.uuid = uuid.encode('utf-8')

    def request(self, url: str, params: dict, data: dict, method: str = 'POST') -> dict:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        psk_wrapped = parsed_url.scheme == "https"
        port = parsed_url.port or (443 if psk_wrapped else 80)
        querystring = self._build_querystring(params)
        requestline = f"{parsed_url.path}{querystring}"
        body = self._encrypt_data(data)
        http_request = self._build_request(method, hostname, requestline, body)

        with self._make_socket(hostname, port, psk_wrapped) as socket:
            try:
                socket.send(http_request)
                datas = socket.recv(10000)
                response_body = datas.split(b"\r\n\r\n")[1].decode("utf-8").strip()
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
                print("[!] Unable to get a response from Tuya API, or response was malformed.")
                print(f"[!] {url} must not be blocked in order to pull data from the Tuya API.")
                if (response_body_json is not None):
                    print(f"[!] Error message: {response_body_json['errorCode']}")
                else:
                    print(f"[!] Error message: {response_body}")
                    print(f"[!] Error message: {exception}")
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

    def _build_request(self, method: str, hostname: str, requestline: str, body: str):
        headers = {
            "Host": hostname,
            "User-Agent": "TUYA_IOT_SDK",
            "Connection": "keep-alive"
        }

        if body:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            headers["Content-Length"] = str(len(body))

        headers_formatted = "\r\n".join([f"{k}: {v}" for k, v in headers.items()])
        request = f"{method} {requestline} HTTP/1.1\r\n{headers_formatted}\r\n\r\n{body}"
        return request.encode("utf-8")

    def _make_socket(self, host: str, port: int, encrypted=True):
        csocket = socket.create_connection((host, port))
        if encrypted:
            def x(hint): return self._psk_and_pskid(hint)
            csocket = sslpsk.wrap_socket(csocket, ssl_version=ssl.PROTOCOL_TLSv1_2, ciphers='PSK-AES128-CBC-SHA256', psk=x)
        return csocket

    def _psk_and_pskid(self, hint):
        if not self.psk:
            return self._psk_id_v1(hint)
        return self._psk_id_v2(hint)

    def _psk_id_v1(self, hint):
        authkey_hash = md5(self.authkey).digest()
        uuid_hash = md5(self.uuid).digest()
        rand_data = random.randbytes(0x10)
        init_id = b'\x01' + rand_data + uuid_hash + b'_' + authkey_hash
        init_id = init_id.replace(b'\x00', b'?')
        iv = md5(init_id[1:]).digest()
        key = md5(hint[-16:]).digest()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        self.psk = cipher.encrypt(init_id[1:33])
        return (self.psk, init_id)

    def _psk_id_v2(self, hint):
        uuid_hash = sha256(self.uuid).digest()
        rand_data = random.randbytes(0x10)
        init_id = b'\x02' + rand_data + uuid_hash
        return (self.psk, init_id.replace(b'\x00', b'?'))
