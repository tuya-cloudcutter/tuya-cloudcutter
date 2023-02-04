"""
mq_pub_15.py
Created by nano on 2018-11-22.
Copyright (c) 2018 VTRUST. All rights reserved.

Modified from tuya-convert for tuya-cloudcutter.
"""
import base64
import binascii
import datetime
import time
from hashlib import md5

import paho.mqtt.client as mqttClient
import paho.mqtt.publish as publish
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad


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


def mqtt_connect(device_id, local_key, broker="127.0.0.1", protocol="2.2"):
    client = mqttClient.Client("CloudCutter")
    client.device_id = device_id
    client.local_key = local_key
    client.protocol = protocol
    client.connect(broker)
    print(f"[{datetime.datetime.now().time()} MQTT] Connected")
    client.on_message = on_message
    # This is a private mqtt server, subscribe to all topics with "#"
    client.subscribe("#")
    client.loop_start()


def on_message(client, userdata, message):
    try:
        if message.payload[:3] == bytes(client.protocol, 'utf-8'):
            clean_payload = iot_dec(message.payload, client.local_key, client.protocol)
        else:
            clean_payload = message.payload.decode()
        print(f"[{datetime.datetime.now().time()} MQTT Received] Topic: {message.topic} - Message: {clean_payload}")
    except:
        print(f"[{datetime.datetime.now().time()} MQTT Recieved] Unable to parse message: {message.payload}")


def trigger_firmware_update(device_id, local_key, protocol="2.2", broker="127.0.0.1"):
    if protocol == "2.1":
        message = '{"data":{"gwId":"%s"},"protocol":15,"s":%d,"t":%d}' % device_id, 1523715, time.time()
    else:
        message = '{"data":{"firmwareType":0},"protocol":15,"t":%d}' % time.time()
    print(f"[{datetime.datetime.now().time()} MQTT Sending] Sending firmware update message {message} using protocol {protocol}")
    payload = iot_enc(message, local_key, protocol)
    publish.single(f"smart/device/in/{device_id}", payload, hostname=broker)
