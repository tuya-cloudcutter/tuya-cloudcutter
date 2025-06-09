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
    print('Usage: python pull_schema.py --input <uuid> <auth_key> <product_key or empty string ""> <firmware_key or empty string ""> <software_version> <baseline_version> <token>')
    print('   or: python pull_schema.py --directory <directory> <token>')
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
        "et": 1,
        "t": epoch_time,
        "uuid": uuid,
        "v": "4.4",
    }

    return params


def build_data(epoch_time, reduced_token, firmware_key, product_key, software_version, mcu_software_version, baseline_version='40.00', cad_version='1.0.2', cd_version='1.0.0', protocol_version='2.2', is_fk: bool = True):
    data = {
        'token': reduced_token,
        'softVer': software_version,
        'productKey': product_key,
        'protocolVer': protocol_version,
        'baselineVer': baseline_version,
        'productKeyStr': firmware_key,
        #'devId': '', # 20 char, is re-activating an already activated device, possibly prevents a devId change?
        #'hid': '', # 12 char, unsure where it gets this value.  Possibly a TuyaMCU id of some sort.
        #'devAttribute': 515,
        'modules': '[{"type":9,"softVer":"' + mcu_software_version + '","online":true}]', # for TuyaMCU devices, version varies.  Alternately "modules": "[{"otaChannel":9,"softVer":"1.0.0","online":true}]",
        'cadVer': cad_version,
        'cdVer': cd_version,
        'options': '{"isFK":' + str(is_fk).lower() + ',"otaChannel":0}',
        't': epoch_time,
    }

    return data


def get_new_token():
    print('[!] No token provided.')
    print("[!] On any device on the same network/vlan as your device running this script, please log into the Smart Life app ('Try as Guest' works fine if you do not already have an account)")
    print("[!]  Note: no real device should currently be in pairing mode, or the instructions below may not match.")
    print("[!]  - Start the add device procedure (hit '+' in the upper-right and select 'Add Device')")
    print("[!]  - Under 'Add Manually' select 'Socket (Wi-Fi)'")
    print("[!]  - Enter your network credentials as instructed")
    print("[!]  - Do not follow any of the instructions about putting a device into pairing mode, instead select 'next' until it asks the status of the indicator and select 'Blink Slowly'")
    print("[!]  - Select 'Go to Connect', then in your wifi selection screen, hit the back button to return to Smart Life.")
    print("[!] A new token should be sent to your network (make sure your firewall is not blocking port 6669), and this script will continue.")
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


def run(directory: str, output_file_prefix: str, uuid: str, auth_key: str, firmware_key: str, product_key: str, factory_pin: str, software_version: str, mcu_software_version: str, baseline_version: str = '40.00', cad_version: str = '1.0.2', cd_version: str = '1.0.0', protocol_version='2.2', token: str = None):
    if uuid is None or len(uuid) != 16:
        if product_key is not None and len(product_key) == 16:
            uuid = product_key
        else:
            print_and_exit('required uuid was not found or was invalid (expected 16 characters)')
    if auth_key is None or len(auth_key) != 32:
        print_and_exit('required auth_key was not found or was invalid (expected 32 characters)')
    if (product_key is None or len(product_key) == 0) and (firmware_key is None or len(firmware_key) == 0) and (factory_pin is None or len(factory_pin) == 0):
        print_and_exit('required firmware key/product key/factory pin was not found or was invalid (expected 16 characters)')
    if software_version is None or len(software_version) < 5:
        print_and_exit('required softVer was not found or was invalid (expected >= 5 characters)')
    if mcu_software_version is None or len(mcu_software_version) < 5:
        print_and_exit('required MCUsoftVer was not found or was invalid (expected >= 5 characters)')
    if cad_version is None or len(cad_version) < 5:
        print_and_exit('required cadVer was not found or was invalid (expected >= 5 characters)')
    if baseline_version is None or len(baseline_version) < 5:
        print_and_exit('required baselineVer was not found or was invalid (expected 5 characters)')

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
    print(f'Using token: {token} product_key: {product_key} firmware_key: {firmware_key}')
    # tuya.device.active encrypts with auth_key
    connection = TuyaAPIConnection(uuid, auth_key)
    url = f"http://a.tuya{region}.com/d.json"
    epoch_time = int(time.time())
    params = build_params(epoch_time, uuid)
    response = None
    requestType = "POST"

    responseCodesToContinueAter = ['FIRMWARE_NOT_MATCH', 'APP_PRODUCT_UNSUPPORT', 'NOT_EXISTS']

    if factory_pin is not None and len(factory_pin) > 0:
        product_key = factory_pin

    if product_key is not None:
        data = build_data(epoch_time, reduced_token, firmware_key, product_key, software_version, mcu_software_version, baseline_version, cad_version, cd_version, protocol_version, False)
        response = connection.request(url, params, data, requestType)

        if response["success"] == False and response["errorCode"] in responseCodesToContinueAter:
            data = build_data(epoch_time, reduced_token, firmware_key, product_key, software_version, mcu_software_version, baseline_version, cad_version, cd_version, protocol_version, True)
            response = connection.request(url, params, data, requestType)

    if response["success"] == False:
        if product_key != firmware_key:
            if (response is None or (response is not None and response["success"] == False and response["errorCode"] != "EXPIRE")) and firmware_key is not None:
                data = build_data(epoch_time, reduced_token, firmware_key, firmware_key, software_version, mcu_software_version, baseline_version, cad_version, cd_version, protocol_version, True)
                response = connection.request(url, params, data, requestType)

                if response["success"] == False and response["errorCode"] in responseCodesToContinueAter:
                    data = build_data(epoch_time, reduced_token, firmware_key, firmware_key, software_version, mcu_software_version, baseline_version, cad_version, cd_version, protocol_version, False)
                    response = connection.request(url, params, data, requestType)

    if response["success"] == True:
        print(f"[+] Schema Id: {response['result']['schemaId']}")
        print(f"[+] Schema: {response['result']['schema']}")
        with open(os.path.join(directory, output_file_prefix + "_schema_id.txt"), 'w') as f:
            f.write(response['result']['schemaId'])
        with open(os.path.join(os.path.join(directory, ".."), "schema_id.txt"), 'w') as f:
            f.write(response['result']['schemaId'])
        with open(os.path.join(directory, output_file_prefix + "_schema.txt"), 'w') as f:
            f.write(response['result']['schema'])
        with open(os.path.join(os.path.join(directory, ".."), "schema.txt"), 'w') as f:
            f.write(response['result']['schema'])
        with open(os.path.join(directory, output_file_prefix + "_dev_id.txt"), 'w') as f:
            f.write(response['result']['devId'])
        with open(os.path.join(directory, output_file_prefix + "_sec_key.txt"), 'w') as f:
            f.write(response['result']['secKey'])
    elif response["success"] == False and response["errorCode"] == 'EXPIRE':
        print("[!] The token provided has either expired, or you are connected to the wrong region")
    else:
        print(response)


