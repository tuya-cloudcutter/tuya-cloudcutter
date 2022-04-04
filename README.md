# Tuya Cloudcutter

This repository contains the toolchain to exploit a wireless vulnerability that can jailbreak some of the latest smart devices built under various brand names by Tuya. The vulnerability as well as the exploitation tooling were identified and created by Khaled Nassar and Tom Clement with support from Jilles Groenendijk.

Our tool disconnects Tuya devices from the cloud, allowing them to run completely locally. Additionally, it can be used to flash custom firmware to devices over-the-air.

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
We'd be happy to receive your contributions! One way to contribute if you already know your way around some binary exploitation or would like to get your hands into it is by building device profiles to support more exploitable devices. Check out the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) for the information about the vulnerability and exploit chain. Example device profiles can also be found in the `device-profiles` directory.

Additionally, device profiles require a proper Datapoint ID (DPID) schema for local configuration with stock firmware. These can be pulled directly from flash on a device (config region starts at 0x1EF000 on BK7231 devices) if it has been configured to communicate with Tuya servers at least once, or through other more cumbersome ways (e.g. proxying the traffic of a device as it's being initialized after pulling its authkey + uuid + psk). It'd be very handy if you happen to know a simpler way pull these schemas!

If you'd like to check if a device is exploitable, one way to lower the chance of having to pry open a device that's not exploitable is testing it out with [this test script](./proof-of-concept/test_device_exploitable.py). **The downside to this test is that it won't tell you if the device is BK7231 based or not, since it seems that RTL87{1,2}0 devices are also exploitable but so far no work has been done to support them.**

These are currently done manually, but there are some plans in the future to simplify the building process. Additionally, we'd love to see a device-agnostic exploit chain!

## Device support
Check out the initial list of [supported devices](./SUPPORTED.md).
