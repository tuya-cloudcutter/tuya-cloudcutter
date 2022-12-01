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
import sslpsk2 as sslpsk
import sys
import ssl
from Cryptodome.Cipher import AES
import Cryptodome.Util.Padding as padding
from urllib.parse import urlparse
from hashlib import md5, sha256
import random
import json
import base64
import time
import os
import struct
import threading

global multicast_token, cancel_thread
multicast_token = None
cancel_thread = False

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

def print_help():
    print('Usage: python pull_active_response.py --input <uuid> <authkey> [<product key / firmware key>] <softVer> <baselineVer> <region> <token>')
    print('   or: python pull_active_response.py --directory <directory> <region> <token>')
    sys.exit(1)

def read_single_line_file(path):
    with open(path, 'r') as file:
        fileContents = file.read()
        if fileContents.__contains__('\n'):
            return None
        return fileContents

def print_and_exit(printText):
    print(printText)
    sys.exit(2)

def build_params(epoch_time, uuid):
    params = {
        "a": "tuya.device.active",
        "t": epoch_time,
        "uuid": uuid,
        "v": "4.4",
        "et": 1,
    }

    return params

def build_data(epoch_time, token, product_key, software_version, baseline_version = '40.00', cad_version = '1.0.2', cd_version = '1.0.0', protocol_version = '2.2', product_key_is_firmware_key: bool = True):
    data = {
        'token': token,
        'productKey': product_key,
        'softVer': software_version,
        'protocolVer': protocol_version,
        'baselineVer': baseline_version,
        'options': '{"isFK":' + str(product_key_is_firmware_key).lower() + '}',
        'cadVer': cad_version,
        'cdVer': cd_version,
        't': epoch_time,
    }
        
    return data

def get_new_token():
    print('[!] No token provided.  On the same network, please log into Smart Life, start the add device procedure, select \'Socket (Wi-Fi)\', enter your network credentials, next until it asks the status of the indicator and select \'Blink Slowly\', select \'Go to Connect\', then in your wifi selection screen, hit the back button to return to Smart Life.  A new token should be sent to your network, and this script will continue.')
    print('[!] Note: this will join the device to your account.  You can safely delete it afterwards.')
    print('[+] Waiting for multicast token from app...')

    global multicast_token, cancel_thread

    try:
        thread = threading.Thread(target=receive_token, args=[])
        thread.start()
        while multicast_token is None:
            time.sleep(0.25)
            pass
    except:
        cancel_thread = True
        print('[!] Cancelled waiting for token.')

    return multicast_token

def receive_token():
    global multicast_token, cancel_thread
    received_token = False
    while received_token == False and cancel_thread == False:
        s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        s.bind(('0.0.0.0', 6669))
        s.settimeout(2)
        try:
            # despite suggestions of being unused, addr must remain present, or this will fail
            msg, addr = s.recvfrom(255)
            (msglen,) = struct.unpack(">I", msg[12:16])
            msg = msg[16 : msglen + 8].decode()
            msg = json.loads(msg)
            token = msg["token"]
            received_token = True
            s.close()
            multicast_token = token
        except KeyboardInterrupt:
            return
        except:
            pass

