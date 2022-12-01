import sys
import json
import os.path

def write_file(key, value):
    with open(os.path.join(base_folder, base_name + "_" + key + ".txt"), "w") as file:
        file.write(value)

def dump(file):
    with open(file, "r") as storage_file:
        storage = json.load(storage_file)
        global base_name, base_folder
        base_name = os.path.basename(file)[:-13]
        base_folder = os.path.dirname(file)
        print(f"[+] uuid: {storage['gw_bi']['uuid']}")
        write_file("uuid", storage['gw_bi']['uuid'])
        print(f"[+] auth_key: {storage['gw_bi']['auth_key']}")
        write_file("auth_key", storage['gw_bi']['auth_key'])
        print(f"[+] ap_ssid: {storage['gw_bi']['ap_ssid']}")
        write_file("ap_ssid", storage['gw_bi']['ap_ssid'])
        # Not all firmwares have version information in storage
        if 'gw_di' in storage:
            if 'swv' in storage['gw_di']:
                print(f"[+] swv: {storage['gw_di']['swv']}")
                write_file("swv", storage['gw_di']['swv'])
            else:
                print(f"[+] swv: 0.0.0")
                write_file("swv", "0.0.0")
            print(f"[+] bv: {storage['gw_di']['bv']}")
            write_file("bv", storage['gw_di']['bv'])
            if 'firmk' in storage['gw_di'] and storage['gw_di']['firmk'] is not None:
                print(f"[+] firmware key: {storage['gw_di']['firmk']}")
                write_file("firmware_key", storage['gw_di']['firmk'])     
            if 'pk' in storage['gw_di'] and storage['gw_di']['pk'] is not None:
                print(f"[+] product key: {storage['gw_di']['pk']}")
                write_file("product_key", storage['gw_di']['pk'])
            if 's_id' in storage['gw_di'] and storage['gw_di']['s_id'] is not None:
                schema_id = storage['gw_di']['s_id']
                if schema_id in storage:
                    print(f"[+] schema: {storage[schema_id]}")
                    print(f"[+] schema {schema_id}:")
                    write_file("schema_id", schema_id)
                    write_file("schema", json.dumps(storage[schema_id]))
        else:
            print("[!] No gw_di, No version or key stored, manual lookup required")
            write_file("manually_process", "No version or key stored, manual lookup required")

def run(storage_file: str):
    if not storage_file:
        print('Usage: python parse_storage.py <storage.json file>')
        sys.exit(1)

    if os.path.exists(storage_file):
        dump(storage_file)
    else:
        print('[!] Storage file not found')
        return

if __name__ == '__main__':
    run(sys.argv[1])
