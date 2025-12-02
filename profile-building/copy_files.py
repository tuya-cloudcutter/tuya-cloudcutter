import json
import os
import os.path
import shutil
import sys


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
    global current_dir
    current_dir = os.path.dirname(full_filename)
    base_name = os.path.basename(full_filename.replace('.bin', ''))
    extract_folder_name = base_name
    extract_folder_path = os.path.abspath(extract_folder_name)

    issue = load_file("issue.txt")
    if issue is not None:
        with open(os.path.join(extract_folder_path, base_name + "_issue.txt"), 'w') as issueFile:
            issueFile.write(issue)

    image = load_file("image.jpg")
    if image is not None:
        with open(os.path.join(extract_folder_path, base_name + "_image.jpg"), 'wb') as imageFile:
            imageFile.write(image)

    schemaId = load_file("schema_id.txt")
    if schemaId is not None:
        with open(os.path.join(extract_folder_path, base_name + "_schema_id.txt"), 'w') as schemaIdFile:
            schemaIdFile.write(schemaId)

    schema = load_file("schema.txt")
    if schema is not None:
        with open(os.path.join(extract_folder_path, base_name + "_schema.txt"), 'w') as schemaFile:
            schemaFile.write(schema)

    storage = load_file("storage.json")
    if storage is not None:
        with open(os.path.join(extract_folder_path, base_name + "_storage.json"), 'w') as storageFile:
            storageFile.write(storage)

    user_param_key = load_file("user_param_key.json")
    if user_param_key is not None:
        with open(os.path.join(extract_folder_path, base_name + "_user_param_key.json"), 'w') as userParamKeyFile:
            userParamKeyFile.write(user_param_key)
    
    decrypted_app_bin = load_file("app.bin")
    if decrypted_app_bin is not None:
        with open(os.path.join(extract_folder_path, base_name + "_active_app.bin"), 'wb') as decryptedAppFile:
            decryptedAppFile.write(decrypted_app_bin)

    ap_ssid = load_file("ap_ssid.txt")
    if ap_ssid is not None:
        with open(os.path.join(extract_folder_path, base_name + "_ap_ssid.txt"), 'w') as apSsidFile:
            apSsidFile.write(ap_ssid)


if __name__ == '__main__':
    run(sys.argv)
