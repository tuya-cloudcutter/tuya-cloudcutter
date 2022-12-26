import argparse
import os
import os.path
import sys

import bk7231tools


def load_file(filename: str):
    global current_dir
    permission = 'r'
    if filename.endswith(".jpg"):
        permission += 'b'
    if os.path.exists(os.path.join(current_dir, filename)):
        with open(os.path.join(current_dir, filename), permission) as f:
            return f.read()
    return None


def run(full_encrypted_file: str):
    if full_encrypted_file is None or full_encrypted_file == '':
        print('Usage: python extract.py <full 2M encrypted bin file>')
        sys.exit(1)

    if not full_encrypted_file.__contains__('_') or full_encrypted_file.__contains__(' ') or not full_encrypted_file.endswith('.bin'):
        print('Filename must match specific rules in order to properly generate a useful profile.')
        print('The general format is Manufacturer-Name_Model-Number.bin')
        print('manufacturer name followed by underscore (_) followed by model are required, and the extension should be .bin')
        print('Dashes (-) should be used instead of spaces, and if there is a dash (-) in any part of the manufacturer or model, it must be replaced with 3 dashes (---) to be maintained.')
        print('There should only be one underscore (_) present, separating manufacturer name and model')
        print('Example: a Tuya Generic DS-101 would become Tuya-Generic_DS---101.bin')
        print('Adding the general device type to the end of the model is recommended.')
        print('Examples: Tuya-Generic_DS---101-Touch-Switch.bin or Tuya-Generic_A60-E26-RGBCT-Bulb.bin')
        sys.exit(1)

    global current_dir, extractfolder, foldername
    current_dir = os.path.dirname(full_encrypted_file)
    output_dir = full_encrypted_file.replace('.bin', '')
    extractfolder = os.path.abspath(output_dir)
    foldername = os.path.basename(output_dir)
    input = argparse.ArgumentParser()
    input.layout = 'ota_1'
    input.rbl = ''
    input.file = full_encrypted_file
    input.output_dir = os.path.join(extractfolder)
    input.extract = True
    input.storage = False

    if not os.path.exists(extractfolder) or not os.path.exists(os.path.join(extractfolder, foldername + "_app_1.00_decrypted.bin")):
        bk7231tools.__main__.dissect_dump_file(input)
        dirListing = os.listdir(extractfolder)

        for file in dirListing:
            if file.endswith('app_pattern_scan.bin'):
                os.rename(os.path.join(extractfolder, file), os.path.join(extractfolder, file.replace('app_pattern_scan.bin', 'app_1.00.bin')))
            elif file.endswith('app_pattern_scan_decrypted.bin'):
                os.rename(os.path.join(extractfolder, file), os.path.join(extractfolder, file.replace('app_pattern_scan_decrypted.bin', 'app_1.00_decrypted.bin')))

        issue = load_file("issue.txt")
        if issue is not None:
            with open(os.path.join(extractfolder, foldername + "_issue.txt"), 'w') as issueFile:
                issueFile.write(issue)

        image = load_file("image.jpg")
        if image is not None:
            with open(os.path.join(extractfolder, foldername + "_image.jpg"), 'wb') as imageFile:
                imageFile.write(image)

        schemaId = load_file("schema_id.txt")
        if schemaId is not None:
            with open(os.path.join(extractfolder, foldername + "_schema_id.txt"), 'w') as schemaIdFile:
                schemaIdFile.write(schemaId)

        schema = load_file("schema.txt")
        if schema is not None:
            with open(os.path.join(extractfolder, foldername + "_schema.txt"), 'w') as schemaFile:
                schemaFile.write(schema)
    else:
        print('[+] Encrypted bin has already been extracted')
        return


if __name__ == '__main__':
    run(sys.argv[1])
