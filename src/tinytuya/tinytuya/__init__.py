# TinyTuya Module
# -*- coding: utf-8 -*-
"""
 Python module to interface with Tuya WiFi smart devices

 Author: Jason A. Cox
 For more information see https://github.com/jasonacox/tinytuya

 Local Control Classes
    OutletDevice(dev_id, address, local_key=None, dev_type='default')
    CoverDevice(dev_id, address, local_key=None, dev_type='default')
    BulbDevice(dev_id, address, local_key=None, dev_type='default')
        dev_id (str): Device ID e.g. 01234567891234567890
        address (str): Device Network IP Address e.g. 10.0.1.99
        local_key (str, optional): The encryption key. Defaults to None.
        dev_type (str): Device type for payload options (see below)
    Cloud(apiRegion, apiKey, apiSecret, apiDeviceID, new_sign_algorithm)

 Functions
    json = status()                    # returns json payload
    set_version(version)               # 3.1 [default] or 3.3
    set_socketPersistent(False/True)   # False [default] or True
    set_socketNODELAY(False/True)      # False or True [default]
    set_socketRetryLimit(integer)      # retry count limit [default 5]
    set_socketTimeout(self, s)         # set connection timeout in seconds [default 5]
    set_dpsUsed(dps_to_request)        # add data points (DPS) to request
    add_dps_to_request(index)          # add data point (DPS) index set to None
    set_retry(retry=True)              # retry if response payload is truncated
    set_status(on, switch=1)           # Set status of the device to 'on' or 'off' (bool)
    set_value(index, value)            # Set int value of any index.
    heartbeat()                        # Send heartbeat to device
    updatedps(index=[1])               # Send updatedps command to device
    turn_on(switch=1)                  # Turn on device / switch #
    turn_off(switch=1)                 # Turn off
    set_timer(num_secs)                # Set timer for num_secs
    set_debug(toggle, color)           # Activate verbose debugging output
    set_sendWait(num_secs)             # Time to wait after sending commands before pulling response
    detect_available_dps()             # Return list of DPS available from device
    generate_payload(command, data)    # Generate TuyaMessage payload for command with data
    send(payload)                      # Send payload to device (do not wait for response)
    receive()                          # Receive payload from device

    OutletDevice:
        set_dimmer(percentage):

    CoverDevice:
        open_cover(switch=1):
        close_cover(switch=1):
        stop_cover(switch=1):

    BulbDevice
        set_colour(r, g, b):
        set_hsv(h, s, v):
        set_white(brightness, colourtemp):
        set_white_percentage(brightness=100, colourtemp=0):
        set_brightness(brightness):
        set_brightness_percentage(brightness=100):
        set_colourtemp(colourtemp):
        set_colourtemp_percentage(colourtemp=100):
        set_scene(scene):             # 1=nature, 3=rave, 4=rainbow
        set_mode(mode='white'):       # white, colour, scene, music
        result = brightness():
        result = colourtemp():
        (r, g, b) = colour_rgb():
        (h,s,v) = colour_hsv()
        result = state():
    
    Cloud
        setregion(apiRegion)
        getdevices(verbose=False)
        getstatus(deviceid)
        getfunctions(deviceid)
        getproperties(deviceid)
        getdps(deviceid)
        sendcommand(deviceid, commands)

 Credits
  * TuyaAPI https://github.com/codetheweb/tuyapi by codetheweb and blackrozes
    For protocol reverse engineering
  * PyTuya https://github.com/clach04/python-tuya by clach04
    The origin of this python module (now abandoned)
  * LocalTuya https://github.com/rospogrigio/localtuya-homeassistant by rospogrigio
    Updated pytuya to support devices with Device IDs of 22 characters

"""

# Modules
from __future__ import print_function  # python 2.7 support
import base64
from hashlib import md5
import json
import logging
import socket
import sys
import time
import colorsys
import binascii
import struct
import requests
import hmac
import hashlib
from collections import namedtuple

# Backward compatability for python2
try:
    input = raw_input
except NameError:
    pass

# Required module: pycryptodome
try:
    import Crypto
    from Crypto.Cipher import AES  # PyCrypto
except ImportError:
    Crypto = AES = None
    import pyaes  # https://github.com/ricmoo/pyaes

version_tuple = (1, 3, 2)
version = __version__ = "%d.%d.%d" % version_tuple
__author__ = "jasonacox"

log = logging.getLogger(__name__)
# Uncomment the following to set debug mode or call set_debug()
# logging.basicConfig(level=logging.DEBUG)  

log.debug("%s version %s", __name__, __version__)
log.debug("Python %s on %s", sys.version, sys.platform)
if Crypto is None:
    log.debug("Using pyaes version %r", pyaes.VERSION)
    log.debug("Using pyaes from %r", pyaes.__file__)
else:
    log.debug("Using PyCrypto %r", Crypto.version_info)
    log.debug("Using PyCrypto from %r", Crypto.__file__)

# Tuya Command Types
UDP = 0  # HEAT_BEAT_CMD
AP_CONFIG = 1  # PRODUCT_INFO_CMD
ACTIVE = 2  # WORK_MODE_CMD
BIND = 3  # WIFI_STATE_CMD - wifi working status
RENAME_GW = 4  # WIFI_RESET_CMD - reset wifi
RENAME_DEVICE = 5  # WIFI_MODE_CMD - Choose smartconfig/AP mode
UNBIND = 6  # DATA_QUERT_CMD - issue command
CONTROL = 7  # STATE_UPLOAD_CMD
STATUS = 8  # STATE_QUERY_CMD
HEART_BEAT = 9
DP_QUERY = 10  # UPDATE_START_CMD - get data points
QUERY_WIFI = 11  # UPDATE_TRANS_CMD
TOKEN_BIND = 12  # GET_ONLINE_TIME_CMD - system time (GMT)
CONTROL_NEW = 13  # FACTORY_MODE_CMD
ENABLE_WIFI = 14  # WIFI_TEST_CMD
DP_QUERY_NEW = 16
SCENE_EXECUTE = 17
UPDATEDPS = 18  # Request refresh of DPS
UDP_NEW = 19
AP_CONFIG_NEW = 20
GET_LOCAL_TIME_CMD = 28
WEATHER_OPEN_CMD = 32
WEATHER_DATA_CMD = 33
STATE_UPLOAD_SYN_CMD = 34
STATE_UPLOAD_SYN_RECV_CMD = 35
HEAT_BEAT_STOP = 37
STREAM_TRANS_CMD = 38
GET_WIFI_STATUS_CMD = 43
WIFI_CONNECT_TEST_CMD = 44
GET_MAC_CMD = 45
GET_IR_STATUS_CMD = 46
IR_TX_RX_TEST_CMD = 47
LAN_GW_ACTIVE = 240
LAN_SUB_DEV_REQUEST = 241
LAN_DELETE_SUB_DEV = 242
LAN_REPORT_SUB_DEV = 243
LAN_SCENE = 244
LAN_PUBLISH_CLOUD_CONFIG = 245
LAN_PUBLISH_APP_CONFIG = 246
LAN_EXPORT_APP_CONFIG = 247
LAN_PUBLISH_SCENE_PANEL = 248
LAN_REMOVE_GW = 249
LAN_CHECK_GW_UPDATE = 250
LAN_GW_UPDATE = 251
LAN_SET_GW_CHANNEL = 252

# Protocol Versions and Headers
PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"
PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + 12 * b"\x00"
MESSAGE_HEADER_FMT = ">4I"  # 4*uint32: prefix, seqno, cmd, length
MESSAGE_RECV_HEADER_FMT = ">5I"  # 4*uint32: prefix, seqno, cmd, length, retcode
MESSAGE_END_FMT = ">2I"  # 2*uint32: crc, suffix
PREFIX_VALUE = 0x000055AA
SUFFIX_VALUE = 0x0000AA55
SUFFIX_BIN = b"\x00\x00\xaaU"

# Tuya Packet Format
TuyaMessage = namedtuple("TuyaMessage", "seqno cmd retcode payload crc")

# Python 2 Support
IS_PY2 = sys.version_info[0] == 2

# TinyTuya Error Response Codes
ERR_JSON = 900
ERR_CONNECT = 901
ERR_TIMEOUT = 902
ERR_RANGE = 903
ERR_PAYLOAD = 904
ERR_OFFLINE = 905
ERR_STATE = 906
ERR_FUNCTION = 907
ERR_DEVTYPE = 908
ERR_CLOUDKEY = 909
ERR_CLOUDRESP = 910
ERR_CLOUDTOKEN = 911
ERR_PARAMS = 912
ERR_CLOUD = 913

error_codes = {
    ERR_JSON: "Invalid JSON Response from Device",
    ERR_CONNECT: "Network Error: Unable to Connect",
    ERR_TIMEOUT: "Timeout Waiting for Device",
    ERR_RANGE: "Specified Value Out of Range",
    ERR_PAYLOAD: "Unexpected Payload from Device",
    ERR_OFFLINE: "Network Error: Device Unreachable",
    ERR_STATE: "Device in Unknown State",
    ERR_FUNCTION: "Function Not Supported by Device",
    ERR_DEVTYPE: "Device22 Detected: Retry Command",
    ERR_CLOUDKEY: "Missing Tuya Cloud Key and Secret",
    ERR_CLOUDRESP: "Invalid JSON Response from Cloud",
    ERR_CLOUDTOKEN: "Unable to Get Cloud Token",
    ERR_PARAMS: "Missing Function Parameters",
    ERR_CLOUD: "Error Response from Tuya Cloud",
    None: "Unknown Error",
}

