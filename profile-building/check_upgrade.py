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
import json
import os
import socket
import struct
import sys
import threading
import time

from tuya_api_connection import TuyaAPIConnection

global multicast_token, cancel_thread
multicast_token = None
cancel_thread = False


def print_help():
    print('Usage: python check_upgrade.py --input <uuid> <auth_key> <dev_id> <sec_key> <token>')
    print('   or: python check_upgrade.py --directory <directory> <token>')
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


def build_params(epoch_time, devId):
    params = {
        "a": "tuya.device.upgrade.get",
        "et": 1,
        "t": epoch_time,
        "devId": devId,
        "v": "4.3",
    }

    return params


def build_data(epoch_time, fwtype = '0'):
    data = {
        'type': fwtype,
        't': epoch_time
    }

    return data


def get_new_token():
    print('[!] No token provided.')
    print("[!] On any device on the same network as you're device running this script, please log into the Smart Life app ('Try as Guest' works fine if you do not already have an account)")
    print("[!]  Note: no real device should currently be in pairing mode, or the instructions below may not match.")
    print("[!]  - Start the add device procedure (hit '+' in the upper-right and select 'Add Device')")
    print("[!]  - Under 'Add Manually' select 'Socket (Wi-Fi)'")
    print("[!]  - Enter your network credentials as instructed")
    print("[!]  - Do not follow any of the instructions about putting a device into pairing mode, instead select 'next' until it asks the status of the indicator and select 'Blink Slowly'")
    print("[!]  - Select 'Go to Connect', then in your wifi selection screen, hit the back button to return to Smart Life.")
    print("[!] A new token should be sent to your network, and this script will continue.")
    print('[!] Note: this will join an unresponsive device to your account.  You can safely delete it afterwards.')
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
            msg = msg[16: msglen + 8].decode()
            msg = json.loads(msg)
            token = msg["token"]
            received_token = True
            s.close()
            multicast_token = token
        except KeyboardInterrupt:
            return
        except:
            pass


def run(directory: str, output_file_prefix: str, uuid: str, auth_key: str, dev_id: str, sec_key: str, token: str = None):
    if uuid is None or len(uuid) != 16:
        print_and_exit('required uuid was not found or was invalid (expected 16 characters)')
    if auth_key is None or len(auth_key) != 32:
        print_and_exit('required auth_key was not found or was invalid (expected 32 characters)')
    if dev_id is None or len(dev_id) != 22:
        print_and_exit('required dev_id was not found or was invalid (expected 22 characters)')
    if sec_key is None or len(sec_key) != 16:
        print_and_exit('required sec_key was not found or was invalid (expected 16 characters)')

    if token is None or len(token) != 14:
        token = get_new_token()

    if token is None:
        print_and_exit('[!] Error receiving new token.')

    region = token[:2]

    # Region information found at: https://airtake-public-data.oss-cn-hangzhou.aliyuncs.com/goat/pdf/1582271993811/Tuya%20Smart%20Cloud%20Platform%20Overview_Tuya%20Smart_Docs.pdf
    # AZ American west AWS Oregan Main Machine Room
    # UEAZ American east AZURE Virginia Machine Room
    if region == "AZ" or region == "UE":
        region = "us"
    # EU Europe AWS Frankfurt Machine Room
    elif region == "EU":
        region = "eu"
    # AY Asia Tencent ShangHai Core Machine Room
    elif region == "AY":
        region = "cn"
    # IN Indian AWS Mumbai Machine Room
    elif region == "IN":
        region = "in"
    else:
        print(f"[!] Unable to determine region from token provided (prefix {region})")
        sys.exit(4)

    reduced_token = token[2:]
    reduced_token = reduced_token[:8]
    assert len(reduced_token) == 8
    print(f'Using token: {token} uuid: {uuid} sec_key: {sec_key}')
    # tuya.device.upgrade.get encrypts with sec_key
    connection = TuyaAPIConnection(uuid, sec_key)
    url = f"http://a.tuya{region}.com/d.json"
    epoch_time = int(time.time())
    params = build_params(epoch_time, dev_id)
    response = None
    requestType = "POST"

    # Wifi firmware, type 0
    data = build_data(epoch_time, 0)
    response = connection.request(url, params, data, requestType)

    if response["success"] == True:
        if response.get('result') is not None:
            wifi_version = response['result']['version']
            firmware_wifi_upgrade_url = response['result']['url']
            print("[+] Wifi Firmware update available:")
            print(f"[+] Version: {wifi_version}")
            print(f"[+] Url: {firmware_wifi_upgrade_url}")
            with open(os.path.join(directory, output_file_prefix + f"_firmware_wifi_{wifi_version}.txt"), 'w') as f:
                f.write(firmware_wifi_upgrade_url)
        else:
            print("[+] No Wifi firmware update available.")
    elif response["success"] == False and response["errorCode"] == 'EXPIRE':
        print("[!] The token provided has either expired, or you are connected to the wrong region")
    else:
        print(response)
        
    # MCU firmware, type 9
    data = build_data(epoch_time, 9)
    response = connection.request(url, params, data, requestType)

    if response["success"] == True:
        if response.get('result') is not None:
            mcu_version = response['result']['version']
            firmware_mcu_upgrade_url = response['result']['url']
            print("[+] MCU Firmware update available:")
            print(f"[+] Version: {mcu_version}")
            print(f"[+] Url: {firmware_mcu_upgrade_url}")
            with open(os.path.join(directory, output_file_prefix + f"_firmware_mcu_{mcu_version}.txt"), 'w') as f:
                f.write(firmware_mcu_upgrade_url)
        else:
            print("[+] No MCU firmware update available.")
    elif response["success"] == False and response["errorCode"] == 'EXPIRE':
        print("[!] The token provided has either expired, or you are connected to the wrong region")
    else:
        print(response)

def run_input(uuid, auth_key, dev_id, sec_key, token=None):
    run('.\\', 'device', uuid, auth_key, dev_id, sec_key, token)


def run_directory(directory, token=None):
    uuid = None
    auth_key = None
    dev_id = None
    sec_key = None
    output_file_prefix = None

    dirListing = os.listdir(f'{directory}')

    for file in dirListing:
        if file.endswith('_uuid.txt'):
            uuid = read_single_line_file(os.path.join(directory, file))
            output_file_prefix = file.replace('_uuid.txt', '')
        elif file.endswith('_auth_key.txt'):
            auth_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_dev_id.txt'):
            dev_id = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_sec_key.txt'):
            sec_key = read_single_line_file(os.path.join(directory, file))

    if uuid is None:
        print('[!] uuid was not found')
        return
    if auth_key is None:
        print('[!] auth_key was not found')
        return
    if dev_id is None:
        print('[!] dev_id was not found')
        return
    if sec_key is None:
        print('[!] sec_key was not found')
        return

    run(directory, output_file_prefix, uuid, auth_key, dev_id, sec_key, token)


if __name__ == '__main__':

    if (sys.argv[2:]):
        if sys.argv[1] == '--input':
            if not sys.argv[7:]:
                print('Unrecognized input.')
                print_help()
            uuid = sys.argv[2]
            auth_key = sys.argv[3]
            dev_id = sys.argv[4]
            sec_key = sys.argv[5]
            token = sys.argv[9]
            run_input(uuid, auth_key, dev_id, sec_key, token)
        elif sys.argv[1] == '--directory':
            if not sys.argv[2:]:
                print('Unrecognized input.')
                print_help()
            directory = sys.argv[2]
            token = (None if len(sys.argv) < 4 else sys.argv[3])
            run_directory(directory, token)
    else:
        print_help()
