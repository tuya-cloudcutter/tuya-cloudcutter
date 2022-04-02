import os, sys
import inquirer


def ask_options(text, options):
    return inquirer.prompt([inquirer.List('result', carousel=True, message=text, choices=options)])


def ask_files(text, dir):
    files = [path for path in os.listdir(dir) if not path.startswith(".")]
    return ask_options(text, files)['result']


def ask_device_type():
    profile_dir = "/work/device-profiles"
    manufacturer = ask_files("Select the brand of your device", profile_dir)
    device = ask_files("Select the article number of your device", f"{profile_dir}/{manufacturer}")
    return manufacturer, device


def ask_custom_firmware():
    firmware_dir = "/work/custom-firmware"
    return f"{firmware_dir}/{ask_files('Select your custom firmware file', firmware_dir)}"


if __name__ == "__main__":
    input_type = sys.argv[1]
    output_file = open(sys.argv[2], "wt")
    if input_type == "device":
        manufacturer, device = ask_device_type()
        print(f"{manufacturer}/{device}", file=output_file)
    elif input_type == "firmware":
        firmware = ask_custom_firmware()
        print(f"{firmware}", file=output_file)
