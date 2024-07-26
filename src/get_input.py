import json
import sys
from enum import Enum
from glob import glob
from os import listdir, makedirs
from os.path import abspath, basename, isdir, isfile, join

import click
import inquirer
import requests


class FirmwareType(Enum):
    INVALID = 0
    IGNORED_HEADER = 1
    IGNORED_FILENAME = 2
    VALID_UG = 3
    VALID_UF2 = 4


UF2_UG_SUFFIX = "-extracted.ug.bin"
UF2_FAMILY_MAP = {
    "bk7231t": 0x675A40B0,
    "bk7231n": 0x7B3EF230,
}


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
    res = inquirer.prompt(
        [
            inquirer.List(
                "result",
                carousel=True,
                message=text,
                choices=options,
            )
        ], theme=inquirer.themes.load_theme_from_dict({ "List": { "selection_color": "underline", "selection_cursor": "►" } })
    )
    if res is None:
        # Ctrl+C
        exit(1)
    return res["result"]


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
    brands = sorted(set(device["manufacturer"] for device in devices), key=str.casefold)
    manufacturer = ask_options("Select the brand of your device", brands)
    names = sorted(
        set(
            device["name"]
            for device in devices
            if device["manufacturer"] == manufacturer
        ), key=str.casefold
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
            try:
                data = json.load(f)
            except:
                print(
                    f"File {file} does not contain valid JSON. "
                    "Please update your file and try again."
                )
                exit(53)
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

def validate_firmware_file_internal(firmware: str, chip: str = None) -> FirmwareType:
    FILE_MAGIC_DICT = {
        b"RBL\x00": "RBL",
        b"\x43\x09\xb5\x96": "QIO",
        b"\x2f\x07\xb5\x94": "UA",
        b"\x55\xAA\x55\xAA": "UG",
        b"UF2\x0A": "UF2",
    }

    base = basename(firmware)
    with open(firmware, "rb") as fs:
        header = fs.read(512)

    magic = header[0:4]
    if magic not in FILE_MAGIC_DICT or len(header) < 512:
        print(
            f"!!! Unrecognized file type - '{base}' is not a UG or UF2 file.",
            file=sys.stderr,
        )
        return FirmwareType.INVALID
    file_type = FILE_MAGIC_DICT[magic]

    if file_type not in ["UG", "UF2"]:
        print(
            f"!!! File {base} is a '{file_type}' file! Please provide an UG file.",
            file=sys.stderr,
        )
        return FirmwareType.INVALID

    if file_type == "UG":
        # check LibreTiny UG version tag (chip type)
        rbl_ver = header[32 + 12 + 16 : 32 + 12 + 16 + 24]
        if b"bk7231" in rbl_ver:
            if chip and chip.encode() not in rbl_ver:
                # wrong chip type
                return FirmwareType.IGNORED_HEADER
            # correct chip type
            return FirmwareType.VALID_UG
        # check chip by filename
        if "bk7231" in base.lower():
            if chip and chip not in base.lower():
                # wrong chip type
                return FirmwareType.IGNORED_FILENAME
            # correct chip type
            return FirmwareType.VALID_UG
        print(
            f"!!! Can't verify chip type of UG file '{base}' - "
            "make sure that BK7231T or BK7231N is present in the filename!",
            file=sys.stderr,
        )
        return FirmwareType.INVALID

    if file_type == "UF2":
        if not chip:
            return FirmwareType.IGNORED_HEADER
        try:
            from ltchiptool import get_version
            from uf2tool.models import Block
        except (ImportError, ModuleNotFoundError) as e:
            print(
                f"!!! Can't read file '{base}' because ltchiptool is not installed. "
                "Ignoring UF2 file.",
                file=sys.stderr,
            )
            return FirmwareType.INVALID
        get_version()
        block = Block()
        block.decode(header)
        if UF2_FAMILY_MAP[chip] != block.family.id:
            return FirmwareType.IGNORED_HEADER
        return FirmwareType.VALID_UF2
    
def extract_uf2(file_with_path: str, firmware_dir: str, chip: str) -> str:
    target = file_with_path + "-" + chip.lower() + UF2_UG_SUFFIX
    print(f"Extracting UF2 package as '{basename(target)}'")

    from ltchiptool.util.intbin import inttobe32
    from uf2tool import OTAScheme, UploadContext
    from uf2tool.models import UF2

    with open(file_with_path, "rb") as f:
        uf2 = UF2(f)
        uf2.read()
        uctx = UploadContext(uf2)

    # BK7231 is single-OTA
    data = uctx.collect_data(OTAScheme.DEVICE_SINGLE)
    if len(data) != 1:
        print("!!! Incompatible UF2 package - got too many chunks!")
        exit(2)
    _, io = data.popitem()
    rbl = io.read()

    file_with_path = abspath(join(firmware_dir, target))
    with open(file_with_path, "wb") as f:
        # build Tuya UG header
        header = b"\x55\xAA\x55\xAA"
        header += b"1.0.0".ljust(12, b"\x00")
        header += inttobe32(len(rbl))
        header += inttobe32(sum(rbl))
        header += inttobe32(sum(header))
        header += b"\xAA\x55\xAA\x55"
        f.write(header)
        # write RBL data
        f.write(rbl)
    return file_with_path


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
    device, profile = None, None
    if isdir(profile_dir):
        device, profile = load_profile(profile_dir)
        if device is None or profile is None:
            print(
                "Custom device or profile is not present, "
                "attempting to download from API."
            )
    if device is None or profile is None:
        device, profile = download_profile(device_slug)
        save_profile(profile_dir, device, profile)
    # write profile data if found
    path = save_combined_profile(profile_dir, device, profile)
    ctx.obj["output"].write(path)


@cli.command()
@click.option(
    "-f",
    "--flashing",
    is_flag=True,
)
@click.pass_context
def choose_profile(ctx, flashing: bool = False):
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
        if flashing:
            device_slug = devices[0]["slug"]
        else:
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
@click.option(
    "-c",
    "--chip",
    type=click.Choice(["bk7231t", "bk7231n"], case_sensitive=False),
    default=None,
)
@click.pass_context
def choose_firmware(ctx, chip: str = None):
    chip = chip and chip.upper()
    firmware_dir = ctx.obj["firmware_dir"]
    files = listdir(firmware_dir)
    options = {}
    invalid_filenames = {}
    for file in files:
        if file.startswith(".") or file.endswith(".md"):
            continue
        if file.endswith(UF2_UG_SUFFIX):
            continue
        path = join(firmware_dir, file)
        fw_type = validate_firmware_file_internal(path, chip and chip.lower())
        if fw_type in [FirmwareType.VALID_UG, FirmwareType.VALID_UF2]:
            options[file] = fw_type
        elif fw_type in [FirmwareType.INVALID]:
            invalid_filenames[file] = file

    if not options:
        print(
            "No valid custom firmware files were found!\n"
            "Add files to the custom-firmware/ directory first.",
            file=sys.stderr,
        )
        exit(1)
        
    if invalid_filenames:
        print("\nThe following files were ignored because they do not meet naming requirements and the chip type could not be determined:")
        for invalid_filename in invalid_filenames:
            print(invalid_filename)
        print("Please see https://github.com/tuya-cloudcutter/tuya-cloudcutter/tree/main/custom-firmware#naming-rules for more information.\n")

    prompt = "Select your custom firmware file"
    if chip:
        prompt += f" for {chip} chip"

    file = ask_options(prompt, sorted(options.keys(), key=str.casefold))
    file_with_path = abspath(join(firmware_dir, file))
    fw_type = options[file]

    if fw_type == FirmwareType.VALID_UF2:
        file_with_path = extract_uf2(file_with_path, firmware_dir, chip)

    ctx.obj["output"].write(basename(file_with_path))

@cli.command()
@click.argument("filename", type=str)
@click.option(
    "-c",
    "--chip",
    type=click.Choice(["bk7231t", "bk7231n"], case_sensitive=False),
    default=None,
)
@click.pass_context
def validate_firmware_file(ctx, filename: str, chip: str = None):
    chip = chip and chip.upper()
    firmware_dir = ctx.obj["firmware_dir"]
    fw_type = validate_firmware_file_internal(join(firmware_dir, filename), chip and chip.lower())
    if fw_type not in [FirmwareType.VALID_UG, FirmwareType.VALID_UF2]:
        print(
            f"The firmware file supplied ({filename}) is not valid for the chosen profile type of {chip}",
            file=sys.stderr,
        )
        exit(1)

    file_with_path = abspath(join(firmware_dir, filename))

    if fw_type == FirmwareType.VALID_UF2:
        file_with_path = extract_uf2(file_with_path, firmware_dir, chip)

    ctx.obj["output"].write(basename(file_with_path))

if __name__ == "__main__":
    cli(obj={})
