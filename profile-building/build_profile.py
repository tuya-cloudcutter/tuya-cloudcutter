from enum import Enum
import os.path
import sys

import extract_beken
import extract_rtl8720cf
import generate_profile_classic
import haxomatic
import process_app
import process_storage
import pull_schema


class Platform(Enum):
    BEKEN = "BEKEN",
    RTL8720CF = "RTL8720CF"

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

    file = sys.argv[1]
    output_dir = file.replace('.bin', '')
    base_name = os.path.basename(output_dir)
    dirname = os.path.dirname(file)
    storage_file = os.path.join(dirname, base_name, base_name + '_storage.json')
    app_file = os.path.join(dirname, base_name, base_name + '_active_app.bin')
    schema_id_file = os.path.join(dirname, base_name, base_name + '_schema_id.txt')
    extracted_location = os.path.join(dirname, base_name)

    if base_name.count('_') != 1 or base_name.count(' ') > 0:
        print_filename_instructions()
        sys.exit(2)

    print(f"[+] Processing {file=} as {base_name}")

    extract_platform = None
    with open(file, 'rb') as fs:
        appcode = fs.read()
        if appcode.find(b'Ameba', 0) > -1:
            extract_platform = Platform.RTL8720CF
        else:
            extract_platform = Platform.BEKEN

    if extract_platform == Platform.BEKEN:
        extract_beken.run(file)
    elif extract_platform == Platform.RTL8720CF:
        extract_rtl8720cf.run(file)
    else:
        raise("no platform?")
    haxomatic.run(app_file)
    process_storage.run(storage_file)
    process_app.run(app_file)

    if not os.path.exists(schema_id_file):
        pull_schema.run_directory(extracted_location, token)
    else:
        print('[+] Schema already present')

    if not os.path.exists(schema_id_file):
        print("[!] Unable to build complete profile as schema remains missing.")
        exit(1)

    generate_profile_classic.run(extracted_location)