# Cryptography Helpers
class AESCipher(object):
    def __init__(self, key):
        self.bs = 16
        self.key = key

    def encrypt(self, raw, use_base64=True):
        if Crypto:
            raw = self._pad(raw)
            cipher = AES.new(self.key, mode=AES.MODE_ECB)
            crypted_text = cipher.encrypt(raw)
        else:
            _ = self._pad(raw)
            cipher = pyaes.blockfeeder.Encrypter(
                pyaes.AESModeOfOperationECB(self.key)
            )  # no IV, auto pads to 16
            crypted_text = cipher.feed(raw)
            crypted_text += cipher.feed()  # flush final block

        if use_base64:
            return base64.b64encode(crypted_text)
        else:
            return crypted_text

    def decrypt(self, enc, use_base64=True):
        if use_base64:
            enc = base64.b64decode(enc)

        if Crypto:
            cipher = AES.new(self.key, AES.MODE_ECB)
            raw = cipher.decrypt(enc)
            return self._unpad(raw).decode("utf-8")

        else:
            cipher = pyaes.blockfeeder.Decrypter(
                pyaes.AESModeOfOperationECB(self.key)
            )  # no IV, auto pads to 16
            plain_text = cipher.feed(enc)
            plain_text += cipher.feed()  # flush final block
            return plain_text

    def _pad(self, s):
        padnum = self.bs - len(s) % self.bs
        return s + padnum * chr(padnum).encode()

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]


# Misc Helpers
def bin2hex(x, pretty=False):
    if pretty:
        space = " "
    else:
        space = ""
    if IS_PY2:
        result = "".join("%02X%s" % (ord(y), space) for y in x)
    else:
        result = "".join("%02X%s" % (y, space) for y in x)
    return result

def hex2bin(x):
    if IS_PY2:
        return x.decode("hex")
    else:
        return bytes.fromhex(x)

def set_debug(toggle=True, color=True):
    """Enable tinytuya verbose logging"""
    if toggle:
        if color:
            logging.basicConfig(
                format="\x1b[31;1m%(levelname)s:%(message)s\x1b[0m", level=logging.DEBUG
            )
        else:
            logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
        log.setLevel(logging.DEBUG)
        log.debug("TinyTuya [%s]\n" % __version__)
    else:
        log.setLevel(logging.NOTSET)

def pack_message(msg):
    """Pack a TuyaMessage into bytes."""
    # Create full message excluding CRC and suffix
    buffer = (
        struct.pack(
            MESSAGE_HEADER_FMT,
            PREFIX_VALUE,
            msg.seqno,
            msg.cmd,
            len(msg.payload) + struct.calcsize(MESSAGE_END_FMT),
        )
        + msg.payload
    )
    # Calculate CRC, add it together with suffix
    buffer += struct.pack(
        MESSAGE_END_FMT, binascii.crc32(buffer) & 0xFFFFFFFF, SUFFIX_VALUE
    )
    return buffer

def unpack_message(data):
    """Unpack bytes into a TuyaMessage."""
    header_len = struct.calcsize(MESSAGE_RECV_HEADER_FMT)
    end_len = struct.calcsize(MESSAGE_END_FMT)

    _, seqno, cmd, _, retcode = struct.unpack(
        MESSAGE_RECV_HEADER_FMT, data[:header_len]
    )
    payload = data[header_len:-end_len]
    crc, _ = struct.unpack(MESSAGE_END_FMT, data[-end_len:])
    return TuyaMessage(seqno, cmd, retcode, payload, crc)

def has_suffix(payload):
    """Check to see if payload has valid Tuya suffix"""
    if len(payload) < 4:
        return False
    log.debug("buffer %r = %r", payload[-4:], SUFFIX_BIN)
    return payload[-4:] == SUFFIX_BIN

def error_json(number=None, payload=None):
    """Return error details in JSON"""
    try:
        spayload = json.dumps(payload)
        # spayload = payload.replace('\"','').replace('\'','')
    except:
        spayload = '""'

    vals = (error_codes[number], str(number), spayload)
    log.debug("ERROR %s - %s - payload: %s" % vals)

    return json.loads('{ "Error":"%s", "Err":"%s", "Payload":%s }' % vals)


# Tuya Device Dictionary - Commands and Payload Template
# See requests.json payload at http s://github.com/codetheweb/tuyapi
# 'default' devices require the 0a command for the DP_QUERY request
# 'device22' devices require the 0d command for the DP_QUERY request and a list of
#            dps used set to Null in the request payload

