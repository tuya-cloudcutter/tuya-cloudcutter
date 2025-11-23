import os
import os.path
import shutil
import sys

from ltchiptool.commands.flash.split import cli
from ltchiptool import Board


def load_file(filename: str):
    global current_dir
    permission = 'r'
    if filename.endswith(".jpg") or filename.endswith(".bin"):
        permission += 'b'
    if os.path.exists(os.path.join(current_dir, filename)):
        with open(os.path.join(current_dir, filename), permission) as f:
            return f.read()
    return None


def run(full_filename: str):
    if full_filename is None or full_filename == '':
        print('Usage: python extract.py <full 2M bin file>')
        sys.exit(1)

    if not full_filename.__contains__('_') or full_filename.__contains__(' ') or not full_filename.endswith('.bin'):
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
    current_dir = os.path.dirname(full_filename)
    output_dir = full_filename.replace('.bin', '')
    extractfolder = os.path.abspath(output_dir)
    foldername = os.path.basename(output_dir)

    if not os.path.exists(extractfolder) or not os.path.exists(os.path.join(extractfolder, foldername + "_active_app.bin")):
        try:
            with open(full_filename, "rb") as f:
                cli.callback(Board("generic-rtl8720cf-2mb-896k"), f, extractfolder, True, True)
        except Exception as ex:
            raise ex

        dirListing = os.listdir(extractfolder)

        active_ota_index = 0

        for file in dirListing:
            if file == "001000_system_E782.bin":
                active_ota_index = 1
            elif file == "001000_system_8959.bin":
                active_ota_index = 2

        for file in dirListing:
            if active_ota_index == 1 and file.startswith("010000_ota1_"):
                shutil.copyfile(os.path.join(extractfolder, file), os.path.join(extractfolder, foldername + "_active_app.bin"))
            elif active_ota_index == 2 and file.startswith("0F0000_ota2_"):
                shutil.copyfile(os.path.join(extractfolder, file), os.path.join(extractfolder, foldername + "_active_app.bin"))

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

        storage = load_file("storage.json")
        if storage is not None:
            with open(os.path.join(extractfolder, foldername + "_storage.json"), 'w') as storageFile:
                storageFile.write(storage)

        user_param_key = load_file("user_param_key.json")
        if user_param_key is not None:
            with open(os.path.join(extractfolder, foldername + "_user_param_key.json"), 'w') as userParamKeyFile:
                userParamKeyFile.write(user_param_key)
        
        decrypted_app_bin = load_file("app.bin")
        if decrypted_app_bin is not None:
            with open(os.path.join(extractfolder, foldername + "_active_app.bin"), 'wb') as decryptedAppFile:
                decryptedAppFile.write(decrypted_app_bin)

        ap_ssid = load_file("ap_ssid.txt")
        if ap_ssid is not None:
            with open(os.path.join(extractfolder, foldername + "_ap_ssid.txt"), 'w') as apSsidFile:
                apSsidFile.write(ap_ssid)
    else:
        print('[+] bin has already been extracted')
        return


if __name__ == '__main__':
    run(sys.argv[1])
