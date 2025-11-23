import re
import sys
from os.path import basename, dirname, exists


def name_output_file(desired_appended_name):
    if appcode_path.endswith('active_app.bin'):
        return appcode_path.replace('active_app.bin', desired_appended_name + ".txt")
    return appcode_path + "_" + desired_appended_name + ".txt"


def read_until_null_or_newline(index):
    strlen = 0
    slice_obj = slice(index, len(appcode))
    for b in appcode[slice_obj]:
        if b != 0 and b != 10 and b != 13:
            strlen += 1
            continue
        slice_obj = slice(index, index + strlen)
        return appcode[slice_obj].decode('utf-8')


def bytecode_search(bytecode: bytes):
    offset = appcode.find(bytecode, 0)

    if offset == -1:
        return []

    matches = [offset]
    offset = appcode.find(bytecode, offset+1)
    while offset != -1:
        matches.append(offset)
        offset = appcode.find(bytecode, offset+1)

    return matches


def read_between_null_or_newline(index):
    startIndex = index
    while startIndex > 0:
        startIndex -= 1
        if appcode[startIndex] == 0 or appcode[startIndex] == 10 or appcode[startIndex] == 13:
            break
    # startIndex is now null, start after it
    startIndex += 1
    return read_until_null_or_newline(startIndex)


def find_device_class(searchPhrase):
    matches = bytecode_search(searchPhrase)
    for match in matches:
        matchText = read_between_null_or_newline(match)
        if matchText == 'BK7231S_2M':
            continue
        if '/' in matchText:
            continue
        return matchText
    return ''


def search_device_class_after_compiled_line():
    compiled_at_string = b'**********[%s] [%s] compiled at %s %s**********'
    offset = appcode.find(compiled_at_string, 0)
    if offset == -1:
        return ''
    offset += len(compiled_at_string) + 1
    for _ in range(4):
        after = read_between_null_or_newline(offset)
        offset += len(after) + 1
        if after.count('_') > 0 and after.count(' ') == 0:
            return after
    return ''


def search_device_class_after_chipid(chipid: str):
    chipid_string = b'\0' + bytes(chipid, 'utf-8') + b'\0'
    offset = appcode.find(chipid_string, 0)
    if offset == -1:
        return ''
    offset += len(chipid_string) + 1
    for _ in range(3):
        after = read_between_null_or_newline(offset)
        offset += len(after) + 1
        if after.count('_') > 0 and after.count('__') == 0 and after.count(' ') == 0:
            return after
    return ''


def search_device_class_after_swv(swv: str):
    swv_string = b'\0' + bytes(swv, 'utf-8') + b'\0'
    offset = appcode.find(swv_string, 0)
    if offset == -1:
        return ''
    offset += len(swv_string) + 1
    for _ in range(3):
        after = read_between_null_or_newline(offset)
        offset += len(after) + 1
        if after.count('_') > 0 and after.count('__') == 0 and after.count(' ') == 0:
            return after
    return ''


def search_swv_after_compiled_line():
    compiled_at_string = b'**********[%s] [%s] compiled at %s %s**********'
    offset = appcode.find(compiled_at_string, 0)
    if offset == -1:
        return ''
    offset += len(compiled_at_string) + 1
    for _ in range(4):
        after = read_between_null_or_newline(offset)
        offset += len(after) + 1
        if after.count('.') > 1:
            return after
    return ''


def search_swv_after_device_class(device_class):
    offset = appcode.find(bytes(device_class, 'utf-8'), 0)
    if offset == -1:
        return ''
    offset += len(device_class) + 1
    for _ in range(4):
        after = read_between_null_or_newline(offset)
        offset += len(after) + 1
        if after.count('.') > 1:
            return after
    return ''


def search_swv_before_device_class(device_class):
    offset = appcode.find(bytes(device_class, 'utf-8'), 0)
    if offset == -1:
        return ''
    offset -= 2
    for _ in range(4):
        after = read_between_null_or_newline(offset)
        offset += len(after) + 1
        if after.count('.') > 1:
            return after
    return ''


def search_key():
    # This will only find keys with the "key" prefix.
    # There are some non-standard ones out there that
    # may require manual finding.
    match = re.search(b"\0key[a-z0-9]{13}\0", appcode)
    if match is not None:
        return read_between_null_or_newline(match.span()[0] + 1)
    return ''


