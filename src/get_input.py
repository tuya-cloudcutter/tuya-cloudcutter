import os, sys
import inquirer


def ask_options(text, options):
    return inquirer.prompt([inquirer.List('result', carousel=True, message=text, choices=options)])


def ask_files(text, dir):
    files = [path for path in os.listdir(dir) if not path.startswith(".")]
    return ask_options(text, sorted(files, key=str.casefold))['result']


def ask_device_type():
    profile_dir = "/work/device-profiles"
    manufacturer = ask_files("Select the brand of your device", profile_dir)
    device = ask_files("Select the article number of your device", f"{profile_dir}/{manufacturer}")
    return manufacturer, device


def ask_custom_firmware(firmware_dir):
    return f"{ask_files('Select your custom firmware file', firmware_dir)}"


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
    output_file = open(sys.argv[2], "wt")
    if input_type == "device":
        manufacturer, device = ask_device_type()
        print(f"{manufacturer}/{device}", file=output_file)
    elif input_type == "firmware":
        firmware_dir = "/work/custom-firmware"
        firmware = ask_custom_firmware(firmware_dir)
        firmware_file_path = os.path.join(firmware_dir, firmware)
        validate_firmware_file(firmware_file_path)
        print(f"{firmware}", file=output_file)
