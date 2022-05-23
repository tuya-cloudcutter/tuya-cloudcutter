# Tuya Cloudcutter

This repository contains the toolchain to exploit a wireless vulnerability that can jailbreak some of the latest smart devices built with the bk7231 chipset under various brand names by Tuya. The vulnerability as well as the exploitation tooling were identified and created by [Khaled Nassar](https://twitter.com/kmhnassar) and [Tom Clement](https://twitter.com/Tom_Clement) with support from [Jilles Groenendijk](https://twitter.com/jilles_com).

Our tool disconnects Tuya devices from the cloud, allowing them to run completely locally. Additionally, it can be used to flash custom firmware to devices over-the-air.

## ⚠️ WARNING⚠️
**Using cloudcutter means that you will NO LONGER be able to use Tuya's apps and servers. Be absolutely sure that you are never going to use them again!**

Additionally, please be aware that this software is experimental and provided without any guarantees from the authors strictly for peronal and educational use. If you will still use it, then you agree that:

1. You understand what the software is doing
2. You choose to use it at your own risk
3. The authors cannot be held accountable for any damages that arise

## How does it work?
If you're curious about the vulnerability and how the exploit chain works, here's the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) and the [proof of concept script](./proof-of-concept/poc.py).

## Usage
Check out [usage instructions](./INSTRUCTIONS.md) and [some host specific instructions for setups on devices like a Raspberry Pi](./HOST_SPECIFIC_INSTRUCTIONS.md)

## Contribution
We'd be happy to receive your contributions! One way to contribute if you already know your way around some binary exploitation or would like to get your hands into it is by building device profiles to support more exploitable devices. Check out the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) for the information about the vulnerability and exploit chain. Example device profiles can also be found in the `device-profiles` directory.

These are currently done manually, but there are some plans in the future to simplify the building process. Additionally, we'd love to see a device-agnostic exploit chain!

### Device dumps
You can also contribute device dumps by making an issue with a link to your device dump, **but be aware if your device was already onboarded on your WiFi AP**. If you don't want your SSID and/or SSID password to be out there, then it's best to dump a device that was onboarded on a dummy AP that you don't mind leaking the parameters for. Otherwise, you may also configure it on a dummy access point a few times before dumping it. This will greatly lower the chances of accidental leakage to anyone working on the building a profile from your device flash dump, **but it is never zero in this case**. As a rule of thumb, it's better to dump a fresh device which has been configured with a dummy AP, but if you still want to dump one that's in use on your home AP then know that you always run the risk of leaking your SSID and password.
Note that a dump made on a device which has been already activated on Tuya's app using a dummy SSID and password would simplify profile building a lot for contributors, so if possible please try to do so.

Tools to dump flash from devices:
- https://github.com/khalednassar/bk7231tools
- https://github.com/OpenBekenIOT/hid_download_py

Additionally, device profiles require a proper Datapoint ID (DPID) schema for local configuration with stock firmware. These can be pulled directly from flash on a device (config region starts at 0x1EF000 on BK7231 devices) if it has been configured to communicate with Tuya servers at least once, or through other more cumbersome ways (e.g. proxying the traffic of a device as it's being initialized after pulling its authkey + uuid + psk). It'd be very handy if you happen to know a simpler way pull these schemas!

### Testing if a device is exploitable
If you'd like to check if a device is exploitable, one way to lower the chance of having to pry open a device that's not exploitable is testing it out with [this test script](./proof-of-concept/test_device_exploitable.py). **The downside to this test is that it won't tell you if the device is BK7231 based or not, since it seems that RTL87{1,2}0 devices are also exploitable but so far no work has been done to support them.**

## Device support
Check out the initial list of [supported devices](./SUPPORTED.md).

## Previous work
- [Smart Home - Smart Hack (35c3 talk)](https://media.ccc.de/v/35c3-9723-smart_home_-_smart_hack) by Michael Steigerwald from [VRUST](https://www.vtrust.de/).
- [tuya-convert](https://github.com/ct-Open-Source/tuya-convert) - MQTT code for triggering firmware updates inspired by their work.
- [tinytuya](https://github.com/jasonacox/tinytuya) - modified version of the library is used to communicate with devices after exploitation.
