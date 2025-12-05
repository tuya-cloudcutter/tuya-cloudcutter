import json
import os
import os.path
import shutil
import sys

from bk7231tools.analysis.kvstorage import KVStorage
from ltchiptool.commands.flash.split import cli as ltchiptool_split_cli
from ltchiptool import Board


def run(full_filename: str, process_inactive_app: bool = False):
    global current_dir
    current_dir = os.path.dirname(full_filename)
    base_name = os.path.basename(full_filename.replace('.bin', ''))
    extract_folder_name = base_name
    if process_inactive_app:
        extract_folder_name += '.inactive_app'
    extract_folder_path = os.path.abspath(extract_folder_name)

    if not os.path.exists(extract_folder_name) or not os.path.exists(os.path.join(extract_folder_path, base_name + "_active_app.bin")):
        try:
            with open(full_filename, "rb") as f:
                ltchiptool_split_cli.callback(Board("generic-rtl8720cf-2mb-896k"), f, extract_folder_path, True, True)
                f.seek(0) # Reset file pointer to beginning after split.
                result = KVStorage.find_storage(f.read())
                if not result:
                    raise ValueError("File doesn't contain known storage area")

                _, data = result
                try:
                    kvs = KVStorage.decrypt_and_unpack(data)
                except Exception:
                    raise RuntimeError("Couldn't unpack storage data - see program logs")

                try:
                    storage = kvs.read_all_values_parsed()
                except Exception:
                    raise RuntimeError("Couldn't parse storage data - see program logs")

                storage = json.dumps(storage, indent="\t")
                with open(os.path.join(extract_folder_path, base_name + "_storage.json"), 'wb') as storageFile:
                    storageFile.write(storage.encode('utf-8'))
                json_data = json.loads(storage)
                if "user_param_key" in json_data:
                    with open(os.path.join(extract_folder_path, base_name + "_user_param_key.json"), 'wb') as upkFile:
                        upkFile.write(json.dumps(json_data["user_param_key"], indent="\t").encode('utf-8'))
        except Exception as ex:
            print(ex)
            raise ex

        dirListing = os.listdir(extract_folder_path)

        active_ota_index = 0

        for file in dirListing:
            if file.startswith("001000_system_"):
                with open(os.path.join(extract_folder_path, file), 'rb') as systemFile:
                    systemFile.seek(4)
                    active_partition_int = int.from_bytes(systemFile.read(4), 'little')
                    active_ota_index = bin(active_partition_int).count('1') % 2 + 1

        # swap active partitions if processing inactive app
        if process_inactive_app:
            active_ota_index = active_ota_index % 2 + 1

        for file in dirListing:
            if active_ota_index == 1 and file.startswith("010000_ota1_"):
                shutil.copyfile(os.path.join(extract_folder_path, file), os.path.join(extract_folder_path, base_name + "_active_app.bin"))
            elif active_ota_index == 2 and file.startswith("0F0000_ota2_"):
                shutil.copyfile(os.path.join(extract_folder_path, file), os.path.join(extract_folder_path, base_name + "_active_app.bin"))
    else:
        print('[+] bin has already been extracted')
        return


if __name__ == '__main__':
    run(sys.argv)
