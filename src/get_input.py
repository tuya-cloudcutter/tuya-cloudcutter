import json
import os, sys
import inquirer
import requests
from os.path import join, dirname


def api_get(path):
    with requests.get(f"https://tuya-cloudcutter.github.io/api/{path}") as r:
        return r.json()


def ask_options(text, options):
    return inquirer.prompt([inquirer.List('result', carousel=True, message=text, choices=options)])["result"]


def ask_files(text, dir):
    files = [path for path in os.listdir(dir) if not path.startswith(".")]
    return ask_options(text, sorted(files, key=str.casefold))


def ask_target_profile(output):
    opts = [
        "By manufacturer/device name",
        "By firmware version and name",
    ]
    mode = ask_options("How do you want to choose the device?", opts)
    if mode == opts[0]:
        device_slug = ask_device_base(api_get("devices.json"))["slug"]
        device = api_get(f"devices/{device_slug}.json")
        profiles = device["profiles"]
        profile_slug = ask_profile_base(profiles)["slug"]
        profile = api_get(f"profiles/{profile_slug}.json")
    else:
        profile_slug = ask_profile_base(api_get("profiles.json"))["slug"]
        profile = api_get(f"profiles/{profile_slug}.json")
        devices = profile["devices"]
        device_slug = ask_device_base(devices)["slug"]
        device = api_get(f"devices/{device_slug}.json")

    return save_profile(output, device, profile)


def download_profile(output, device_slug):
    output_path = join(output, "device-profiles", device_slug)
    if os.path.isfile(join(output_path, "device.json")) and os.path.isfile(join(output_path, "profile.json")):
        return device_slug
    device = api_get(f"devices/{device_slug}.json")
    profiles = device["profiles"]
    profile_slug = profiles[0]["slug"]
    profile = api_get(f"profiles/{profile_slug}.json")
    return save_profile(output, device, profile)


def ask_device_base(devices):
    brands = sorted(set(device["manufacturer"] for device in devices))
    manufacturer = ask_options("Select the brand of your device", brands)
    names = sorted(
        set(
            device["name"]
            for device in devices
            if device["manufacturer"] == manufacturer
        )
    )
    name = ask_options("Select the article number of your device", names)
    return next(
        device
        for device in devices
        if device["manufacturer"] == manufacturer and device["name"] == name
    )


def ask_profile_base(profiles):
    profiles = {
        f"{profile['name']} / {profile['sub_name']}": profile
        for profile in profiles
        if profile["type"] == "CLASSIC"
    }
    names = sorted(set(profiles.keys()))
    name = ask_options("Select the firmware version and name", names)
    return profiles[name]


def ask_custom_firmware(firmware_dir):
    return f"{ask_files('Select your custom firmware file', firmware_dir)}"


def save_profile(output, device, profile):
    device_slug = device["slug"]
    output_path = join(output, "device-profiles", device_slug)
    os.makedirs(output_path, exist_ok=True)
    with open(join(output_path, "device.json"), "w") as f:
        json.dump(device, f, indent="\t")
    with open(join(output_path, "profile.json"), "w") as f:
        json.dump(profile, f, indent="\t")
    return device_slug


def validate_firmware_file(firmware):
    UG_FILE_MAGIC = b"\x55\xAA\x55\xAA"
    FILE_MAGIC_DICT = {
        b"RBL\x00": "RBL",
        b"\x43\x09\xb5\x96": "QIO",
        b"\x2f\x07\xb5\x94": "UA"
    }
    
    with open(firmware, "rb") as fs:
        magic = fs.read(4)
        error_code = 0
        if magic in FILE_MAGIC_DICT:
            print(f"Firmware {firmware} is an {FILE_MAGIC_DICT[magic]} file! Please provide a UG file.", file=sys.stderr)
            error_code = 51
        elif magic != UG_FILE_MAGIC:
            print(f"Firmware {firmware} is not a UG file.", file=sys.stderr)
            error_code = 52
        else:
            # File is a UG file
            error_code = 0
            pass

        if error_code != 0:
            sys.exit(error_code)
    return firmware


if __name__ == "__main__":
    input_type = sys.argv[1]
    if input_type == "download_profile":
        download_profile(sys.argv[2], sys.argv[3])
        exit(0)
    output_file = open(sys.argv[2], "wt")
    if input_type == "device":
        device_slug = ask_target_profile(sys.argv[3])
        print(f"{device_slug}", file=output_file)
    elif input_type == "firmware":
        firmware_dir = "/work/custom-firmware"
        firmware = ask_custom_firmware(firmware_dir)
        firmware_file_path = os.path.join(firmware_dir, firmware)
        validate_firmware_file(firmware_file_path)
        print(f"{firmware}", file=output_file)
