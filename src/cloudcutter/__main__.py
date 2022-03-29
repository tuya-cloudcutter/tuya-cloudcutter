import argparse
import json
import os
import sys
import time

import tinytuya.tinytuya as tinytuya
import tornado.httpserver
import tornado.ioloop
import tornado.web

from .crypto.pskcontext import PSKContext
from .device import DEFAULT_AUTH_KEY, DEVICE_PROFILE_FILE_NAME, DeviceConfig
from .exploit import exploit_device_with_config
from .protocol.handlers import DetachHandler, GetURLHandler
from .protocol.transformers import ResponseTransformer


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
        parsed_data = device.updatedps()
        device.set_version(3.3)

        trials = 0
        while ("Err" not in parsed_data and trials < 5):
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
    except Exception as e:
        print(f"Exeception: {repr(e)}")
        sys.exit(90)

def __configure_local_device(args):
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

    ssid, password = args.ssid, args.password

    def dynamic_config_endpoint_hook(handler, *_):
        """
        Hooks into an endpoint response for the dynamic config. Standard response should not be overwritten, but needs to
        register a task to change device SSID. Hence, return None.
        """
        tornado.ioloop.IOLoop.current().call_later(5.0, __configure_ssid_on_device, handler.request.remote_ip, config, ssid, password)
        return None

    response_transformers = __configure_local_device_response_transformers(config)
    endpoint_hooks = {"tuya.device.dynamic.config.get": dynamic_config_endpoint_hook}

    application = tornado.web.Application([
        (r'/v1/url_config', GetURLHandler, dict(ipaddr=args.ip)),
        (r'/v2/url_config', GetURLHandler, dict(ipaddr=args.ip)),
        (r'/d.json', DetachHandler, dict(profile_directory=args.profile, response_transformers=response_transformers, config=config, endpoint_hooks=endpoint_hooks)),
    ])

    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)

    https_server = tornado.httpserver.HTTPServer(application, ssl_options=context)
    https_server.listen(443)

    tornado.ioloop.IOLoop.current().start()


def __update_firmware(args):
    print("Update not implemented yet", file=sys.stderr)
    sys.exit(50)


def __exploit_device(args):
    output_dir = args.output_directory
    if not (os.path.exists(output_dir) and os.path.isdir(output_dir)):
        print(f"Provided output directory {output_dir} does not exist or not a directory", file=sys.stderr)
        sys.exit(60)

    profile_path = os.path.join(args.profile, DEVICE_PROFILE_FILE_NAME)
    try:
        with open(profile_path, "r") as fs:
            exploit_profile = json.load(fs)
    except OSError:
        print(f"Could not load profile {profile_path}. Are you sure the profile directory and file exist?", file=sys.stderr)
        sys.exit(65)

    device_config = exploit_device_with_config(exploit_profile)
    device_id = device_config.get(DeviceConfig.DEVICE_ID)

    output_path = os.path.join(output_dir, f"{device_id}.deviceconfig")
    device_config.write(output_path)

    print(f"Exploit run, saved device config to!")

    # To communicate with external scripts
    print(f"output={output_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="cloudcutter",
        description="Detach tuya devices from the cloud or install custom firmware on them",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="subcommand to execute")

    parser_configure = subparsers.add_parser("configure_local_device", help="Configure detached device with local keys and onboard it on desired WiFi AP")
    parser_configure.add_argument("profile", help="Device profile directory to use for detaching")
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
    parser_configure.set_defaults(handler=__configure_local_device)

    parser_update_firmware = subparsers.add_parser("update_firmware", help="Update the device's firmware")
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
    parser_exploit_device.set_defaults(handler=__exploit_device)

    return parser.parse_args()


args = parse_args()
args.handler(args)