payload_dict = {
    # Default Device
    "default": {
        AP_CONFIG: {  # [BETA] Set Control Values on Device
            "hexByte": "01",
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL: {  # Set Control Values on Device
            "hexByte": "07",
            "command": {"devId": "", "uid": "", "t": ""},
        },
        STATUS: {  # Get Status from Device
            "hexByte": "08",
            "command": {"gwId": "", "devId": ""},
        },
        HEART_BEAT: {"hexByte": "09", "command": {"gwId": "", "devId": ""}},
        DP_QUERY: {  # Get Data Points from Device
            "hexByte": "0a",
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL_NEW: {"hexByte": "0d", "command": {"devId": "", "uid": "", "t": ""}},
        DP_QUERY_NEW: {"hexByte": "0f", "command": {"devId": "", "uid": "", "t": ""}},
        UPDATEDPS: {"hexByte": "12", "command": {"dpId": [18, 19, 20]}},
        "prefix": "000055aa00000000000000",
        # Next byte is command "hexByte" + length of remaining payload + command + suffix
        # (unclear if multiple bytes used for length, zero padding implies could be more
        # than one byte)
        "suffix": "000000000000aa55",
    },
    # Special Case Device with 22 character ID - Some of these devices
    # Require the 0d command as the DP_QUERY status request and the list of
    # dps requested payload
    "device22": {
        DP_QUERY: {  # Get Data Points from Device
            "hexByte": "0d",  # Uses CONTROL_NEW command for some reason
            "command": {"devId": "", "uid": "", "t": ""},
        },
        CONTROL: {  # Set Control Values on Device
            "hexByte": "07",
            "command": {"devId": "", "uid": "", "t": ""},
        },
        HEART_BEAT: {"hexByte": "09", "command": {"gwId": "", "devId": ""}},
        UPDATEDPS: {
            "hexByte": "12",
            "command": {"dpId": [18, 19, 20]},
        },
        "prefix": "000055aa00000000000000",
        "suffix": "000000000000aa55",
    },
}


########################################################
#             Local Classes and Functions
########################################################

class XenonDevice(object):
    def __init__(
        self, dev_id, address, local_key="", dev_type="default", connection_timeout=5
    ):
        """
        Represents a Tuya device.

        Args:
            dev_id (str): The device id.
            address (str): The network address.
            local_key (str, optional): The encryption key. Defaults to None.

        Attributes:
            port (int): The port to connect to.
        """

        self.id = dev_id
        self.address = address
        self.local_key = local_key
        self.local_key = local_key.encode("latin1")
        self.connection_timeout = connection_timeout
        self.version = 3.1
        self.retry = True
        self.dev_type = dev_type
        self.disabledetect = False  # if True do not detect device22
        self.port = 6668  # default - do not expect caller to pass in
        self.socket = None
        self.socketPersistent = False
        self.socketNODELAY = True
        self.socketRetryLimit = 5
        self.cipher = AESCipher(self.local_key)
        self.dps_to_request = {}
        self.seqno = 0
        self.sendWait = 0.01
        if address is None or address == "Auto" or address == "0.0.0.0":
            # try to determine IP address automatically
            (addr, ver) = self.find(dev_id)
            if addr is None:
                log.debug("Unable to find device on network (specify IP address)")
                raise Exception("Unable to find device on network (specify IP address)")
            self.address = addr
            if ver == "3.3":
                self.version = 3.3
            time.sleep(0.5)

    def __del__(self):
        # In case we have a lingering socket connection, close it
        if self.socket is not None:
            # self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None

    def __repr__(self):
        # FIXME can do better than this
        return "%r" % ((self.id, self.address),)

    def _get_socket(self, renew):
        if renew and self.socket is not None:
            # self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
        if self.socket is None:
            # Set up Socket
            retries = 0
            while retries < self.socketRetryLimit:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if self.socketNODELAY:
                    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.socket.settimeout(self.connection_timeout)
                try:
                    retries = retries + 1
                    self.socket.connect((self.address, self.port))
                    return True
                except socket.timeout as err:
                    # unable to open socket
                    log.debug(
                        "socket unable to connect - retry %d/%d"
                        % (retries, self.socketRetryLimit)
                    )
                    self.socket.close()
                    time.sleep(0.1)
                except Exception as err:
                    # unable to open socket
                    log.debug(
                        "socket unable to connect - retry %d/%d"
                        % (retries, self.socketRetryLimit)
                    )
                    self.socket.close()
                    time.sleep(5)
            # unable to get connection
            return False
        # existing socket active
        return True

    def _send_receive(self, payload, minresponse=28, getresponse=True):
        """
        Send single buffer `payload` and receive a single buffer.

        Args:
            payload(bytes): Data to send. Set to 'None' to receive only.
            minresponse(int): Minimum response size expected (default=28 bytes)
        """
        success = False
        retries = 0
        dev_type = self.dev_type
        data = None
        while not success:
            # open up socket if device is available
            if not self._get_socket(False):
                # unable to get a socket - device likely offline
                if self.socket is not None:
                    self.socket.close()
                self.socket = None
                return error_json(ERR_OFFLINE)
            # send request to device
            try:
                if payload is not None:
                    self.socket.send(payload)
                    time.sleep(self.sendWait)  # give device time to respond
                if getresponse is True:
                    data = self.socket.recv(1024)
                    # device may send null ack (28 byte) response before a full response
                    if self.retry and len(data) <= minresponse:
                        log.debug("received null payload (%r), fetch new one", data)
                        time.sleep(0.1)
                        data = self.socket.recv(1024)  # try to fetch new payload
                    success = True
                    log.debug("received data=%r", binascii.hexlify(data))
                # legacy/default mode avoids persisting socket across commands
                if not self.socketPersistent:
                    self.socket.close()
                    self.socket = None
                if getresponse is False:
                    return None
            except KeyboardInterrupt as err:
                log.debug("Keyboard Interrupt - Exiting")
                raise
            except socket.timeout as err:
                # a socket timeout occurred
                if payload is None:
                    # Receive only mode - return None
                    return None
                retries = retries + 1
                log.debug(
                    "Timeout or exception in _send_receive() - retry "
                    + str(retries)
                    + "/"
                    + str(self.socketRetryLimit)
                )
                # if we exceed the limit of retries then lets get out of here
                if retries > self.socketRetryLimit:
                    if self.socket is not None:
                        self.socket.close()
                        self.socket = None
                    log.debug(
                        "Exceeded tinytuya retry limit ("
                        + str(self.socketRetryLimit)
                        + ")"
                    )
                    # timeout reached - return error
                    json_payload = error_json(
                        ERR_TIMEOUT, "Check device key or version"
                    )
                    return json_payload
                # retry:  wait a bit, toss old socket and get new one
                time.sleep(0.1)
                self._get_socket(True)
            except Exception as err:
                # likely network or connection error
                retries = retries + 1
                log.debug(
                    "Network connection error - retry "
                    + str(retries)
                    + "/"
                    + str(self.socketRetryLimit)
                )
                # if we exceed the limit of retries then lets get out of here
                if retries > self.socketRetryLimit:
                    if self.socket is not None:
                        self.socket.close()
                        self.socket = None
                    log.debug(
                        "Exceeded tinytuya retry limit ("
                        + str(self.socketRetryLimit)
                        + ")"
                    )
                    log.debug("Unable to connect to device ")
                    # timeout reached - return error
                    json_payload = error_json(ERR_CONNECT)
                    return json_payload
                # retry:  wait a bit, toss old socket and get new one
                time.sleep(0.1)
                self._get_socket(True)
            # except
        # while

        # option - decode Message with hard coded offsets
        # result = self._decode_payload(data[20:-8])

        # Unpack Message into TuyaMessage format
        # and return payload decrypted
        try:
            msg = unpack_message(data)
            # Data available: seqno cmd retcode payload crc
            log.debug("raw unpacked message = %r", msg)
            result = self._decode_payload(msg.payload)
        except:
            log.debug("error unpacking or decoding tuya JSON payload")
            result = error_json(ERR_PAYLOAD)

        # Did we detect a device22 device? Return ERR_DEVTYPE error.
        if dev_type != self.dev_type:
            log.debug(
                "Device22 detected and updated (%s -> %s) - Update payload and try again",
                dev_type,
                self.dev_type,
            )
            result = error_json(ERR_DEVTYPE)

        return result

    def _decode_payload(self, payload):
        log.debug("decode payload=%r", payload)
        cipher = AESCipher(self.local_key)

        if payload.startswith(PROTOCOL_VERSION_BYTES_31):
            # Received an encrypted payload
            # Remove version header
            payload = payload[len(PROTOCOL_VERSION_BYTES_31) :]
            # Decrypt payload
            # Remove 16-bytes of MD5 hexdigest of payload
            payload = cipher.decrypt(payload[16:])
        elif self.version == 3.3:
            # Trim header for non-default device type
            if self.dev_type != "default" or payload.startswith(
                PROTOCOL_VERSION_BYTES_33
            ):
                payload = payload[len(PROTOCOL_33_HEADER) :]
                log.debug("removing 3.3=%r", payload)
            try:
                log.debug("decrypting=%r", payload)
                payload = cipher.decrypt(payload, False)
            except:
                log.debug("incomplete payload=%r", payload)
                return None

            log.debug("decrypted 3.3 payload=%r", payload)
            # Try to detect if device22 found
            log.debug("payload type = %s" % type(payload))
            if not isinstance(payload, str):
                try:
                    payload = payload.decode()
                except:
                    log.debug("payload was not string type and decoding failed")
                    return error_json(ERR_JSON, payload)
            if not self.disabledetect and "data unvalid" in payload:
                self.dev_type = "device22"
                # set at least one DPS
                self.dps_to_request = {"1": None}
                log.debug(
                    "'data unvalid' error detected: switching to dev_type %r",
                    self.dev_type,
                )
                return None
        elif not payload.startswith(b"{"):
            log.debug("Unexpected payload=%r", payload)
            return error_json(ERR_PAYLOAD, payload)

        if not isinstance(payload, str):
            payload = payload.decode()
        log.debug("decoded results=%r", payload)
        try:
            json_payload = json.loads(payload)
        except:
            json_payload = error_json(ERR_JSON, payload)
        return json_payload

    def receive(self):
        """
        Poll device to read any payload in the buffer.  Timeout results in None returned.
        """
        return self._send_receive(None)

    def send(self, payload):
        """
        Send single buffer `payload`.

        Args:
            payload(bytes): Data to send.
        """
        return self._send_receive(payload, 0, False)

    def detect_available_dps(self):
        """Return which datapoints are supported by the device."""
        # device22 devices need a sort of bruteforce querying in order to detect the
        # list of available dps experience shows that the dps available are usually
        # in the ranges [1-25] and [100-110] need to split the bruteforcing in
        # different steps due to request payload limitation (max. length = 255)
        self.dps_cache = {}
        ranges = [(2, 11), (11, 21), (21, 31), (100, 111)]

        for dps_range in ranges:
            # dps 1 must always be sent, otherwise it might fail in case no dps is found
            # in the requested range
            self.dps_to_request = {"1": None}
            self.add_dps_to_request(range(*dps_range))
            try:
                data = self.status()
            except Exception as ex:
                self.exception("Failed to get status: %s", ex)
                raise
            if "dps" in data:
                self.dps_cache.update(data["dps"])

            if self.dev_type == "default":
                return self.dps_cache
        self.debug("Detected dps: %s", self.dps_cache)
        return self.dps_cache

    def add_dps_to_request(self, dp_indicies):
        """Add a datapoint (DP) to be included in requests."""
        if isinstance(dp_indicies, int):
            self.dps_to_request[str(dp_indicies)] = None
        else:
            self.dps_to_request.update({str(index): None for index in dp_indicies})

    def set_bulb_type(self, type):
        self.bulb_type = type

    def set_version(self, version):
        self.version = version

    def set_socketPersistent(self, persist):
        self.socketPersistent = persist

    def set_socketNODELAY(self, nodelay):
        self.socketNODELAY = nodelay

    def set_socketRetryLimit(self, limit):
        self.socketRetryLimit = limit

    def set_socketTimeout(self, s):
        self.connection_timeout = s

    def set_dpsUsed(self, dps_to_request):
        self.dps_to_request = dps_to_request

    def set_retry(self, retry):
        self.retry = retry

    def set_sendWait(self, s):
        self.sendWait = s

    def close(self):
        self.__del__()

    def find(self, did=None):
        """Scans network for Tuya devices with ID = did

        Parameters:
            did = The specific Device ID you are looking for (returns only IP and Version)

        Response:
            (ip, version)
        """
        if did is None:
            return (None, None)
        log.debug("Listening for device %s on the network" % did)
        # Enable UDP listening broadcasting mode on UDP port 6666 - 3.1 Devices
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        client.bind(("", UDPPORT))
        client.settimeout(TIMEOUT)
        # Enable UDP listening broadcasting mode on encrypted UDP port 6667 - 3.3 Devices
        clients = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        clients.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        clients.bind(("", UDPPORTS))
        clients.settimeout(TIMEOUT)

        count = 0
        counts = 0
        maxretry = 30
        ret = (None, None)

        while (count + counts) <= maxretry:
            if count <= counts:  # alternate between 6666 and 6667 ports
                count = count + 1
                try:
                    data, addr = client.recvfrom(4048)
                except:
                    # Timeout
                    continue
            else:
                counts = counts + 1
                try:
                    data, addr = clients.recvfrom(4048)
                except:
                    # Timeout
                    continue
            ip = addr[0]
            gwId = version = ""
            result = data
            try:
                result = data[20:-8]
                try:
                    result = decrypt_udp(result)
                except:
                    result = result.decode()

                result = json.loads(result)
                ip = result["ip"]
                gwId = result["gwId"]
                version = result["version"]
            except:
                result = {"ip": ip}

            # Check to see if we are only looking for one device
            if gwId == did:
                # We found it!
                ret = (ip, version)
                break

        # while
        clients.close()
        client.close()
        log.debug(ret)
        return ret

    def generate_payload(self, command, data=None, gwId=None, devId=None, uid=None):
        """
        Generate the payload to send.

        Args:
            command(str): The type of command.
                This is one of the entries from payload_dict
            data(dict, optional): The data to send.
                This is what will be passed via the 'dps' entry
            gwId(str, optional): Will be used for gwId
            devId(str, optional): Will be used for devId
            uid(str, optional): Will be used for uid
        """
        json_data = payload_dict[self.dev_type][command]["command"]
        command_hb = payload_dict[self.dev_type][command]["hexByte"]

        if "gwId" in json_data:
            if gwId is not None:
                json_data["gwId"] = gwId
            else:
                json_data["gwId"] = self.id
        if "devId" in json_data:
            if devId is not None:
                json_data["devId"] = devId
            else:
                json_data["devId"] = self.id
        if "uid" in json_data:
            if uid is not None:
                json_data["uid"] = uid
            else:
                json_data["uid"] = self.id
        if "t" in json_data:
            json_data["t"] = str(int(time.time()))

        if data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            else:
                json_data["dps"] = data
        if command_hb == "0d":  # CONTROL_NEW
            json_data["dps"] = self.dps_to_request

        # Create byte buffer from hex data
        payload = json.dumps(json_data)
        # if spaces are not removed device does not respond!
        payload = payload.replace(" ", "")
        payload = payload.encode("utf-8")
        log.debug("building payload=%r", payload)

        if self.version == 3.3:
            # expect to connect and then disconnect to set new
            self.cipher = AESCipher(self.local_key)
            payload = self.cipher.encrypt(payload, False)
            self.cipher = None
            if command_hb != "0a" and command_hb != "12":
                # add the 3.3 header
                payload = PROTOCOL_33_HEADER + payload
        elif command == CONTROL:
            # need to encrypt
            self.cipher = AESCipher(self.local_key)
            payload = self.cipher.encrypt(payload)
            preMd5String = (
                b"data="
                + payload
                + b"||lpv="
                + PROTOCOL_VERSION_BYTES_31
                + b"||"
                + self.local_key
            )
            m = md5()
            m.update(preMd5String)
            hexdigest = m.hexdigest()
            # some tuya libraries strip 8: to :24
            payload = (
                PROTOCOL_VERSION_BYTES_31
                + hexdigest[8:][:16].encode("latin1")
                + payload
            )
            self.cipher = None

        # create Tuya message packet
        msg = TuyaMessage(self.seqno, int(command_hb, 16), 0, payload, 0)
        self.seqno += 1  # increase message sequence number
        buffer = pack_message(msg)
        log.debug("payload generated=%r",binascii.hexlify(buffer))
        return buffer

    def generate_payload_raw(self, command, retcode, data, skip_header=True):
        """
        Low level generation of the payload to send.

        Args:
            command(int): The type of command.
            data(dict): The data to send.
            retcode(int): Retcode for the command. Usually 0.
            skip_header(bool): For Protocol 3.3, does not add the protocol header if True
        """
        # Create byte buffer from hex data
        # Make sure to dump it with no spaces after : chars,
        # otherwise device does not respond.
        # This was done incorrectly before by removing all spaces!
        payload = json.dumps(data, separators=(',', ':'))
        payload = payload.encode("utf-8")
        log.debug("building payload=%r", payload)

        if self.version == 3.3:
            # expect to connect and then disconnect to set new
            self.cipher = AESCipher(self.local_key)
            payload = self.cipher.encrypt(payload, False)
            self.cipher = None
            if skip_header:
                # add the 3.3 header
                payload = PROTOCOL_33_HEADER + payload
        elif command == CONTROL:
            # need to encrypt
            self.cipher = AESCipher(self.local_key)
            payload = self.cipher.encrypt(payload)
            preMd5String = (
                b"data="
                + payload
                + b"||lpv="
                + PROTOCOL_VERSION_BYTES_31
                + b"||"
                + self.local_key
            )
            m = md5()
            m.update(preMd5String)
            hexdigest = m.hexdigest()
            # some tuya libraries strip 8: to :24
            payload = (
                PROTOCOL_VERSION_BYTES_31
                + hexdigest[8:][:16].encode("latin1")
                + payload
            )
            self.cipher = None

        # create Tuya message packet
        msg = TuyaMessage(self.seqno, command, retcode, payload, 0)
        self.seqno += 1  # increase message sequence number
        buffer = pack_message(msg)
        log.debug("payload generated=%r",binascii.hexlify(buffer))
        return buffer


class Device(XenonDevice):
    def __init__(self, dev_id, address, local_key="", dev_type="default"):
        super(Device, self).__init__(dev_id, address, local_key, dev_type)

    def status(self):
        """Return device status."""
        log.debug("status() entry (dev_type is %s)", self.dev_type)
        payload = self.generate_payload(DP_QUERY)

        data = self._send_receive(payload)
        log.debug("status() received data=%r", data)
        # Error handling
        if data and "Err" in data:
            if data["Err"] == str(ERR_DEVTYPE):
                # Device22 detected and change - resend with new payload
                log.debug("status() rebuilding payload for device22")
                payload = self.generate_payload(DP_QUERY)
                data = self._send_receive(payload)

        return data

    def set_status(self, on, switch=1):
        """
        Set status of the device to 'on' or 'off'.

        Args:
            on(bool):  True for 'on', False for 'off'.
            switch(int): The switch to set
        """
        # open device, send request, then close connection
        if isinstance(switch, int):
            switch = str(switch)  # index and payload is a string
        payload = self.generate_payload(CONTROL, {switch: on})

        data = self._send_receive(payload)
        log.debug("set_status received data=%r", data)

        return data

    def product(self):
        """
        Request AP_CONFIG Product Info from device. [BETA]

        """
        # open device, send request, then close connection
        payload = self.generate_payload(AP_CONFIG)
        data = self._send_receive(payload, 0)
        log.debug("product received data=%r", data)
        return data

    def heartbeat(self):
        """
        Send a simple HEART_BEAT command to device.

        """
        # open device, send request, then close connection
        payload = self.generate_payload(HEART_BEAT)
        data = self._send_receive(payload, 0)
        log.debug("heartbeat received data=%r", data)
        return data

    def updatedps(self, index=[1]):
        """
        Request device to update index.

        Args:
            index(array): list of dps to update (ex. [4, 5, 6, 18, 19, 20])
        """
        log.debug("updatedps() entry (dev_type is %s)", self.dev_type)
        # open device, send request, then close connection
        payload = self.generate_payload(UPDATEDPS, index)
        data = self._send_receive(payload, 0)
        log.debug("updatedps received data=%r", data)
        return data

    def set_value(self, index, value):
        """
        Set int value of any index.

        Args:
            index(int): index to set
            value(int): new value for the index
        """
        # open device, send request, then close connection
        if isinstance(index, int):
            index = str(index)  # index and payload is a string

        payload = self.generate_payload(CONTROL, {index: value})

        data = self._send_receive(payload)

        return data

    def turn_on(self, switch=1):
        """Turn the device on"""
        self.set_status(True, switch)

    def turn_off(self, switch=1):
        """Turn the device off"""
        self.set_status(False, switch)

    def set_timer(self, num_secs, dps_id=0):
        """
        Set a timer.

        Args:
            num_secs(int): Number of seconds
            dps_id(int): DPS Index for Timer
        """

        # Query status, pick last device id as that is probably the timer
        if dps_id == 0:
            status = self.status()
            if "dps" in status:
                devices = status["dps"]
                devices_numbers = list(devices.keys())
                devices_numbers.sort()
                dps_id = devices_numbers[-1]
            else:
                log.debug("set_timer received error=%r", status)
                return status

        payload = self.generate_payload(CONTROL, {dps_id: num_secs})

        data = self._send_receive(payload)
        log.debug("set_timer received data=%r", data)
        return data


class OutletDevice(Device):
    """
    Represents a Tuya based Smart Plug or Switch.

    Args:
        dev_id (str): The device id.
        address (str): The network address.
        local_key (str, optional): The encryption key. Defaults to None.
    """

    def __init__(self, dev_id, address, local_key="", dev_type="default"):
        super(OutletDevice, self).__init__(dev_id, address, local_key, dev_type)

    def set_dimmer(self, percentage=None, value=None, dps_id=3):
        """Set dimmer value

        Args:
            percentage (int): percentage dim 0-100
            value (int): direct value for switch 0-255
            dps_id (int): DPS index for dimmer value
        """

        if percentage is not None:
            level = int(percentage * 255.0 / 100.0)
        else:
            level = value

        if level == 0:
            self.turn_off()
        elif level is not None:
            if level < 25:
                level = 25
            if level > 255:
                level = 255
            self.turn_on()
            self.set_value(dps_id, level)


class CoverDevice(Device):
    """
    Represents a Tuya based Smart Window Cover.

    Args:
        dev_id (str): The device id.
        address (str): The network address.
        local_key (str, optional): The encryption key. Defaults to None.
    """

    DPS_INDEX_MOVE = "1"
    DPS_INDEX_BL = "101"

    DPS_2_STATE = {
        "1": "movement",
        "101": "backlight",
    }

    def __init__(self, dev_id, address, local_key="", dev_type="default"):
        super(CoverDevice, self).__init__(dev_id, address, local_key, dev_type)

    def open_cover(self, switch=1):
        """Open the cover"""
        self.set_status("on", switch)

    def close_cover(self, switch=1):
        """Close the cover"""
        self.set_status("off", switch)

    def stop_cover(self, switch=1):
        """Stop the motion of the cover"""
        self.set_status("stop", switch)


class BulbDevice(Device):
    """
    Represents a Tuya based Smart Light/Bulb.

    This class supports two types of bulbs with different DPS mappings and functions:
        Type A - Uses DPS index 1-5
        Type B - Uses DPS index 20-27 (no index 1)
        Type C - Same as Type A except that it is using DPS 2 for brightness, which ranges from 0-1000.  These are the Feit branded dimmers found at Costco.

    Init Args:
        dev_id (str): The device id.
        address (str): The network address.
        local_key (str, optional): The encryption key. Defaults to None.

    """

    # Two types of Bulbs - TypeA uses DPS 1-5, TypeB uses DPS 20-24
    DPS_INDEX_ON = {"A": "1", "B": "20", "C": "1"}
    DPS_INDEX_MODE = {"A": "2", "B": "21", "C": "1"}
    DPS_INDEX_BRIGHTNESS = {"A": "3", "B": "22", "C": "2"}
    DPS_INDEX_COLOURTEMP = {"A": "4", "B": "23", "C": None}
    DPS_INDEX_COLOUR = {"A": "5", "B": "24", "C": None}
    DPS_INDEX_SCENE = {"A": "2", "B": "25", "C": None}
    DPS_INDEX_TIMER = {"A": None, "B": "26", "C": None}
    DPS_INDEX_MUSIC = {"A": None, "B": "27", "C": None}
    DPS = "dps"
    DPS_MODE_WHITE = "white"
    DPS_MODE_COLOUR = "colour"
    DPS_MODE_SCENE = "scene"
    DPS_MODE_MUSIC = "music"
    DPS_MODE_SCENE_1 = "scene_1"  # nature
    DPS_MODE_SCENE_2 = "scene_2"
    DPS_MODE_SCENE_3 = "scene_3"  # rave
    DPS_MODE_SCENE_4 = "scene_4"  # rainbow

    DPS_2_STATE = {
        "1": "is_on",
        "2": "mode",
        "3": "brightness",
        "4": "colourtemp",
        "5": "colour",
        "20": "is_on",
        "21": "mode",
        "22": "brightness",
        "23": "colourtemp",
        "24": "colour",
    }

    # Set Default Bulb Types
    bulb_type = "A"
    has_brightness = False
    has_colourtemp = False
    has_colour = False

    def __init__(self, dev_id, address, local_key="", dev_type="default"):
        super(BulbDevice, self).__init__(dev_id, address, local_key, dev_type)

    @staticmethod
    def _rgb_to_hexvalue(r, g, b, bulb="A"):
        """
        Convert an RGB value to the hex representation expected by Tuya Bulb.

        Index (DPS_INDEX_COLOUR) is assumed to be in the format:
            (Type A) Index: 5 in hex format: rrggbb0hhhssvv
            (Type B) Index: 24 in hex format: hhhhssssvvvv

        While r, g and b are just hexadecimal values of the corresponding
        Red, Green and Blue values, the h, s and v values (which are values
        between 0 and 1) are scaled:
            Type A: 360 (h) and 255 (s and v)
            Type B: 360 (h) and 1000 (s and v)

        Args:
            r(int): Value for the colour red as int from 0-255.
            g(int): Value for the colour green as int from 0-255.
            b(int): Value for the colour blue as int from 0-255.
        """
        rgb = [r, g, b]
        hsv = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)

        # Bulb Type A
        if bulb == "A":
            hexvalue = ""
            for value in rgb:
                hsvarray = [int(hsv[0] * 360), int(hsv[1] * 255), int(hsv[2] * 255)]
                temp = str(hex(int(value))).replace("0x", "")
                if len(temp) == 1:
                    temp = "0" + temp
                hexvalue = hexvalue + temp

            hsvarray = [int(hsv[0] * 360), int(hsv[1] * 255), int(hsv[2] * 255)]
            hexvalue_hsv = ""
            for value in hsvarray:
                temp = str(hex(int(value))).replace("0x", "")
                if len(temp) == 1:
                    temp = "0" + temp
                hexvalue_hsv = hexvalue_hsv + temp
            if len(hexvalue_hsv) == 7:
                hexvalue = hexvalue + "0" + hexvalue_hsv
            else:
                hexvalue = hexvalue + "00" + hexvalue_hsv

        # Bulb Type B
        if bulb == "B":
            # h:0-360,s:0-1000,v:0-1000|hsv|
            hexvalue = ""
            hsvarray = [int(hsv[0] * 360), int(hsv[1] * 1000), int(hsv[2] * 1000)]
            for value in hsvarray:
                temp = str(hex(int(value))).replace("0x", "")
                while len(temp) < 4:
                    temp = "0" + temp
                hexvalue = hexvalue + temp

        return hexvalue

    @staticmethod
    def _hexvalue_to_rgb(hexvalue, bulb="A"):
        """
        Converts the hexvalue used by Tuya for colour representation into
        an RGB value.

        Args:
            hexvalue(string): The hex representation generated by BulbDevice._rgb_to_hexvalue()
        """
        if bulb == "A":
            r = int(hexvalue[0:2], 16)
            g = int(hexvalue[2:4], 16)
            b = int(hexvalue[4:6], 16)
        if bulb == "B":
            # hexvalue is in hsv
            h = float(int(hexvalue[0:4], 16) / 360.0)
            s = float(int(hexvalue[4:8], 16) / 1000.0)
            v = float(int(hexvalue[8:12], 16) / 1000.0)
            rgb = colorsys.hsv_to_rgb(h, s, v)
            r = int(rgb[0] * 255)
            g = int(rgb[1] * 255)
            b = int(rgb[2] * 255)

        return (r, g, b)

    @staticmethod
    def _hexvalue_to_hsv(hexvalue, bulb="A"):
        """
        Converts the hexvalue used by Tuya for colour representation into
        an HSV value.

        Args:
            hexvalue(string): The hex representation generated by BulbDevice._rgb_to_hexvalue()
        """
        if bulb == "A":
            h = int(hexvalue[7:10], 16) / 360.0
            s = int(hexvalue[10:12], 16) / 255.0
            v = int(hexvalue[12:14], 16) / 255.0
        if bulb == "B":
            # hexvalue is in hsv
            h = int(hexvalue[0:4], 16) / 360.0
            s = int(hexvalue[4:8], 16) / 1000.0
            v = int(hexvalue[8:12], 16) / 1000.0

        return (h, s, v)

    def set_version(self, version):
        """
        Set the Tuya device version 3.1 or 3.3 for BulbDevice
        Attempt to determine BulbDevice Type: A or B based on:
            Type A has keys 1-5 (default)
            Type B has keys 20-29
            Type C is Feit type bulbs from costco
        """
        self.version = version

        # Try to determine type of BulbDevice Type based on DPS indexes
        status = self.status()
        if status is not None:
            if "dps" in status:
                if "1" not in status["dps"]:
                    self.bulb_type = "B"
                if self.DPS_INDEX_BRIGHTNESS[self.bulb_type] in status["dps"]:
                    self.has_brightness = True
                if self.DPS_INDEX_COLOURTEMP[self.bulb_type] in status["dps"]:
                    self.has_colourtemp = True
                if self.DPS_INDEX_COLOUR[self.bulb_type] in status["dps"]:
                    self.has_colour = True
            else:
                self.bulb_type = "B"
        else:
            # response has no dps
            self.bulb_type = "B"
        log.debug("bulb type set to %s" % self.bulb_type)

    def turn_on(self, switch=0):
        """Turn the device on"""
        if switch == 0:
            switch = self.DPS_INDEX_ON[self.bulb_type]
        self.set_status(True, switch)

    def turn_off(self, switch=0):
        """Turn the device on"""
        if switch == 0:
            switch = self.DPS_INDEX_ON[self.bulb_type]
        self.set_status(False, switch)

    def set_mode(self, mode="white"):
        """
        Set bulb mode

        Args:
            mode(string): white,colour,scene,music

        """
        payload = self.generate_payload(
            CONTROL, {self.DPS_INDEX_MODE[self.bulb_type]: mode}
        )
        data = self._send_receive(payload)
        return data

    def set_scene(self, scene):
        """
        Set to scene mode

        Args:
            scene(int): Value for the scene as int from 1-4.
        """
        if not 1 <= scene <= 4:
            return error_json(
                ERR_RANGE, "set_scene: The value for scene needs to be between 1 and 4."
            )

        if scene == 1:
            s = self.DPS_MODE_SCENE_1
        elif scene == 2:
            s = self.DPS_MODE_SCENE_2
        elif scene == 3:
            s = self.DPS_MODE_SCENE_3
        else:
            s = self.DPS_MODE_SCENE_4

        payload = self.generate_payload(
            CONTROL, {self.DPS_INDEX_MODE[self.bulb_type]: s}
        )
        data = self._send_receive(payload)
        return data

    def set_colour(self, r, g, b):
        """
        Set colour of an rgb bulb.

        Args:
            r(int): Value for the colour Red as int from 0-255.
            g(int): Value for the colour Green as int from 0-255.
            b(int): Value for the colour Blue as int from 0-255.
        """
        if not self.has_colour:
            return error_json(
                ERR_FUNCTION, "set_colour: Device does not support color."
            )
        if not 0 <= r <= 255:
            return error_json(
                ERR_RANGE,
                "set_colour: The value for red needs to be between 0 and 255.",
            )
        if not 0 <= g <= 255:
            return error_json(
                ERR_RANGE,
                "set_colour: The value for green needs to be between 0 and 255.",
            )
        if not 0 <= b <= 255:
            return error_json(
                ERR_RANGE,
                "set_colour: The value for blue needs to be between 0 and 255.",
            )

        hexvalue = BulbDevice._rgb_to_hexvalue(r, g, b, self.bulb_type)

        payload = self.generate_payload(
            CONTROL,
            {
                self.DPS_INDEX_MODE[self.bulb_type]: self.DPS_MODE_COLOUR,
                self.DPS_INDEX_COLOUR[self.bulb_type]: hexvalue,
            },
        )
        data = self._send_receive(payload)
        return data

    def set_hsv(self, h, s, v):
        """
        Set colour of an rgb bulb using h, s, v.

        Args:
            h(float): colour Hue as float from 0-1
            s(float): colour Saturation as float from 0-1
            v(float): colour Value as float from 0-1
        """
        if not self.has_colour:
            return error_json(
                ERR_FUNCTION, "set_colour: Device does not support color."
            )
        if not 0 <= h <= 1.0:
            return error_json(
                ERR_RANGE, "set_colour: The value for Hue needs to be between 0 and 1."
            )
        if not 0 <= s <= 1.0:
            return error_json(
                ERR_RANGE,
                "set_colour: The value for Saturation needs to be between 0 and 1.",
            )
        if not 0 <= v <= 1.0:
            return error_json(
                ERR_RANGE,
                "set_colour: The value for Value needs to be between 0 and 1.",
            )

        (r, g, b) = colorsys.hsv_to_rgb(h, s, v)
        hexvalue = BulbDevice._rgb_to_hexvalue(
            r * 255.0, g * 255.0, b * 255.0, self.bulb_type
        )

        payload = self.generate_payload(
            CONTROL,
            {
                self.DPS_INDEX_MODE[self.bulb_type]: self.DPS_MODE_COLOUR,
                self.DPS_INDEX_COLOUR[self.bulb_type]: hexvalue,
            },
        )
        data = self._send_receive(payload)
        return data

    def set_white_percentage(self, brightness=100, colourtemp=0):
        """
        Set white coloured theme of an rgb bulb.

        Args:
            brightness(int): Value for the brightness in percent (0-100)
            colourtemp(int): Value for the colour temperature in percent (0-100)
        """
        # Brightness
        if not (0 <= brightness <= 100):
            return error_json(
                ERR_RANGE,
                "set_white_percentage: Brightness percentage needs to be between 0 and 100.",
            )

        b = int(25 + (255 - 25) * brightness / 100)

        if self.bulb_type == "B":
            b = int(10 + (1000 - 10) * brightness / 100)

        # Colourtemp
        if not (0 <= colourtemp <= 100):
            return error_json(
                ERR_RANGE,
                "set_white_percentage: Colourtemp percentage needs to be between 0 and 100.",
            )

        c = int(255 * colourtemp / 100)

        if self.bulb_type == "B":
            c = int(1000 * colourtemp / 100)

        data = self.set_white(b, c)
        return data

    def set_white(self, brightness=-1, colourtemp=-1):
        """
        Set white coloured theme of an rgb bulb.

        Args:
            brightness(int): Value for the brightness (A:25-255 or B:10-1000)
            colourtemp(int): Value for the colour temperature (A:0-255, B:0-1000).

            Default: Max Brightness and Min Colourtemp
        """
        # Brightness (default Max)
        if brightness < 0:
            brightness = 255
            if self.bulb_type == "B":
                brightness = 1000
        if self.bulb_type == "A" and not (25 <= brightness <= 255):
            return error_json(
                ERR_RANGE, "set_white: The brightness needs to be between 25 and 255."
            )
        if self.bulb_type == "B" and not (10 <= brightness <= 1000):
            return error_json(
                ERR_RANGE, "set_white: The brightness needs to be between 10 and 1000."
            )

        # Colourtemp (default Min)
        if colourtemp < 0:
            colourtemp = 0
        if self.bulb_type == "A" and not (0 <= colourtemp <= 255):
            return error_json(
                ERR_RANGE,
                "set_white: The colour temperature needs to be between 0 and 255.",
            )
        if self.bulb_type == "B" and not (0 <= colourtemp <= 1000):
            return error_json(
                ERR_RANGE,
                "set_white: The colour temperature needs to be between 0 and 1000.",
            )

        payload = self.generate_payload(
            CONTROL,
            {
                self.DPS_INDEX_MODE[self.bulb_type]: self.DPS_MODE_WHITE,
                self.DPS_INDEX_BRIGHTNESS[self.bulb_type]: brightness,
                self.DPS_INDEX_COLOURTEMP[self.bulb_type]: colourtemp,
            },
        )

        data = self._send_receive(payload)
        return data

    def set_brightness_percentage(self, brightness=100):
        """
        Set the brightness value of an rgb bulb.

        Args:
            brightness(int): Value for the brightness in percent (0-100)
        """
        if not (0 <= brightness <= 100):
            return error_json(
                ERR_RANGE,
                "set_brightness_percentage: Brightness percentage needs to be between 0 and 100.",
            )
        b = int(25 + (255 - 25) * brightness / 100)
        if self.bulb_type == "B":
            b = int(10 + (1000 - 10) * brightness / 100)

        data = self.set_brightness(b)
        return data

    def set_brightness(self, brightness):
        """
        Set the brightness value of an rgb bulb.

        Args:
            brightness(int): Value for the brightness (25-255).
        """
        if self.bulb_type == "A" and not (25 <= brightness <= 255):
            return error_json(
                ERR_RANGE,
                "set_brightness: The brightness needs to be between 25 and 255.",
            )
        if self.bulb_type == "B" and not (10 <= brightness <= 1000):
            return error_json(
                ERR_RANGE,
                "set_brightness: The brightness needs to be between 10 and 1000.",
            )

        # Determine which mode bulb is in and adjust accordingly
        state = self.state()
        data = None

        if "mode" in state:
            if state["mode"] == "white":
                # for white mode use DPS for brightness
                if not self.has_brightness:
                    return error_json(
                        ERR_FUNCTION, "set_colour: Device does not support brightness."
                    )
                payload = self.generate_payload(
                    CONTROL, {self.DPS_INDEX_BRIGHTNESS[self.bulb_type]: brightness}
                )
                data = self._send_receive(payload)

            if state["mode"] == "colour":
                # for colour mode use hsv to increase brightness
                if self.bulb_type == "A":
                    value = brightness / 255.0
                else:
                    value = brightness / 1000.0
                (h, s, v) = self.colour_hsv()
                data = self.set_hsv(h, s, value)

        if data is not None:
            return data
        else:
            return error_json(ERR_STATE, "set_brightness: Unknown bulb state.")

    def set_colourtemp_percentage(self, colourtemp=100):
        """
        Set the colour temperature of an rgb bulb.

        Args:
            colourtemp(int): Value for the colour temperature in percentage (0-100).
        """
        if not (0 <= colourtemp <= 100):
            return error_json(
                ERR_RANGE,
                "set_colourtemp_percentage: Colourtemp percentage needs to be between 0 and 100.",
            )
        c = int(255 * colourtemp / 100)
        if self.bulb_type == "B":
            c = int(1000 * colourtemp / 100)

        data = self.set_colourtemp(c)
        return data

    def set_colourtemp(self, colourtemp):
        """
        Set the colour temperature of an rgb bulb.

        Args:
            colourtemp(int): Value for the colour temperature (0-255).
        """
        if not self.has_colourtemp:
            return error_json(
                ERR_FUNCTION, "set_colourtemp: Device does not support colortemp."
            )
        if self.bulb_type == "A" and not (0 <= colourtemp <= 255):
            return error_json(
                ERR_RANGE,
                "set_colourtemp: The colour temperature needs to be between 0 and 255.",
            )
        if self.bulb_type == "B" and not (0 <= colourtemp <= 1000):
            return error_json(
                ERR_RANGE,
                "set_colourtemp: The colour temperature needs to be between 0 and 1000.",
            )

        payload = self.generate_payload(
            CONTROL, {self.DPS_INDEX_COLOURTEMP[self.bulb_type]: colourtemp}
        )
        data = self._send_receive(payload)
        return data

    def brightness(self):
        """Return brightness value"""
        return self.status()[self.DPS][self.DPS_INDEX_BRIGHTNESS[self.bulb_type]]

    def colourtemp(self):
        """Return colour temperature"""
        return self.status()[self.DPS][self.DPS_INDEX_COLOURTEMP[self.bulb_type]]

    def colour_rgb(self):
        """Return colour as RGB value"""
        hexvalue = self.status()[self.DPS][self.DPS_INDEX_COLOUR[self.bulb_type]]
        return BulbDevice._hexvalue_to_rgb(hexvalue, self.bulb_type)

    def colour_hsv(self):
        """Return colour as HSV value"""
        hexvalue = self.status()[self.DPS][self.DPS_INDEX_COLOUR[self.bulb_type]]
        return BulbDevice._hexvalue_to_hsv(hexvalue, self.bulb_type)

    def state(self):
        """Return state of Bulb"""
        status = self.status()
        state = {}
        if not status:
            return error_json(ERR_JSON, "state: empty response")

        if "Error" in status.keys():
            return error_json(ERR_JSON, status["Error"])

        if self.DPS not in status.keys():
            return error_json(ERR_JSON, "state: no data points")

        for key in status[self.DPS].keys():
            if key in self.DPS_2_STATE:
                state[self.DPS_2_STATE[key]] = status[self.DPS][key]

        return state


# Utility Functions

# SCAN network for Tuya devices
MAXCOUNT = 15  # How many tries before stopping
UDPPORT = 6666  # Tuya 3.1 UDP Port
UDPPORTS = 6667  # Tuya 3.3 encrypted UDP Port
TIMEOUT = 3.0  # Seconds to wait for a broadcast

# UDP packet payload decryption - credit to tuya-convert


def pad(s):
    return s + (16 - len(s) % 16) * chr(16 - len(s) % 16)


def unpad(s):
    return s[: -ord(s[len(s) - 1 :])]


def encrypt(msg, key):
    return AES.new(key, AES.MODE_ECB).encrypt(pad(msg).encode())


def decrypt(msg, key):
    return unpad(AES.new(key, AES.MODE_ECB).decrypt(msg)).decode()


udpkey = md5(b"yGAdlopoPVldABfn").digest()


def decrypt_udp(msg):
    return decrypt(msg, udpkey)


# Return positive number or zero
def floor(x):
    if x > 0:
        return x
    else:
        return 0


def appenddevice(newdevice, devices):
    if newdevice["ip"] in devices:
        return True
    """
    for i in devices:
        if i['ip'] == newdevice['ip']:
                return True
    """
    devices[newdevice["ip"]] = newdevice
    return False


# Scan function shortcut
def scan(maxretry=None, color=True):
    """Scans your network for Tuya devices with output to stdout"""
    d = deviceScan(True, maxretry, color)


# Scan function
def deviceScan(verbose=False, maxretry=None, color=True, poll=True):
    """Scans your network for Tuya devices and returns dictionary of devices discovered
        devices = tinytuya.deviceScan(verbose)

    Parameters:
        verbose = True or False, print formatted output to stdout [Default: False]
        maxretry = The number of loops to wait to pick up UDP from all devices
        color = True or False, print output in color [Default: True]
        poll = True or False, poll dps status for devices if possible

    Response:
        devices = Dictionary of all devices found

    To unpack data, you can do something like this:

        devices = tinytuya.deviceScan()
        for ip in devices:
            id = devices[ip]['gwId']
            key = devices[ip]['productKey']
            vers = devices[ip]['version']
            dps = devices[ip]['dps']

    """
    DEVICEFILE = "devices.json"
    havekeys = False
    tuyadevices = []

    # Lookup Tuya device info by (id) returning (name, key)
    def tuyaLookup(deviceid):
        for i in tuyadevices:
            if i["id"] == deviceid:
                return (i["name"], i["key"])
        return ("", "")

    # Check to see if we have additional Device info
    try:
        # Load defaults
        with open(DEVICEFILE) as f:
            tuyadevices = json.load(f)
            havekeys = True
            log.debug("loaded=%s [%d devices]" % (DEVICEFILE, len(tuyadevices)))
            # If no maxretry value set, base it on number of devices
            if maxretry is None:
                maxretry = len(tuyadevices) + MAXCOUNT
    except:
        # No Device info
        pass

    # If no maxretry value set use default
    if maxretry is None:
        maxretry = MAXCOUNT

    # Enable UDP listening broadcasting mode on UDP port 6666 - 3.1 Devices
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.bind(("", UDPPORT))
    client.settimeout(TIMEOUT)
    # Enable UDP listening broadcasting mode on encrypted UDP port 6667 - 3.3 Devices
    clients = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    clients.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    clients.bind(("", UDPPORTS))
    clients.settimeout(TIMEOUT)

    if verbose:
        if color is False:
            # Disable Terminal Color Formatting
            bold = subbold = normal = dim = alert = alertdim = cyan = red = yellow = ""
        else:
            # Terminal Color Formatting
            bold = "\033[0m\033[97m\033[1m"
            subbold = "\033[0m\033[32m"
            normal = "\033[97m\033[0m"
            dim = "\033[0m\033[97m\033[2m"
            alert = "\033[0m\033[91m\033[1m"
            alertdim = "\033[0m\033[91m\033[2m"
            cyan = "\033[0m\033[36m"
            red = "\033[0m\033[31m"
            yellow = "\033[0m\033[33m"

        print(
            "\n%sTinyTuya %s(Tuya device scanner)%s [%s]\n"
            % (bold, normal, dim, __version__)
        )
        if havekeys:
            print("%s[Loaded devices.json - %d devices]\n" % (dim, len(tuyadevices)))
        print(
            "%sScanning on UDP ports %s and %s for devices (%s retries)...%s\n"
            % (subbold, UDPPORT, UDPPORTS, maxretry, normal)
        )

    # globals
    devices = {}
    count = 0
    counts = 0
    spinnerx = 0
    spinner = "|/-\\|"

    log.debug("listening for UDP 6666 and 6667")
    while (count + counts) <= maxretry:
        note = "invalid"
        if verbose:
            print("%sScanning... %s\r" % (dim, spinner[spinnerx]), end="")
            spinnerx = (spinnerx + 1) % 4
            sys.stdout.flush()
            time.sleep(0.1)

        if count <= counts:  # alternate between 6666 and 6667 ports
            try:
                data, addr = client.recvfrom(4048)
            except KeyboardInterrupt as err:
                log.debug("Keyboard Interrupt - Exiting")
                if verbose:
                    print("\n**User Break**")
                exit()
            except Exception as err:
                # Timeout
                count = count + 1
                continue
        else:
            try:
                data, addr = clients.recvfrom(4048)
            except KeyboardInterrupt as err:
                log.debug("Keyboard Interrupt - Exiting")
                if verbose:
                    print("\n**User Break**")
                exit()
            except Exception as err:
                # Timeout
                counts = counts + 1
                continue
        ip = addr[0]
        gwId = productKey = version = dname = dkey = ""
        result = data
        try:
            result = data[20:-8]
            try:
                result = decrypt_udp(result)
            except:
                result = result.decode()

            result = json.loads(result)
            log.debug("Received valid UDP packet: %r" % result)

            note = "Valid"
            ip = result["ip"]
            gwId = result["gwId"]
            productKey = result["productKey"]
            version = result["version"]
        except:
            if verbose:
                print(alertdim + "*  Unexpected payload=%r\n" + normal, result)
            result = {"ip": ip}
            note = "Unknown"
            log.debug("Invalid UDP Packet: %r" % result)

        # check to see if we have seen this device before and add to devices array
        if appenddevice(result, devices) is False:

            # new device found - back off count if we keep getting new devices
            if version == "3.1":
                count = floor(count - 1)
            else:
                counts = floor(counts - 1)
            if havekeys:
                try:
                    # Try to pull name and key data
                    (dname, dkey) = tuyaLookup(gwId)
                except:
                    pass
            if verbose:
                if dname == "":
                    print(
                        "Unknown v%s%s Device%s   Product ID = %s  [%s payload]:\n    %sAddress = %s,  %sDevice ID = %s, %sLocal Key = %s,  %sVersion = %s"
                        % (
                            normal,
                            version,
                            dim,
                            productKey,
                            note,
                            subbold,
                            ip,
                            cyan,
                            gwId,
                            red,
                            dkey,
                            yellow,
                            version,
                        )
                    )
                else:
                    print(
                        "%s%s%s  Product ID = %s  [%s payload]:\n    %sAddress = %s,  %sDevice ID = %s,  %sLocal Key = %s,  %sVersion = %s"
                        % (
                            normal,
                            dname,
                            dim,
                            productKey,
                            note,
                            subbold,
                            ip,
                            cyan,
                            gwId,
                            red,
                            dkey,
                            yellow,
                            version,
                        )
                    )

            try:
                if poll:
                    time.sleep(0.1)  # give device a break before polling
                    if version == "3.1":
                        # Version 3.1 - no device key requires - poll for status data points
                        d = OutletDevice(gwId, ip, dkey)
                        d.set_version(3.1)
                        dpsdata = d.status()
                        if "dps" not in dpsdata:
                            if verbose:
                                if "Error" in dpsdata:
                                    print(
                                        "%s    Access rejected by %s: %s"
                                        % (alertdim, ip, dpsdata["Error"])
                                    )
                                else:
                                    print(
                                        "%s    Invalid response from %s: %r"
                                        % (alertdim, ip, dpsdata)
                                    )
                            devices[ip]["err"] = "Unable to poll"
                        else:
                            devices[ip]["dps"] = dpsdata
                            if verbose:
                                print(dim + "    Status: %s" % dpsdata["dps"])
                    else:
                        # Version 3.3+ requires device key
                        if dkey != "":
                            d = OutletDevice(gwId, ip, dkey)
                            d.set_version(3.3)
                            dpsdata = d.status()
                            if "dps" not in dpsdata:
                                if verbose:
                                    if "Error" in dpsdata:
                                        print(
                                            "%s    Access rejected by %s: %s"
                                            % (alertdim, ip, dpsdata["Error"])
                                        )
                                    else:
                                        print(
                                            "%s    Check DEVICE KEY - Invalid response from %s: %r"
                                            % (alertdim, ip, dpsdata)
                                        )
                                devices[ip]["err"] = "Unable to poll"
                            else:
                                devices[ip]["dps"] = dpsdata
                                if verbose:
                                    print(dim + "    Status: %s" % dpsdata["dps"])
                        else:
                            if verbose:
                                print(
                                    "%s    No Stats for %s: DEVICE KEY required to poll for status%s"
                                    % (alertdim, ip, dim)
                                )
                    # else
                # if poll
            except:
                if verbose:
                    print(alertdim + "    Unexpected error for %s: Unable to poll" % ip)
                devices[ip]["err"] = "Unable to poll"
            if dname != "":
                devices[ip]["name"] = dname
                devices[ip]["key"] = dkey
        else:
            if version == "3.1":
                count = count + 1
            else:
                counts = counts + 1

    if verbose:
        print(
            "                    \n%sScan Complete!  Found %s devices.\n"
            % (normal, len(devices))
        )
    log.debug("Scan complete with %s devices found" % len(devices))
    clients.close()
    client.close()
    return devices

########################################################
#             Cloud Classes and Functions
########################################################

class Cloud(object):
    def __init__(self, apiRegion=None, apiKey=None, apiSecret=None, apiDeviceID=None, new_sign_algorithm=True):
        """
        Tuya Cloud IoT Platform Access

        Args:
            dev_id (str): The device id.
            address (str): The network address.
            local_key (str, optional): The encryption key. Defaults to None.

        Playload Construction - Header Data:
            Parameter 	  Type    Required	Description
            client_id	  String     Yes	client_id
            signature     String     Yes	HMAC-SHA256 Signature (see below)
            sign_method	  String	 Yes	Message-Digest Algorithm of the signature: HMAC-SHA256.
            t	          Long	     Yes	13-bit standard timestamp (now in milliseconds).
            lang	      String	 No	    Language. It is zh by default in China and en in other areas.
            access_token  String     *      Required for service management calls

        Signature Details:
            * OAuth Token Request: signature = HMAC-SHA256(KEY + t, SECRET).toUpperCase()
            * Service Management: signature = HMAC-SHA256(KEY + access_token + t, SECRET).toUpperCase()

        URIs:
            * Get Token = https://openapi.tuyaus.com/v1.0/token?grant_type=1
            * Get UserID = https://openapi.tuyaus.com/v1.0/devices/{DeviceID}
            * Get Devices = https://openapi.tuyaus.com/v1.0/users/{UserID}/devices

        REFERENCE: 
            * https://images.tuyacn.com/smart/docs/python_iot_code_sample.py
            * https://iot.tuya.com/cloud/products/detail
        """
        # Class Variables
        self.CONFIGFILE = 'tinytuya.json'
        self.apiRegion = apiRegion
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        self.apiDeviceID = apiDeviceID
        self.urlhost = ''
        self.uid = None     # Tuya Cloud User ID
        self.token = None
        self.new_sign_algorithm = new_sign_algorithm

        if apiKey is None or apiSecret is None:
            try:
                # Load defaults from config file if available
                config = {}
                with open(self.CONFIGFILE) as f:
                    config = json.load(f)
                    self.apiRegion = config['apiRegion']
                    self.apiKey = config['apiKey'] 
                    self.apiSecret = config['apiSecret'] 
                    self.apiDeviceID = config['apiDeviceID']
            except:
                return error_json(
                    ERR_CLOUDKEY,
                    "Tuya Cloud Key and Secret required",
                )

        self.setregion(apiRegion)
        # Attempt to connect to cloud and get token
        self.token = self._gettoken()
    
    def setregion(self, apiRegion=None):
        # Set hostname based on apiRegion
        if apiRegion is None:
            apiRegion = self.apiRegion
        self.apiRegion = apiRegion.lower()
        self.urlhost = "openapi.tuyacn.com"          # China Data Center
        if(self.apiRegion == "us"):
            self.urlhost = "openapi.tuyaus.com"      # Western America Data Center
        if(self.apiRegion == "us-e"):
            self.urlhost = "openapi-ueaz.tuyaus.com" # Eastern America Data Center
        if(self.apiRegion == "eu"):
            self.urlhost = "openapi.tuyaeu.com"      # Central Europe Data Center
        if(self.apiRegion == "eu-w"):
            self.urlhost = "openapi-weaz.tuyaeu.com" # Western Europe Data Center
        if(self.apiRegion == "in"):
            self.urlhost = "openapi.tuyain.com"      # India Datacenter

    def _tuyaplatform(self, uri, action='GET', post=None, ver='v1.0', recursive=False):
        """
        Handle GET and POST requests to Tuya Cloud 
        """
        # Build URL and Header
        url = "https://%s/%s/%s" % (self.urlhost, ver, uri)
        headers = {}
        body = {}
        if action == 'POST':
            body = json.dumps(post)
            headers['Content-type'] = 'application/json'
        else:
            action = 'GET'
        now = int(time.time()*1000)
        headers = dict(list(headers.items()) + [('Signature-Headers', ":".join(headers.keys()))]) if headers else {}
        if(self.token==None):
            payload = self.apiKey + str(now)
            headers['secret'] = self.apiSecret
        else:
            payload = self.apiKey + self.token + str(now)
        
        # If running the post 6-30-2021 signing algorithm update the payload to include it's data
        if self.new_sign_algorithm: 
            payload += ('%s\n' % action +                                                # HTTPMethod
                hashlib.sha256(bytes((body or "").encode('utf-8'))).hexdigest() + '\n' + # Content-SHA256
                ''.join(['%s:%s\n'%(key, headers[key])                                   # Headers
                            for key in headers.get("Signature-Headers", "").split(":")
                            if key in headers]) + '\n' +
                '/' + url.split('//', 1)[-1].split('/', 1)[-1])  
        # Sign Payload
        signature = hmac.new(
            self.apiSecret.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest().upper()

        # Create Header Data
        headers['client_id'] = self.apiKey
        headers['sign'] = signature
        headers['t'] = str(now)
        headers['sign_method'] = 'HMAC-SHA256'
        
        if(self.token != None):
            headers['access_token'] = self.token

        # Send Request to Cloud and Get Response
        if action == 'GET':
            response = requests.get(url, headers=headers)
            log.debug(
                "GET: response code=%d text=%s token=%s" % (response.status_code, response.text, self.token)
            )
        else:
            log.debug(
                "POST: URL=%s HEADERS=%s DATA=%s" % (url, headers, body),
            )
            response = requests.post(url, headers=headers, data=body)
        
        # Check to see if token is expired
        if "token invalid" in response.text:
            if recursive is True:
                log.debug("Failed 2nd attempt to renew token - Aborting")
                return None
            log.debug("Token Expired - Try to renew")
            token = self._gettoken()
            if "err" in token:
                log.debug("Failed to renew token")
                return None
            else:
                return self._tuyaplatform(uri, action, post, ver, True)

        try:
            response_dict = json.loads(response.content.decode())
        except:
            try:
                response_dict = json.loads(response.content)
            except:
                return error_json(
                    ERR_CLOUDKEY,
                    "Cloud _tuyaplatform() invalid response: %r" % response.content,
                )
        # Check to see if token is expired
        return(response_dict)

    def _gettoken(self):
        # Get Oauth Token from tuyaPlatform
        self.token = None
        response_dict = self._tuyaplatform('token?grant_type=1')

        if not response_dict['success']:
                return error_json(
                    ERR_CLOUDTOKEN,
                    "Cloud _gettoken() failed: %r" % response_dict['msg'],
                )

        self.token = response_dict['result']['access_token']
        return(self.token)

    def _getuid(self, deviceid=None):
        # Get user ID (UID) for deviceid
        if deviceid is None:
            return error_json(
                ERR_PARAMS,
                "_getuid() requires deviceID parameter"
            )
        uri = 'devices/%s' % deviceid
        response_dict = self._tuyaplatform(uri)

        if not response_dict['success']:
            log.debug(
                    "Error from Tuya Cloud: %r" % response_dict['msg'],
            )
            return None
        uid = response_dict['result']['uid']
        return(uid)
        
    def getdevices(self, verbose=False):
        """
        Return dictionary of all devices. 
        If verbose is true, return full Tuya device 
        details.
        """
        uid = self._getuid(self.apiDeviceID)
        if uid is None:
            return error_json(
                ERR_CLOUD,
                "Unable to get device list"
            )
        # Use UID to get list of all Devices for User
        uri = 'users/%s/devices' % uid
        json_data = self._tuyaplatform(uri)

        if verbose:
            return(json_data)
        else:
            # Filter to only Name, ID and Key
            tuyadevices = []
            for i in json_data['result']:
                item = {}
                item['name'] = i['name'].strip()
                item['id'] = i['id']
                item['key'] = i['local_key']
                tuyadevices.append(item)
            return(tuyadevices)

    def _getdevice(self, param='status', deviceid=None):
        if deviceid is None:
            return error_json(
                ERR_PARAMS,
                "Missing DeviceID Parameter"
            )
        uri = 'iot-03/devices/%s/%s' % (deviceid, param)
        response_dict = self._tuyaplatform(uri)

        if not response_dict['success']:
            log.debug(
                    "Error from Tuya Cloud: %r" % response_dict['msg'],
            )
        return(response_dict)
    
    def getstatus(self, deviceid=None):
        """
        Get the status of the device. 
        """
        return(self._getdevice('status', deviceid))

    def getfunctions(self, deviceid=None):
        """
        Get the functions of the device. 
        """
        return(self._getdevice('functions', deviceid))

    def getproperties(self, deviceid=None):
        """
        Get the properties of the device. 
        """
        return(self._getdevice('specification', deviceid))

    def getdps(self, deviceid=None):
        """
        Get the specifications including DPS IDs of the device. 
        """
        if deviceid is None:
            return error_json(
                ERR_PARAMS,
                "Missing DeviceID Parameter"
            )
        uri = 'devices/%s/specifications' % (deviceid)
        response_dict = self._tuyaplatform(uri, ver='v1.1')

        if not response_dict['success']:
            log.debug(
                    "Error from Tuya Cloud: %r" % response_dict['msg'],
            )
        return(response_dict)

    def sendcommand(self, deviceid=None, commands=None):
        """
        Send a command to the device
        """
        if deviceid is None or commands is None:
            return error_json(
                ERR_PARAMS,
                "Missing DeviceID and Command Parameters"
            )
        uri = 'iot-03/devices/%s/commands' % (deviceid)
        response_dict = self._tuyaplatform(uri,action='POST',post=commands)

        if not response_dict['success']:
            log.debug(
                    "Error from Tuya Cloud: %r" % response_dict['msg'],
            )
        return(response_dict)