def run_input(uuid, auth_key, firmware_key, product_key, factory_pin, software_version, mcu_software_version, baseline_version='40.00', cad_version='1.0.2', cd_version='1.0.0', protocol_version='2.2', token=None):
    run('.\\', 'device', uuid, auth_key, firmware_key, product_key, factory_pin, software_version, mcu_software_version, baseline_version, cad_version, cd_version, protocol_version, token)


def run_directory(directory, token=None):
    uuid = None
    auth_key = None
    factory_pin = None
    product_key = None
    firmware_key = None
    software_version = None
    mcu_software_version = None
    baseline_version = '40.00'
    cad_version = '1.0.2'
    cd_version = '1.0.0'
    protocol_version = '2.2'
    output_file_prefix = None

    dirListing = os.listdir(f'{directory}')

    for file in dirListing:
        if file.endswith('_uuid.txt'):
            uuid = read_single_line_file(os.path.join(directory, file))
            output_file_prefix = file.replace('_uuid.txt', '')
        elif file.endswith('_auth_key.txt'):
            auth_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_factory_pin.txt'):
            factory_pin = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_product_key.txt'):
            product_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_firmware_key.txt'):
            firmware_key = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_swv.txt'):
            software_version = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_mcuswv.txt'):
            mcu_software_version = read_single_line_file(os.path.join(directory, file))
        elif file.endswith('_bv.txt'):
            baseline_version = read_single_line_file(os.path.join(directory, file))

    if uuid is None:
        print('[!] uuid was not found')
        return
    if auth_key is None:
        print('[!] auth_key was not found')
        return
    if (product_key is None or len(product_key) == 0) and (firmware_key is None or len(firmware_key) == 0) and (factory_pin is None or len(factory_pin) == 0):
        print('[!] firmware key/product key/factory pin was not found, at least one must be provided')
        return
    if software_version is None:
        print('[!] software_version was not found')
        return
    if mcu_software_version is None:
        print('[!] mcu_software_version was not found, falling back to 1.0.0')
        mcu_software_version = "1.0.0"
    if baseline_version is None:
        print('[!] baseline_version was not found')
        return

    run(directory, output_file_prefix, uuid, auth_key, firmware_key, product_key, factory_pin, software_version, mcu_software_version, baseline_version, cad_version, cd_version, protocol_version, token)


if __name__ == '__main__':

    if (sys.argv[2:]):
        if sys.argv[1] == '--input':
            if not sys.argv[7:]:
                print('Unrecognized input.')
                print_help()
            uuid = sys.argv[2]
            auth_key = sys.argv[3]
            firmware_key = sys.argv[4]
            product_key = sys.argv[5]
            factory_pin = sys.argv[6]
            software_version = sys.argv[7]
            mcu_software_version = sys.argv[8]
            cad_version = ('1.0.2' if sys.argv[9] is None else sys.argv[9])
            baseline_version = ('40.00' if sys.argv[10] is None else sys.argv[10])
            token = sys.argv[9]
            run_input(uuid, auth_key, firmware_key, product_key, factory_pin, software_version, mcu_software_version, cad_version, baseline_version, token)
        elif sys.argv[1] == '--directory':
            if not sys.argv[2:]:
                print('Unrecognized input.')
                print_help()
            directory = sys.argv[2]
            token = (None if len(sys.argv) < 4 else sys.argv[3])
            run_directory(directory, token)
    else:
        print_help()
