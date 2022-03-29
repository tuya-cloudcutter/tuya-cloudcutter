# Tuya Cloudcutter

This repository contains the toolchain to exploit a wireless vulnerability that can jailbreak some of the latest smart devices built under various brand names by Tuya. The vulnerability as well as the exploitation tooling were identified and created by Khaled Nassar and Tom Clement with support from Jilles Groenendijk.

Our tool disconnects Tuya devices from the cloud, allowing them to run completely locally. Additionally, it can be used to flash custom firmware to devices over-the-air (this part is still being polished and is a WIP, check here later to see if it's added!).

## ⚠️ WARNING⚠️
Please be aware that this software is experimental and provided without any guarantees from the authors strictly for peronal and educational use. If you will still use it, then please be aware that:

1. You understand what the software is doing
2. You choose to use it at your own risk
3. The authors cannot be held accountable for any damages that arise

## How does it work?
If you're curious about the vulnerability and how the exploit chain works, here's the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) and the [proof of concept script](./proof-of-concept/poc.py).

## Usage
Check out [INSTRUCTIONS](./INSTRUCTIONS.md)

## Contribution
We'd be happy to receive your contributions! One way to contribute if you already know your way around some binary exploitation or would like to get your hands into it is by building device profiles to support more exploitable devices. Check out the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) for the information about the vulnerability and exploit chain. Example device profiles can also be found at `src/cloudcutter/device-profiles`.

These are currently done manually, but there are some plans in the future to simplify the building process. Additionally, we'd love to see a device-agnostic exploit chain!

## Device support
Check out the initial list of [supported devices](./SUPPORTED.md).