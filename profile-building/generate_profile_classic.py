import json
import os
import os.path
import sys

full_path: str
base_name: str


def load_file(filename):
    permission = 'r'
    if filename.endswith(".jpg"):
        permission += 'b'
    path = os.path.join(full_path, f"{base_name}_{filename}")
    if os.path.exists(path):
        with open(path, permission) as f:
            return f.read()
    return None


def assemble():
    if os.path.exists(full_path) == False:
        print("[!] Unable to find device directory name")
        return

    patched = load_file("patched.txt")
    if patched:
        print("==============================================================================================================")
        print("[!] The binary supplied appears to be patched and no longer vulnerable to the tuya-cloudcutter exploit.")
        print("==============================================================================================================")
        return

    # All should have these
    manufacturer = base_name.split('_')[0].replace('-', ' ').replace("   ", "-")
    name = base_name.split('_')[1].replace('-', ' ').replace("   ", "-")
    device_class = load_file("device_class.txt")
    chip = load_file("chip.txt")
    sdk = load_file("sdk.txt")
    bv = load_file("bv.txt")
    ap_ssid = load_file("ap_ssid.txt")
    haxomatic_matched = load_file("haxomatic_matched.txt") is not None
    icon = load_file("icon.txt")

    if haxomatic_matched is None:
        print("[!] Directory has not been fully processed, unable to generate classic profile")
        return

    # Optional items
    swv = load_file("swv.txt")
    if swv is None:
        swv = "0.0.0"
    product_key = load_file("product_key.txt")
    firmware_key = load_file("firmware_key.txt")
    address_finish = load_file("address_finish.txt")
    address_datagram = load_file("address_datagram.txt")
    address_ssid = load_file("address_ssid.txt")
    address_ssid_padding = load_file("address_ssid_padding.txt")
    address_passwd = load_file("address_passwd.txt")
    address_passwd_padding = load_file("address_passwd_padding.txt")
    address_token = load_file("address_token.txt")
    address_token_padding = load_file("address_token_padding.txt")
    schema_id = load_file("schema_id.txt")
    schema = load_file("schema.txt")
    if schema is not None and schema != '':
        schema = json.loads(schema)
    issue = load_file("issue.txt")
    image = load_file("image.jpg")
    device_configuration = load_file("user_param_key.json")
    tuyamcu_baud = load_file("tuyamcu_baud.txt")

    profile = {}
    firmware = {}
    data = {}

    profile["name"] = f"{swv} - {chip}"
    profile["sub_name"] = device_class
    profile["type"] = "CLASSIC"
    profile["icon"] = icon

    firmware["chip"] = chip
    firmware["name"] = device_class
    firmware["version"] = swv
    firmware["sdk"] = f"{sdk}-{bv}"
    if firmware_key is not None:
        firmware["key"] = firmware_key

    profile["firmware"] = firmware

    data["address_finish"] = address_finish
    if address_datagram is not None:
        data["address_datagram"] = address_datagram
    if address_ssid is not None:
        data["address_ssid"] = address_ssid
        if address_ssid_padding is not None:
            data["address_ssid_padding"] = int(address_ssid_padding)
    if address_passwd is not None:
        data["address_passwd"] = address_passwd
        if address_passwd_padding is not None:
            data["address_passwd_padding"] = int(address_passwd_padding)
    if address_token is not None:
        data["address_token"] = address_token
        if address_token_padding is not None:
            data["address_token_padding"] = int(address_token_padding)

    profile["data"] = data

    if not os.path.exists(os.path.join(full_path, "profile-classic")):
        os.makedirs(os.path.join(full_path, "profile-classic"))
    if not os.path.exists(os.path.join(full_path, "profile-classic", "devices")):
        os.makedirs(os.path.join(full_path, "profile-classic", "devices"))
    if not os.path.exists(os.path.join(full_path, "profile-classic", "images")):
        os.makedirs(os.path.join(full_path, "profile-classic", "images"))
    if not os.path.exists(os.path.join(full_path, "profile-classic", "profiles")):
        os.makedirs(os.path.join(full_path, "profile-classic", "profiles"))

    classic_profile_name = f"{device_class.replace('_', '-')}-{swv}-sdk-{sdk}-{bv}".lower()

    print(f"[+] Creating classic profile {classic_profile_name}")
    with open(os.path.join(full_path, "profile-classic", "profiles", f"{classic_profile_name}.json"), 'w') as f:
        f.write(json.dumps(profile, indent='\t'))
        f.write('\n')

    device = {}
    device["manufacturer"] = manufacturer
    device["name"] = name
    device_filename = f"{manufacturer.replace(' ', '-')}-{name.replace(' ', '-')}".lower()
    # this won't be used in exploiting, bit it is useful to have a known one
    # in case we need to regenerate schemas from Tuya's API
    # device["uuid"] = uuid
    # device["auth_key"] = auth_key
    if product_key is not None:
        device["key"] = product_key
    device["ap_ssid"] = ap_ssid
    device["github_issues"] = []

    if issue is not None:
        device["github_issues"].append(int(issue))

    device["image_urls"] = []

    if image is not None:
        device["image_urls"].append(device_filename + ".jpg")

    device["profiles"] = [classic_profile_name]

    if schema_id is not None and schema is not None:
        schema_dict = {}
        schema_dict[f"{schema_id}"] = schema
        device["schemas"] = schema_dict
    else:
        print("[!] Schema is not present, unable to generate classic device file")
        return

    if device_configuration is not None:
        device["device_configuration"] = json.loads(device_configuration)

    if tuyamcu_baud is not None:
        device["tuyamcu_baud"] = tuyamcu_baud

    # version cleanup
    name_end = device["name"].split()[-1]
    # version is present, but doesn't match what is being processed, correct it
    if name_end.startswith("v") and name_end != f"v{swv}":
        device["name"] = device["name"].replace(name_end, f"v{swv}")
        device_filename = device_filename.replace(name_end, f"v{swv}")
    # no version present, add it
    if not name_end.startswith("v"):
        device["name"] = f"{device['name']} v{swv}"
        device_filename = f"{device_filename}-v{swv}"

    print(f"[+] Creating device profile {device_filename}")
    with open(os.path.join(full_path, "profile-classic", "devices", f"{device_filename}.json"), 'w') as f:
        f.write(json.dumps(device, indent='\t'))
        f.write('\n')

    if image is not None:
        with open(os.path.join(full_path, "profile-classic", "images", f"{device_filename}.jpg"), 'wb') as f:
            f.write(image)


def run(processed_directory: str):
    global full_path, base_name
    full_path = processed_directory
    base_name = os.path.basename(os.path.normpath(full_path)).replace('.inactive_app', '')

    assemble()
    return


if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: python generate_classic.py <processed_directory>')
        sys.exit(1)

    run(sys.argv[1])
