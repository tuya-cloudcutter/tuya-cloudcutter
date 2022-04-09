#!/usr/bin/env python3

##
# pull_active_response.py
# Get response for the tuya.device.active endpoint
# from server for use in device profiles.
# 
# Has been tested with light bulbs, and some of
# the parameters may be off for other devices, but
# the general concept can be replicated if needed.
# 
# Requires a valid device uuid, authkey, product
# key from a firmware dump as well as a valid activation
# token. Official mobile apps can generate valid tokens
# which can be sniffed over the network for use.
# 
##
import socket
import sslpsk
import sys
import ssl
from Cryptodome.Cipher import AES
import Cryptodome.Util.Padding as padding
from urllib.parse import urlparse
from hashlib import md5, sha256
import random
import json
import base64

class TuyaAPIConnection(object):
    def __init__(self, uuid: str, authkey: str, psk: str = None):
        self.psk = psk.encode('utf-8') if psk else b''
        self.authkey = authkey.encode('utf-8')
        self.uuid = uuid.encode('utf-8')

    def request(self, url: str, params: dict, data: dict, method: str = 'POST') -> dict:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        psk_wrapped = parsed_url.scheme == "https"
        port = parsed_url.port or (443 if psk_wrapped else 80)

        params["et"] = 1
        params["uuid"] = self.uuid.decode("utf-8")

        querystring = self._build_querystring(params)
        requestline = f"{parsed_url.path}{querystring}"
        body = self._encrypt_data(data)
        http_request = self._build_request(method, hostname, requestline, body)

        with self._make_socket(hostname, port, psk_wrapped) as socket:
            socket.send(http_request)
            datas = socket.recv(10000)
            response_body = datas.split(b"\r\n\r\n")[1].decode("utf-8").strip()
            result = json.loads(response_body)["result"]
            result = base64.b64decode(result)
            result = self._decrypt_data(result)
            result = result.decode('utf-8')
            result = json.loads(result)
            return result


    def _encrypt_data(self, data: dict):
        jsondata = json.dumps(data, separators=(",",":"))
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
        print(signature_body)
        signature = md5(signature_body).hexdigest()
        query += "&sign=" + signature
        print(query)
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
            x = lambda hint: self._psk_and_pskid(hint)
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


if __name__ == '__main__':
    if not sys.argv[3:]:
        print('Usage: python pull_active_response.py <uuid> <authkey> <token> [<product key / firmware key>]', file=sys.stderr)
        sys.exit(1)


    uuid = sys.argv[1]
    authkey = sys.argv[2]

    token = sys.argv[3]
    prodkey = sys.argv[4] if len(sys.argv) > 4 else 'keytg5kq8gvkv9dh'

    if len(token) != 14:
        print('Token must be 14 chars')
        sys.exit(2)

    token = token[2:]
    token = token[:8]
    assert len(token) == 8
    print('Using token:', token, 'prodkey:', prodkey, file=sys.stderr)
    connection = TuyaAPIConnection(uuid=uuid, authkey=authkey)
    url="http://a.tuyaeu.com/d.json"
    t=37
    params = {
            "a": "tuya.device.active",
            "t": t,
            "v": "4.4"
    }
    data = {'token': token, 'softVer': '2.9.16', 'productKey': prodkey, 'protocolVer': '2.2', 'baselineVer': '40.00', 'productKeyStr': prodkey, 'devId': 'bf27a86f49bf35f70c7ign', 'hid': '508a06b10603', 'modules': '[{"type":9,"softVer":"2.9.16","online":true}]', 'devAttribute': 515, 'cadVer': '1.0.2', 'cdVer': '1.0.0', 'options': '{"isFK":true}', 't': t}
    print(json.dumps(connection.request(url, params, data, "POST"), separators=(',',':')))