def run(directory: str, output_file_prefix: str, uuid: str, product_key: str, auth_key: str, software_version: str, baseline_version: str = '40.00', cad_version: str = '1.0.2', cd_version: str = '1.0.0', protocol_version = '2.2', product_key_is_firmware_key: bool = True, region: str = 'us', token: str = None):
    knownRegions = [ 'us', 'eu' ]

    if uuid is None or len(uuid) != 16:
        if product_key is not None and len(product_key) == 16:
            uuid = product_key
        else:
            print_and_exit('required uuid was not found or was invalid (expected 16 characters)')
    if auth_key is None or len(auth_key) != 32:
        print_and_exit('required authkey was not found or was invalid (expected 32 characters)')
    if product_key is None or len(product_key) != 16:
        print_and_exit('required prodkey was not found or was invalid (expected 16 characters)')
    if software_version is None or len(software_version) < 5:
        print_and_exit('required softVer was not found or was invalid (expected >= 5 characters)')
    if cad_version is None or len(cad_version) < 5:
        print_and_exit('required cadVer was not found or was invalid (expected >= 5 characters)')
    if baseline_version is None or len(baseline_version) < 5:
        print_and_exit('required baselineVer was not found or was invalid (expected 5 characters)')
    if region is None or region not in knownRegions:
        print_and_exit(f'required region was not found or was invalid.  Known regions: {knownRegions}')
    
    if token is None or len(token) != 14:
        token = get_new_token()

    if token is None:
        print_and_exit('[!] Error receiving new token.')

    token = token[2:]
    token = token[:8]
    assert len(token) == 8
    print('Using token:', token, 'prodkey:', product_key, file=sys.stderr)
    connection = TuyaAPIConnection(uuid=uuid, authkey=auth_key)
    url = f"http://a.tuya{region}.com/d.json"
    epoch_time = int(time.time())

    params = build_params(epoch_time, uuid)
    data = build_data(epoch_time, token, product_key, software_version, baseline_version, cad_version, cd_version, protocol_version, product_key_is_firmware_key)

    response = connection.request(url, params, data, "POST")

    if response["success"] == False:
        print(response)
    else:
        print(f"[+] Schema Id: {response['result']['schemaId']}")
        print(f"[+] Schema: {response['result']['schema']}")
        with open(os.path.join(directory, output_file_prefix + "_schema_id.txt"), 'w') as f:
            f.write(response['result']['schemaId'])
        with open(os.path.join(directory, output_file_prefix + "_schema.txt"), 'w') as f:
            f.write(response['result']['schema'])

def run_input(uuid, authkey, product_key, software_version, baseline_version = '40.00', cad_version = '1.0.2', cd_version = '1.0.0', protocol_version = '2.2', product_key_is_firmware_key: bool = True, region = 'us', token = None):
    run('.\\', 'device', uuid, product_key, authkey, software_version, baseline_version, cad_version, cd_version, protocol_version, product_key_is_firmware_key, region, token)

def run_directory(directory, region = 'us', token = None):
    has_schema = False
    uuid = None
    auth_key = None
    product_key = None
    firmware_key = None
    software_version = None
    baseline_version = '40.00'
    cad_version = '1.0.2'
    cd_version = '1.0.0'
    protocol_version = '2.2'
    product_key_is_firmware_key = False
    output_file_prefix = None

    dirListing = os.listdir(f'{directory}')

    for file in dirListing:
        if file.endswith('_uuid.txt'):
            uuid = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_auth_key.txt'):
            auth_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_product_key.txt'):
            product_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_firmware_key.txt'):
            firmware_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_swv.txt'):
            software_version = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_bv.txt'):
            baseline_version = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_chip.txt'):
            output_file_prefix = file.replace('_chip.txt', '')
        elif file.endswith('_schema_id.txt'):
            has_schema = True
    
    if has_schema:
        print('[+] Schema already present')
        return

    if product_key is None:
        product_key = firmware_key
        product_key_is_firmware_key = True

    if uuid is None:
        print('[!] uuid was not found')
        return
    if auth_key is None:
        print('[!] authkey was not found')
        return
    if product_key is None:
        print('[!] prodkey was not found')
        return
    if software_version is None:
        print('[!] softVer was not found')
        return
    if baseline_version is None:
        print('[!] baselineVer was not found')
        return

    run(directory, output_file_prefix, uuid, product_key, auth_key, software_version, baseline_version, cad_version, cd_version, protocol_version, product_key_is_firmware_key, region, token)

if __name__ == '__main__':
   
    if (sys.argv[2:]):
        if sys.argv[1] == '--input':
            if not sys.argv[5:]:
                print('Unrecognized input.')
                print_help()
            uuid = sys.argv[2]
            authkey = sys.argv[3]
            prodkey = sys.argv[4]
            softVer = sys.argv[5]
            cadVer = ('1.0.2' if sys.argv[6] is None else sys.argv[6])
            baselineVer = ('40.00' if sys.argv[7] is None else sys.argv[7])
            region = ('us' if sys.argv[8] is None else sys.argv[8])
            token = sys.argv[9]
            run_input(uuid, authkey, prodkey, softVer, cadVer, baselineVer, region, token)
        elif sys.argv[1] == '--directory':
            if not sys.argv[2:]:
                print('Unrecognized input.')
                print_help()
            directory = sys.argv[2]
            print(len(sys.argv))
            region = ('us' if len(sys.argv) < 4 else sys.argv[3])
            token = (None if len(sys.argv) < 5 else sys.argv[4])
            run_directory(directory, region, token)
    else:
        print_help()