def dump():
    global base_name, base_folder
    base_name = basename(appcode_path)[:-23]
    base_folder = dirname(appcode_path)
    sdk_line = ''
    if b'< TUYA IOT SDK' in appcode:
        sdk_line = read_until_null_or_newline(appcode.index(b'< TUYA IOT SDK'))
        sdk_version = sdk_line.split()[4].split(':')[1]
        print(f"[+] SDK: {sdk_version}")
        with open(name_output_file("sdk"), 'w') as f:
            f.write(sdk_version)
    elif b'\x002.3.0\x00' in appcode and b'\x002.5.2\x00' in appcode:
        # Fix for a single case where there is no sdk line, but we know the version
        sdk_version = '2.3.0'
        print(f"[+] SDK: {sdk_version}")
        with open(name_output_file("sdk"), 'w') as f:
            f.write(sdk_version)

    swv = None
    # If swv from storage load it, otherwise search for it to use for device class searching.
    if exists(name_output_file("swv")):
        with open(name_output_file("swv"), 'r') as f:
            swv = f.read().strip()        

    device_class_search_keys = [
        b'oem_bk7231s_',
        b'bk7231t_common_',
        b'bk7231s_',
        b'oem_bk7231n_',
        b'bk7231n_common_',
        b'_common_ty',
    ]

    device_class = ''

    for searchKey in device_class_search_keys:
        device_class = find_device_class(searchKey)
        if device_class != '':
            break

    if device_class == '':
        device_class = search_device_class_after_compiled_line()
    if device_class == '':
        device_class = search_device_class_after_chipid("bk7231n")
    if device_class == '':
        device_class = search_device_class_after_chipid("BK7231NL")
    if device_class == '':
        device_class = search_device_class_after_chipid("bk7231t")
    if device_class == '':
        device_class = search_device_class_after_chipid("rtl8720cf_ameba")
    if device_class == '' and swv is not None:
        device_class = search_device_class_after_swv(swv)

    if device_class != '':
        print(f"[+] Device class: {device_class}")
        with open(name_output_file("device_class"), 'w') as f:
            f.write(device_class)
        if 'light_ty' in device_class:
            with open(name_output_file("icon"), 'w') as f:
                f.write('lightbulb-outline')
        elif '_plug' in device_class or '_dltj' in device_class:
            with open(name_output_file("icon"), 'w') as f:
                f.write('power-plug')
        elif 'strip' in device_class:
            with open(name_output_file("icon"), 'w') as f:
                f.write('string-lights')
        elif 'switch' in device_class:
            with open(name_output_file("icon"), 'w') as f:
                f.write('toggle-switch-outline')
        else:
            with open(name_output_file("icon"), 'w') as f:
                f.write('memory')
    else:
        print("[!] Unable to determine device class, please open an issue and include the bin file.")

    # If swv doesn't exist from storage loaded above
    if swv is None:
        swv = search_swv_after_compiled_line()
        if swv == '':
            swv = search_swv_after_device_class(device_class)
        if swv == '':
            swv = search_swv_before_device_class(device_class)
        if swv != '':
            print(f"[+] Version: {swv}")
            with open(name_output_file("swv"), 'w') as f:
                f.write(swv)

    # If bv doesn't exist from storage
    if exists(name_output_file("bv")) == False and sdk_line != '':
        for sdk_part in re.split(r'[ _\s]+', sdk_line):
            if sdk_part.startswith('BS:'):
                bv = sdk_part.split(':')[1]
                print(f"[+] bv: {bv}")
                with open(name_output_file("bv"), 'w') as f:
                    f.write(bv)

    # If key doesn't exist from storage
    if exists(name_output_file("firmware_key")) == False:
        key = search_key()
        if key is not None and key != '':
            print(f"[+] firmware_key: {key}")
            with open(name_output_file("firmware_key"), 'w') as f:
                f.write(key)


def run(device_folder: str):
    if not device_folder:
        print('Usage: python parse_app.py <dercypted app file>')
        sys.exit(1)

    global appcode_path, appcode
    appcode_path = device_folder
    with open(appcode_path, 'rb') as fs:
        appcode = fs.read()
        dump()


if __name__ == '__main__':
    run(sys.argv[1])
