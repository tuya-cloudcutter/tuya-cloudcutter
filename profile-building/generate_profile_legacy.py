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

    profile = load_file("legacy_profile")
    schema_id = load_file("schema_id")
    schema = load_file("schema")

    if profile is None or schema_id is None or schema is None:
        print("[!] Directory has not been fully processed, unable to generate legacy profile")
        return

    if not os.path.exists(os.path.join(full_path, "profile-legacy")):
        os.makedirs(os.path.join(full_path, "profile-legacy"))

    print("[+] Creating legacy profile")
    with open(os.path.join(full_path, "profile-legacy", "profile"), 'w') as f:
        f.write(profile)

    if schema_id is not None and schema is not None:
        schema_dict = {}
        schema_dict[f"{schema_id}"] = schema

    print(f"[+] Creating tuya.device.active.json")
    with open(os.path.join(full_path, "profile-legacy", "tuya.device.active.json"), 'w') as f:
        escaped_schema = schema.replace('"', '\\"')
        f.write('{"result":{"schema":"%s","devId":"bf27a86f49bf35f70c7ign","resetFactory":false,"timeZone":"+02:00","capability":1025,"secKey":"bfd40216f0b7f1b1","stdTimeZone":"+01:00","schemaId":"%s","dstIntervals":[[1648342800,1667091600],[1679792400,1698541200],[1711846800,1729990800],[1743296400,1761440400],[1774746000,1792890000]],"localKey":"a8e1099488f00ad3"},"t":1649240023,"success":true}' % (escaped_schema, schema_id))

    with open(os.path.join(full_path, "profile-legacy", "atop.online.debug.log.json"), 'w') as f:
        f.write('{"result": true, "t": 1644817605, "success": true}')
    with open(os.path.join(full_path, "profile-legacy", "tuya.device.dynamic.config.ack.json"), 'w') as f:
        f.write('{"t": 1644817608, "success": true}')
    with open(os.path.join(full_path, "profile-legacy", "tuya.device.dynamic.config.get.json"), 'w') as f:
        f.write('{"result":{"ackId":"0-0","validTime":1800,"time":1640995200,"config":{"stdTimeZone":"+01:00","dstIntervals":[[1648342800,1667091600],[1679792400,1698541200]]},"timezone":{"ackId":"0-0","validTime":1800,"time":1640995200,"config":{"stdTimeZone":"+01:00","dstIntervals":[[1648342800,1667091600],[1679792400,1698541200]]}}},"t":1640995200,"success":true}')
    with open(os.path.join(full_path, "profile-legacy", "tuya.device.timer.count.json"), 'w') as f:
        f.write('{"result": {"devId": "bf8d34cb20a1497360ivjw", "count": 0, "lastFetchTime": 0}, "t": 1644817612, "success": true}')
    with open(os.path.join(full_path, "profile-legacy", "tuya.device.upgrade.silent.get.json"), 'w') as f:
        f.write('{"t": 1644817611, "success": true}')
    with open(os.path.join(full_path, "profile-legacy", "tuya.device.uuid.pskkey.get"), 'w') as f:
        f.write('{"result": {"pskKey": "NA"}, "t": 1644817598, "success": true}')

def run(processed_directory: str):
    global full_path, base_name
    full_path = processed_directory
    base_name = os.path.basename(os.path.normpath(full_path))

    assemble()
    return

if __name__ == '__main__':
    if not sys.argv[1:]:
        print('Usage: python generate_profile_legacy.py <processed_directory>')
        sys.exit(1)
    
    run(sys.argv[1])
