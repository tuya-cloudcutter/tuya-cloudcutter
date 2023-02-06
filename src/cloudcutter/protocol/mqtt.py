"""
mq_pub_15.py
Created by nano on 2018-11-22.
Copyright (c) 2018 VTRUST. All rights reserved.

Modified from tuya-convert for tuya-cloudcutter.
"""
import base64
import binascii
import datetime
import json
import sys
import time
from hashlib import md5

import paho.mqtt.client as mqttClient
import paho.mqtt.publish as publish
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad

from cloudcutter.protocol import handlers

mqtt_flash_progress_finished = False


def encrypt(msg, key):
    return AES.new(key, AES.MODE_ECB).encrypt(pad(msg.encode(), block_size=16))


def decrypt(msg, key):
    return unpad(AES.new(key, AES.MODE_ECB).decrypt(msg), block_size=16).decode()


def iot_dec(message, local_key, protocol='2.2'):
    if protocol == '2.1':
        message_clear = decrypt(base64.b64decode(message[19:]), local_key.encode())
    else:
        message_clear = decrypt(message[15:], local_key.encode())

    return message_clear


def iot_enc(message, local_key, protocol):
    messge_enc = encrypt(message, local_key.encode())
    if protocol == "2.1":
        messge_enc = base64.b64encode(messge_enc)
        signature = b'data=' + messge_enc + b'||pv=' + \
            protocol.encode() + b'||' + local_key.encode()
        signature = md5(signature).hexdigest()[8:8+16].encode()
        messge_enc = protocol.encode() + signature + messge_enc
    else:
        timestamp = b'%08d' % ((int(time.time()*100) % 100000000))
        messge_enc = timestamp + messge_enc
        crc = binascii.crc32(messge_enc).to_bytes(4, byteorder='big')
        messge_enc = protocol.encode() + crc + messge_enc
    return messge_enc


def mqtt_connect(device_id, local_key, tornadoIoLoop, broker="127.0.0.1", protocol="2.2", graceful_exit_timeout: int = 15, verbose_output: bool = False):
    client = mqttClient.Client("CloudCutter")
    client.device_id = device_id
    client.local_key = local_key
    client.tornadoIoLoop = tornadoIoLoop
    client.protocol = protocol
    client.graceful_exit_timeout = graceful_exit_timeout
    client.verbose_output = verbose_output
    client.connect(broker)
    if verbose_output:
        print(f"[{datetime.datetime.now().time()} MQTT] Connected")
    client.on_message = on_message
    # This is a private mqtt server, subscribe to all topics with "#"
    client.subscribe("#")
    client.loop_start()


def on_message(client, userdata, message):
    progress: int = 0
    try:
        if message.payload[:3] == bytes(client.protocol, 'utf-8'):
            clean_payload = iot_dec(message.payload, client.local_key, client.protocol)
        else:
            clean_payload = message.payload.decode()

        try:
            payload_json = json.loads(clean_payload)
            if payload_json["data"]["progress"]:
                progress = int(payload_json["data"]["progress"])
        except:
            pass

        if client.verbose_output:
            print(f"[{datetime.datetime.now().time()} MQTT Received] Topic: {message.topic} - Message: {clean_payload}")
        elif progress > 0:
            print(f"Firmware update progress: {progress}%")

    except:
        if client.verbose_output:
            print(f"[{datetime.datetime.now().time()} MQTT Recieved] Unable to parse message: {message.payload}")

    # If the progress is greater than or equal to 90%, set completed flag (which will trigger a timeout check to start counting down)
    if progress >= 95:
        global mqtt_flash_progress_finished
        mqtt_flash_progress_finished = True

        if mqtt_flash_progress_finished and handlers.file_send_finished:
            print(f"Firmware file has been sent and MQTT reported a progress of nearly complete.  Waiting {client.graceful_exit_timeout} seconds to ensure flashing completes.")
            time.sleep(client.graceful_exit_timeout)
            print("Flashing should be complete.  It takes about 15 seconds for the device to reboot and verify the flash was valid.")
            print("Please wait about 30 seconds then look for signs of activity from the firmware you supplied (either watch for AP mode or check if it joined your network).")
            print(f"Device MAC address: {handlers.device_mac}")
            client.tornadoIoLoop.stop()
            client.disconnect()
            sys.exit(0)


def trigger_firmware_update(device_id, local_key, protocol="2.2", broker="127.0.0.1", verbose_output: bool = False):
    if protocol == "2.1":
        message = '{"data":{"gwId":"%s"},"protocol":15,"s":%d,"t":%d}' % device_id, 1523715, time.time()
    else:
        message = '{"data":{"firmwareType":0},"protocol":15,"t":%d}' % time.time()
    if verbose_output:
        print(f"[{datetime.datetime.now().time()} MQTT Sending] Sending firmware update message {message} using protocol {protocol}")
    payload = iot_enc(message, local_key, protocol)
    publish.single(f"smart/device/in/{device_id}", payload, hostname=broker)
