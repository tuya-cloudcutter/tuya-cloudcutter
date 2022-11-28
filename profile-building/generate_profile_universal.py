import json
import os, os.path
import sys

full_path: str
base_name: str

def load_file(filename):
    path = os.path.join(full_path, f"{base_name}_{filename}.txt")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return None

def assemble():
    if os.path.exists(full_path) == False:
        print("[!] Unable to find device directory name")
        return

    # All should have these
    manufacturer = base_name.split('_')[0].replace('-', ' ').replace("   ", "-")
    name = base_name.split('_')[1].replace('-', ' ').replace("   ", "-")
    
    device_class = load_file("device_class")
    chip = load_file("chip")
    sdk = load_file("sdk")
    bv = load_file("bv")
    uuid = load_file("uuid")

    ap_ssid = load_file("ap_ssid")
    auth_key = load_file("auth_key")
    address_finish = load_file("address_finish")
    icon = load_file("icon")

    if address_finish is None:
        print("[!] Directory has not been fully processed, unable to generate universal profile")
        return

    # Optional items
    swv = load_file("swv")
    if swv is None:
        swv = "0.0.0"
    key = load_file("key")
    address_datagram = load_file("address_datagram")
    address_ssid = load_file("address_ssid")
    address_passwd = load_file("address_passwd")
    schema_id = load_file("schema_id")
    schema = load_file("schema")
    if schema is not None and schema != '':
        schema = json.loads(schema)
    issue = load_file("issue")

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
    if key is not None:
        firmware["key"] = key

    profile["firmware"] = firmware

    data["address_finish"] = address_finish
    if address_datagram is not None:
        data["address_datagram"] = address_datagram
    if address_ssid is not None:
        data["address_ssid"] = address_ssid
    if address_passwd is not None:
        data["address_passwd"] = address_passwd

    profile["data"] = data

    if not os.path.exists(os.path.join(full_path, "profile-universal")):
        os.makedirs(os.path.join(full_path, "profile-universal"))
    if not os.path.exists(os.path.join(full_path, "profile-universal", "devices")):
        os.makedirs(os.path.join(full_path, "profile-universal", "devices"))
    if not os.path.exists(os.path.join(full_path, "profile-universal", "profiles")):
        os.makedirs(os.path.join(full_path, "profile-universal", "profiles"))

    universal_profile_name = f"{device_class}-{swv}-sdk-{sdk}-{bv}".lower()

    print(f"[+] Creating universal profile {universal_profile_name}")
    with open(os.path.join(full_path, "profile-universal", "profiles", f"{universal_profile_name}.json"), 'w') as f:
        f.write(json.dumps(profile, indent=4))
        f.write('\n')

    device = {}
    device["manufacturer"] = manufacturer
    device["name"] = name
    # this won't be used in exploiting, bit it is useful to have a known one
    # in case we need to regenerate schemas from Tuya's API
    device["uuid"] = uuid
    device["auth_key"] = auth_key
    device["ap_ssid"] = ap_ssid

    if issue is not None:
        device["github_issues"] = [ int(issue) ]

    device["profiles"] = [ universal_profile_name ]

    if schema_id is not None and schema is not None:
        schema_dict = {}
        schema_dict[f"{schema_id}"] = schema
        device["schema"] = schema_dict
    else:
        print("[!] Schema is not present, unable to generate universal device file")
        return

    device_filename = f"{manufacturer.replace(' ', '-')}-{name.replace(' ', '-')}".lower()
    print(f"[+] Creating device profile {device_filename}")
    with open(os.path.join(full_path, "profile-universal", "devices", f"{device_filename}.json"), 'w') as f:
        f.write(json.dumps(device, indent=4))
        f.write('\n')

def run(processed_directory: str):
    global full_path, base_name
    full_path = processed_directory
    base_name = os.path.basename(os.path.normpath(full_path))

    assemble()
    return

if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: python generate_universal.py <processed_directory>')
        sys.exit(1)
    
    run(sys.argv[1])
