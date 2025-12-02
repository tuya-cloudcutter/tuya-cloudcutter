from enum import Enum
import os.path
import sys

import extract_beken
import extract_rtl8720cf
import extract_rtl8710bn
import copy_files
import generate_profile_classic
import haxomatic
import process_app
import process_storage
import pull_schema


class Platform(Enum):
    BEKEN = "BEKEN",
    RTL8720CF = "RTL8720CF",
    RTL8710BN = "RTL8710BN",


def print_filename_instructions():
    print('Encrypted bin name must be in the pattern of Manufacturer-Name_Model-and-device-description')
    print('Use dashes in places of spaces, and if a dash (-) is present, replace it with 3 dashes (---)')
    print('There should only be 1 underscore in the filename, separating manufacturer name and model description')


if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: python build_profile.py <full 2M encrypted bin file> <token=\'None\'>')
        print('Token is optional.  Token instructions will prompt if needed.')
        print_filename_instructions()
        sys.exit(1)

    token = None
    if len(sys.argv) > 2 and sys.argv[2] is not None:
        token = sys.argv[2]

    process_inactive_app = False
    for arg in sys.argv:
        if arg == '--inactive':
            process_inactive_app = True

    file = sys.argv[1]
    base_name = os.path.basename(file.replace('.bin', ''))
    extract_folder_name = base_name
    if process_inactive_app:
        extract_folder_name += '.inactive_app'
    current_dirname = os.path.dirname(file)
    storage_file = os.path.join(current_dirname, extract_folder_name, base_name + '_storage.json')
    app_file = os.path.join(current_dirname, extract_folder_name, base_name + '_active_app.bin')
    schema_id_file = os.path.join(current_dirname, extract_folder_name, base_name + '_schema_id.txt')
    extracted_location = os.path.join(current_dirname, extract_folder_name)

    if base_name.count('_') != 1 or base_name.count(' ') > 0:
        print_filename_instructions()
        sys.exit(2)

    print(f"[+] Processing {file=} as {base_name}")

    extract_platform = None
    with open(file, 'rb') as fs:
        appcode = fs.read()
        if appcode.find(b'AmebaZII', 0) > -1:
            extract_platform = Platform.RTL8720CF
        elif appcode.find(b'81958711', 0) > -1:
            extract_platform = Platform.RTL8710BN
        else:
            extract_platform = Platform.BEKEN

    if file is None or file == '':
        print('Usage: python extract.py <full 2M encrypted bin file>')
        sys.exit(1)

    if not file.__contains__('_') or file.__contains__(' ') or not file.endswith('.bin'):
        print('Filename must match specific rules in order to properly generate a useful profile.')
        print('The general format is Manufacturer-Name_Model-Number.bin')
        print('manufacturer name followed by underscore (_) followed by model are required, and the extension should be .bin')
        print('Dashes (-) should be used instead of spaces, and if there is a dash (-) in any part of the manufacturer or model, it must be replaced with 3 dashes (---) to be maintained.')
        print('There should only be one underscore (_) present, separating manufacturer name and model')
        print('Example: a Tuya Generic DS-101 would become Tuya-Generic_DS---101.bin')
        print('Adding the general device type to the end of the model is recommended.')
        print('Examples: Tuya-Generic_DS---101-Touch-Switch.bin or Tuya-Generic_A60-E26-RGBCT-Bulb.bin')
        sys.exit(1)

    if extract_platform == Platform.BEKEN:
        extract_beken.run(file)
    elif extract_platform == Platform.RTL8720CF:
        extract_rtl8720cf.run(file, process_inactive_app)
    elif extract_platform == Platform.RTL8710BN:
        extract_rtl8710bn.run(file, process_inactive_app)
    else:
        raise("no platform?")
    
    copy_files.run(file)
    
    haxomatic.run(app_file)
    process_storage.run(storage_file, process_inactive_app)
    process_app.run(app_file)

    if not os.path.exists(schema_id_file):
        pull_schema.run_directory(extracted_location, token)
    else:
        print('[+] Schema already present')

    if not os.path.exists(schema_id_file):
        print("[!] Unable to build complete profile as schema remains missing.")
        exit(1)

    generate_profile_classic.run(extracted_location)
