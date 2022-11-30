import argparse
from fileinput import filename
import hmac
import json
import os
import re
import sys
import time
from hashlib import sha256
from tornado.log import enable_pretty_logging
from traceback import print_exc

import tinytuya.tinytuya as tinytuya
import tornado.httpserver
import tornado.ioloop
import tornado.web

from .crypto.pskcontext import PSKContext
from .device import DEFAULT_AUTH_KEY, DEVICE_DATA_FILE_NAME, DEVICE_PROFILE_FILE_NAME, DeviceConfig
from .exploit import (build_network_config_packet, exploit_device_with_config,
                      send_network_config_datagram)
from .protocol import mqtt
from .protocol.handlers import DetachHandler, GetURLHandler, OldSDKGetURLHandler, OTAFilesHandler
from .protocol.transformers import ResponseTransformer

# Enable tornado pretty logging for more verbose output by default
enable_pretty_logging()


def __configure_local_device_response_transformers(config):
    return [
            ResponseTransformer({"timestamp", "t", "time"}, lambda _: int(time.time())),
            ResponseTransformer({"devId", "deviceId"}, lambda _: config.get(DeviceConfig.DEVICE_ID)),
            ResponseTransformer({"secKey"}, lambda _: config.get(DeviceConfig.SEC_KEY)),
            ResponseTransformer({"localKey"}, lambda _: config.get(DeviceConfig.LOCAL_KEY)),
            ResponseTransformer({"pskKey", "psk_key"}, lambda _: "")
    ]


def __configure_ssid_on_device(ip: str, config: DeviceConfig, ssid: str, password: str):
    try:
        device_id = config.get(DeviceConfig.DEVICE_ID)
        local_key = config.get(DeviceConfig.LOCAL_KEY)
        print(f"{device_id=}, {ip=}, {local_key=}")
        device = tinytuya.Device(device_id, ip, local_key)
        device.connection_timeout = 0.2

        payload = { "ssid": ssid }
        if password:
            payload["passwd"] = password

        device.version = 3.3
        parsed_data = device.updatedps() or {}
        device.set_version(3.3)

        trials = 0
        while parsed_data is not None and "Err" not in parsed_data and trials < 5:
            # Once device joins SSID, we get a timeout / connection error, which adds "Err" attribute. We'll wait for that to happen.
            parsed_data = device._send_receive(device.generate_payload_raw(command=0x0f, retcode=0x0, data=payload, skip_header=False), minresponse=0)
            trials += 1
            time.sleep(0.2)
        
        if trials >= 5:
            print("Failed to set the WiFi AP creds on the device, latest error:")
            print(parsed_data)
            sys.exit(80)

        print(f"Device should be successfully onboarded on WiFi AP!")
        sys.exit(0)
    except Exception:
        print_exc()
        sys.exit(90)


def __trigger_firmware_update(config: DeviceConfig):
    device_id = config.get(DeviceConfig.DEVICE_ID)
    local_key = config.get(DeviceConfig.LOCAL_KEY)

    mqtt.trigger_firmware_update(device_id=device_id, local_key=local_key, protocol="2.2", broker="127.0.0.1")
    print("Firmware update messages triggered. Device will download and reset. Exiting in 30 seconds.")
    tornado.ioloop.IOLoop.current().call_later(30.0, lambda : sys.exit(0))


