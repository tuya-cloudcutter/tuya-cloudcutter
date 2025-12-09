import argparse
import os
import os.path
import sys

import bk7231tools


def run(full_encrypted_file: str):
    global current_dir
    current_dir = os.path.dirname(full_encrypted_file)
    base_name = os.path.basename(full_encrypted_file.replace('.bin', ''))
    extract_folder_name = base_name
    extract_folder_path = os.path.abspath(extract_folder_name)
    input = argparse.ArgumentParser()
    input.layout = 'ota_1'
    input.rbl = ''
    input.file = full_encrypted_file
    input.output_dir = os.path.join(extract_folder_path)
    input.extract = True
    input.storage = False

    if not os.path.exists(extract_folder_path) or not os.path.exists(os.path.join(extract_folder_path, base_name + "_active_app.bin")):
        try:
            bk7231tools.__main__.dissect_dump_file(input)
        except Exception as ex:
            print(ex)

        dirListing = os.listdir(extract_folder_path)

        for file in dirListing:
            if file.endswith('app_pattern_scan.bin'):
                os.rename(os.path.join(extract_folder_path, file), os.path.join(extract_folder_path, file.replace('app_pattern_scan.bin', 'app_1.00.bin')))
            elif file.endswith('app_pattern_scan_decrypted.bin'):
                os.rename(os.path.join(extract_folder_path, file), os.path.join(extract_folder_path, file.replace('app_pattern_scan_decrypted.bin', 'active_app.bin')))
            elif file.endswith('app_1.00_decrypted.bin'):
                os.rename(os.path.join(extract_folder_path, file), os.path.join(extract_folder_path, file.replace('app_1.00_decrypted.bin', 'active_app.bin')))
    else:
        print('[+] Encrypted bin has already been extracted')
        return


if __name__ == '__main__':
    run(sys.argv[1])
