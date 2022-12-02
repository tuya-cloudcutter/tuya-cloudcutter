import json
import sys
from glob import glob
from os import listdir, makedirs
from os.path import abspath, basename, isdir, isfile, join

import click
import inquirer
import requests


def api_get(path):
    with requests.get(f"https://tuya-cloudcutter.github.io/api/{path}") as r:
        if r.status_code == 404:
            print("The specified device does not exist in the API.")
            exit(1)
        if r.status_code != 200:
            print("API request failed. Make sure you have an Internet connection.")
            exit(1)
        return r.json()


def ask_options(text, options):
    return inquirer.prompt(
        [
            inquirer.List(
                "result",
                carousel=True,
                message=text,
                choices=options,
            )
        ]
    )["result"]


def ask_files(text, dir):
    files = [
        path
        for path in listdir(dir)
        if not path.startswith(".") and isfile(join(dir, path))
    ]
    path = ask_options(text, sorted(files, key=str.casefold))
    return abspath(join(dir, path))


def ask_dirs(text, dir):
    files = [
        path
        for path in listdir(dir)
        if not path.startswith(".") and isdir(join(dir, path)) and path != "schema"
    ]
    path = ask_options(text, sorted(files, key=str.casefold))
    return abspath(join(dir, path))


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


def download_profile(device_slug):
    device = api_get(f"devices/{device_slug}.json")
    profiles = device["profiles"]
    profile_slug = profiles[0]["slug"]
    profile = api_get(f"profiles/{profile_slug}.json")
    return device, profile


def save_profile(profile_dir, device, profile):
    makedirs(profile_dir, exist_ok=True)
    with open(join(profile_dir, "device.json"), "w") as f:
        json.dump(device, f, indent="\t")
    with open(join(profile_dir, "profile.json"), "w") as f:
        json.dump(profile, f, indent="\t")


def load_profile(profile_dir):
    device, profile = None, None
    for file in glob(join(profile_dir, "*.json")):
        with open(file, "r") as f:
            data = json.load(f)
        # match characteristic keys
        if "profiles" in data:
            device = data
            continue
        if "firmware" in data:
            profile = data
            continue
        if device and profile:
            break
    return device, profile


def save_combined_profile(profile_dir, device, profile):
    makedirs(profile_dir, exist_ok=True)
    combined = {
        "slug": basename(profile_dir),
        "device": device,
        "profile": profile,
    }
    combined_path = join(profile_dir, "combined.json")
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent="\t")
    return abspath(combined_path)


def validate_firmware_file(firmware):
    UG_FILE_MAGIC = b"\x55\xAA\x55\xAA"
    FILE_MAGIC_DICT = {
        b"RBL\x00": "RBL",
        b"\x43\x09\xb5\x96": "QIO",
        b"\x2f\x07\xb5\x94": "UA",
    }

    with open(firmware, "rb") as fs:
        magic = fs.read(4)
        error_code = 0
        if magic in FILE_MAGIC_DICT:
            print(
                f"Firmware {firmware} is an {FILE_MAGIC_DICT[magic]} file! Please provide a UG file.",
                file=sys.stderr,
            )
            error_code = 51
        elif magic != UG_FILE_MAGIC:
            print(f"Firmware {firmware} is not a UG file.", file=sys.stderr)
            error_code = 52
        else:
            # File is a UG file
            error_code = 0
            pass

        if error_code != 0:
            exit(error_code)
    return firmware


@click.group()
@click.option(
    "-w",
    "--workdir",
    type=click.Path(exists=True, file_okay=False),
    required=True,
)
@click.option(
    "-o",
    "--output",
    type=click.File(mode="w"),
    required=True,
)
@click.pass_context
def cli(ctx, workdir: str, output: click.File):
    ctx.ensure_object(dict)
    ctx.obj["firmware_dir"] = join(workdir, "custom-firmware")
    ctx.obj["profiles_dir"] = join(workdir, "device-profiles")
    ctx.obj["output"] = output


@cli.command()
@click.argument("slug", type=str)
@click.pass_context
def write_profile(ctx, slug: str):
    device_slug = slug
    profiles_dir = ctx.obj["profiles_dir"]
    profile_dir = join(profiles_dir, device_slug)
    # try to find device and profile JSON files
    if isdir(profile_dir):
        device, profile = load_profile(profile_dir)
    # else try to download the profile from API
    if not (device and profile):
        device, profile = download_profile(device_slug)
        save_profile(profile_dir, device, profile)
    # write profile data if found
    path = save_combined_profile(profile_dir, device, profile)
    ctx.obj["output"].write(path)


@cli.command()
@click.pass_context
def choose_profile(ctx):
    profiles_dir = ctx.obj["profiles_dir"]
    device_slug = None
    opts = [
        "By manufacturer/device name",
        "By firmware version and name",
        "From device-profiles (i.e. custom profile)",
    ]
    mode = ask_options("How do you want to choose the device?", opts)
    if mode == opts[0]:
        device_slug = ask_device_base(api_get("devices.json"))["slug"]
        device = api_get(f"devices/{device_slug}.json")
        profiles = device["profiles"]
        profile_slug = ask_profile_base(profiles)["slug"]
        profile = api_get(f"profiles/{profile_slug}.json")
    elif mode == opts[1]:
        profile_slug = ask_profile_base(api_get("profiles.json"))["slug"]
        profile = api_get(f"profiles/{profile_slug}.json")
        devices = profile["devices"]
        device_slug = ask_device_base(devices)["slug"]
        device = api_get(f"devices/{device_slug}.json")
    elif mode == opts[2]:
        profile_dir = ask_dirs("Select device profile", profiles_dir)
        device, profile = load_profile(profile_dir)
    else:
        exit(2)

    if device_slug is not None:
        profile_dir = join(profiles_dir, device_slug)
        save_profile(profile_dir, device, profile)

    path = save_combined_profile(profile_dir, device, profile)
    ctx.obj["output"].write(path)


@cli.command()
@click.pass_context
def choose_firmware(ctx):
    firmware_dir = ctx.obj["firmware_dir"]
    path = ask_files("Select your custom firmware file", firmware_dir)
    ctx.obj["output"].write(path)


if __name__ == "__main__":
    cli(obj={})