def __configure_local_device_or_update_firmware(args, update_firmare: bool = False):
    if not os.path.exists(args.config):
        print(f"Configuration file {args.config} does not exist", file=sys.stderr)
        sys.exit(10)

    if not os.path.exists(args.profile):
        print(f"Device profile directory {args.profile} does not exist", file=sys.stderr)
        sys.exit(20)

    if not os.path.isdir(args.profile):
        print(f"Provided device profile path {args.profile} is not a directory", file=sys.stderr)
        sys.exit(30)

    config = DeviceConfig.read(args.config)
    authkey, uuid = config.get_bytes(DeviceConfig.AUTH_KEY, default=DEFAULT_AUTH_KEY), config.get_bytes(DeviceConfig.UUID)
    context = PSKContext(authkey=authkey, uuid=uuid)

    with open(os.path.join(args.profile, DEVICE_DATA_FILE_NAME), "r") as f:
        device = json.load(f)

    def dynamic_config_endpoint_hook(handler, *_):
        """
        Hooks into an endpoint response for the dynamic config. Standard response should not be overwritten, but needs to
        register a task to either changed device SSID or update firmware. Hence, return None.
        """
        if update_firmare:
            task_function = __trigger_firmware_update
            task_args = (config, )
        else:
            task_args = (handler.request.remote_ip, config, args.ssid, args.password)
            task_function = __configure_ssid_on_device

        tornado.ioloop.IOLoop.current().call_later(5.0, task_function, *task_args)
        return None

    def upgrade_endpoint_hook(handler, *_):
        with open(args.firmware, "rb") as fs:
            upgrade_data = fs.read()
        sec_key = config.get_bytes(DeviceConfig.SEC_KEY)
        file_sha = sha256(upgrade_data).hexdigest().upper().encode("utf-8")
        file_hmac = hmac.digest(sec_key, file_sha, sha256).hex().upper()
        firmware_filename = os.path.basename(args.firmware)

        return {
            "result": {
                "url": f"http://{args.ip}:80/files/{firmware_filename}",
                "hmac": file_hmac,
                "version": "9.0.0",
                "size": str(len(upgrade_data)),
                "type": 0,
            },
            "success": True,
            "t": int(time.time())
        }

    def active_endpoint_hook(handler, *_):
        schema_id, schema = list(device["schemas"].items())[0]
        return {
            "result": {
                "schema": json.dumps(schema, separators=(',', ':')),
                "devId": "DUMMY",
                "resetFactory": False,
                "timeZone": "+02:00",
                "capability": 1025,
                "secKey": "DUMMY",
                "stdTimeZone": "+01:00",
                "schemaId": schema_id,
                "dstIntervals": [],
                "localKey": "DUMMY",
            },
            "success": True,
            "t": int(time.time())
        }

    response_transformers = __configure_local_device_response_transformers(config)
    endpoint_hooks = {
        "tuya.device.dynamic.config.get": dynamic_config_endpoint_hook,
        "tuya.device.active": active_endpoint_hook,
    }

    if update_firmare:
        endpoint_hooks.update({
            "tuya.device.upgrade.silent.get": upgrade_endpoint_hook,
            "tuya.device.upgrade.get": upgrade_endpoint_hook
        })

    application = tornado.web.Application([
        (r'/v1/url_config', GetURLHandler, dict(ipaddr=args.ip)),
        (r'/v2/url_config', GetURLHandler, dict(ipaddr=args.ip)),
        # 2018 SDK specific endpoint
        (r'/device/url_config', OldSDKGetURLHandler, dict(ipaddr=args.ip)),
        (r'/d.json', DetachHandler, dict(schema_directory=args.schema, response_transformers=response_transformers, config=config, endpoint_hooks=endpoint_hooks)),
        (f'/files/(.*)', OTAFilesHandler, dict(path="/work/custom-firmware/")),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)

    https_server = tornado.httpserver.HTTPServer(application, ssl_options=context)
    https_server.listen(443)

    # 2018 SDK seems to request that port for some reason
    dns_https_server = tornado.httpserver.HTTPServer(application, ssl_options=context)
    dns_https_server.listen(4433)

    tornado.ioloop.IOLoop.current().start()


def __update_firmware(args):
    if not (os.path.exists(args.firmware) and os.path.isfile(args.firmware)):
        print(f"Firmware {args.firmware} does not exist or not a file.", file=sys.stderr)
        sys.exit(50)

    UG_FILE_MAGIC = b"\x55\xAA\x55\xAA"
    FILE_MAGIC_DICT = {
        b"RBL\x00": "RBL",
        b"\x43\x09\xb5\x96": "QIO",
        b"\x2f\x07\xb5\x94": "UA"
    }
    
    with open(args.firmware, "rb") as fs:
        magic = fs.read(4)
        error_code = 0
        if magic in FILE_MAGIC_DICT:
            print(f"Firmware {args.firmware} is an {FILE_MAGIC_DICT[magic]} file! Please provide a UG file.", file=sys.stderr)
            error_code = 51
        elif magic != UG_FILE_MAGIC:
            print(f"Firmware {args.firmware} is not a UG file.", file=sys.stderr)
            error_code = 52
        else:
            # File is a UG file
            error_code = 0
            pass

        if error_code != 0:
            sys.exit(error_code)
    
    __configure_local_device_or_update_firmware(args, update_firmare=True)


def __exploit_device(args):
    output_dir = args.output_directory
    if not (os.path.exists(output_dir) and os.path.isdir(output_dir)):
        print(f"Provided output directory {output_dir} does not exist or not a directory", file=sys.stderr)
        sys.exit(60)

    profile_path = os.path.join(args.profile, DEVICE_PROFILE_FILE_NAME)
    device_path = os.path.join(args.profile, DEVICE_DATA_FILE_NAME)
    try:
        with open(profile_path, "r") as fs:
            exploit_profile = json.load(fs)
        with open(device_path, "r") as fs:
            exploit_device = json.load(fs)
    except OSError:
        print(f"Could not load profile {profile_path}. Are you sure the profile directory and file exist?", file=sys.stderr)
        sys.exit(65)

    device_config = exploit_device_with_config(args, exploit_profile, exploit_device)
    device_uuid = device_config.get(DeviceConfig.UUID)

    output_path = os.path.join(output_dir, f"{device_uuid}.deviceconfig")
    device_config.write(output_path)

    print(f"Exploit run, saved device config to!")

    # To communicate with external scripts
    print(f"output={output_path}")


def __configure_wifi(args):
    SSID = args.SSID
    password = args.password
    
    # Pass the payload through the json module specifically
    # to avoid issues with special chars (e.g. ") in either
    # SSIDs or passwords.
    payload = {"ssid": SSID, "token": "AAAAAAAA"}

    # Configure the password ONLY if it's present
    # Some devices may parse incorrectly otherwise
    if password:
        payload["passwd"] = password

    payload = json.dumps(payload)

    datagram = build_network_config_packet(payload.encode('ascii'))
    # Send the configuration diagram a few times with minor delay
    # May improve reliability in some setups
    for _ in range(5):
        send_network_config_datagram(datagram)
        time.sleep(0.300)
    print(f"Configured device to connect to '{SSID}'")

def __validate_localapicredential_arg(length):
    def check_arg(value):
        if (len(value) == 0):
            return value
        elif (len(value) != length):
            raise argparse.ArgumentTypeError("%s length is invalid, it must be %s characters long" % value, length)
        elif (not re.compile('[a-zA-Z0-9]').match(value)):
            raise argparse.ArgumentTypeError("%s value is invalid, it must contain only letters or numbers" % value)
        return value
    return check_arg

def parse_args():
    parser = argparse.ArgumentParser(
        prog="cloudcutter",
        description="Detach tuya devices from the cloud or install custom firmware on them",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="subcommand to execute")

    parser_configure = subparsers.add_parser("configure_local_device", help="Configure detached device with local keys and onboard it on desired WiFi AP")
    parser_configure.add_argument("profile", help="Device profile directory to use for detaching")
    parser_configure.add_argument("schema", help="Endpoint schemas directory to use for detaching")
    parser_configure.add_argument("config", help="Device configuration file")
    parser_configure.add_argument(
        "--ip",
        dest="ip",
        default="10.42.42.1",
        help="IP address to listen on and respond to the devices with (default: 10.42.42.1)",
    )
    parser_configure.add_argument(
        "--ssid",
        required=True,
        help="SSID that the device will be onboarded on after configuration",
    )
    parser_configure.add_argument(
        "--password",
        required=False,
        default="",
        help="Password of the SSID for device onboarding (default: empty)",
    )
    parser_configure.set_defaults(handler=__configure_local_device_or_update_firmware)

    parser_update_firmware = subparsers.add_parser("update_firmware", help="Update the device's firmware")
    parser_update_firmware.add_argument("profile", help="Device profile directory to use for updating")
    parser_update_firmware.add_argument("schema", help="Endpoint schemas directory to use for updating")
    parser_update_firmware.add_argument("config", help="Device configuration file")
    parser_update_firmware.add_argument("firmware", help="OTA firmware image to update the device to")
    parser_update_firmware.add_argument(
        "--ip",
        dest="ip",
        default="10.42.42.1",
        help="IP address to listen on and respond to the devices with (default: 10.42.42.1)",
    )
    parser_update_firmware.set_defaults(handler=__update_firmware)

    parser_exploit_device = subparsers.add_parser(
        "exploit_device",
        help="Exploit a device - requires that the attacking system is on the device's AP"
    )
    parser_exploit_device.add_argument("profile", help="Device profile directory to use for exploitation")
    parser_exploit_device.add_argument(
        "--output-directory",
        dest="output_directory",
        required=False,
        default="/work/configured-devices",
        help="A directory to which the modified device parameters file will be written (default: <workdir>/configured-devices)"
    )
    parser_exploit_device.add_argument(
        "--deviceid",
        dest="device_id",
        required=False,
        default="",
        help="deviceid assigned to the device (default: Random)",
        type=__validate_localapicredential_arg(20),
    )
    parser_exploit_device.add_argument(
        "--localkey",
        dest="local_key",
        required=False,
        default="",
        help="localkey assigned to the device (default: Random)",
        type=__validate_localapicredential_arg(16),
    )
    parser_exploit_device.set_defaults(handler=__exploit_device)

    parser_configure_wifi = subparsers.add_parser(
        "configure_wifi",
        help="Makes a device to which you're connected via its AP mode join a given WiFi network"
    )
    parser_configure_wifi.add_argument("SSID", help="WiFi access point name to make the device join")
    parser_configure_wifi.add_argument("password", help="WiFi access point password")
    parser_configure_wifi.set_defaults(handler=__configure_wifi)

    return parser.parse_args()


args = parse_args()
args.handler(args)
