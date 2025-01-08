import json
import os.path
import sys


def write_file(key, value: str):
    try:
        with open(os.path.join(base_folder, base_name + "_" + key + ".txt"), "x") as file:
            file.write(value)
    except:
        return

def dump(file):
    with open(file, "r") as storage_file:
        storage = json.load(storage_file)
        global base_name, base_folder
        base_name = os.path.basename(file)[:-13]
        base_folder = os.path.dirname(file)
        factory_pin = None
        firmware_key = None
        product_key = None
        if 'gw_bi' in storage and storage['gw_bi']:
            print(f"[+] uuid: {storage['gw_bi']['uuid']}")
            write_file("uuid", storage['gw_bi']['uuid'])
            print(f"[+] auth_key: {storage['gw_bi']['auth_key']}")
            write_file("auth_key", storage['gw_bi']['auth_key'])
            print(f"[+] ap_ssid: {storage['gw_bi']['ap_ssid']}")
            write_file("ap_ssid", storage['gw_bi']['ap_ssid'])
            if 'fac_pin' in storage['gw_bi'] and storage['gw_bi']['fac_pin'] is not None:
                factory_pin = storage['gw_bi']['fac_pin']
                print(f"[+] factory pin: {factory_pin}")
                write_file("factory_pin", factory_pin)
        # Not all firmwares have version information in storage
        if 'gw_di' in storage:
            if 'swv' in storage['gw_di']:
                print(f"[+] storage swv: {storage['gw_di']['swv']}")
                write_file("swv", storage['gw_di']['swv'])
            else:
                print(f"[+] storage swv: 0.0.0")
                write_file("swv", "0.0.0")
            if 'dev_swv' in storage['gw_di']:
                print(f"[+] storage dev_swv: {storage['gw_di']['dev_swv']}")
                write_file("mcuswv", storage['gw_di']['dev_swv'])
            else:
                print(f"[+] storage dev_swv: 0.0.0")
                write_file("mcuswv", "0.0.0")
            if 'bv' in storage['gw_di']:
                print(f"[+] storage bv: {storage['gw_di']['bv']}")
                write_file("bv", storage['gw_di']['bv'])
            else:
                print(f"[+] storage bv: 0.0.0")
                write_file("bv", "0.0.0")
            if 'firmk' in storage['gw_di'] and storage['gw_di']['firmk'] is not None:
                firmware_key = storage['gw_di']['firmk']
                print(f"[+] firmware key: {firmware_key}")
                write_file("firmware_key", firmware_key)
            if 'pk' in storage['gw_di'] and storage['gw_di']['pk'] is not None:
                product_key = storage['gw_di']['pk']
                print(f"[+] product key: {product_key}")
                write_file("product_key", product_key)
            if 's_id' in storage['gw_di'] and storage['gw_di']['s_id'] is not None:
                schema_id = storage['gw_di']['s_id']
                if schema_id in storage:
                    if write_file("schema_id", schema_id):
                        print(f"[+] schema: {storage[schema_id]}")
                    if write_file("schema", json.dumps(storage[schema_id])):
                        print(f"[+] schema {schema_id}:")
        if 'baud_cfg' in storage and 'baud' in storage['baud_cfg']:
            print(f"[+] TuyaMCU baud: {storage['baud_cfg']['baud']}")
            write_file("tuyamcu_baud", f"{storage['baud_cfg']['baud']}")
        elif 'uart_adapt_params' in storage and 'uart_baud' in storage['uart_adapt_params']:
            print(f"[+] TuyaMCU baud: {storage['uart_adapt_params']['uart_baud']}")
            write_file("tuyamcu_baud", f"{storage['uart_adapt_params']['uart_baud']}")
        if not firmware_key and not product_key and not factory_pin:
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
