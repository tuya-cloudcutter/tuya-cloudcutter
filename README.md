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
Check out [usage instructions](./INSTRUCTIONS.md) for info about **flashing custom firmware** and local **cloud-less usage (detaching)**. There are also [some host specific instructions for setups on devices like a Raspberry Pi](./HOST_SPECIFIC_INSTRUCTIONS.md).

## Contribution
We'd be happy to receive your contributions! One way to contribute if you already know your way around some binary exploitation or would like to get your hands into it is by building device profiles to support more exploitable devices. Check out the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) for the information about the vulnerability and exploit chain.

Additional work on expanding the [Lightleak](https://github.com/tuya-cloudcutter/lightleak) project, which can dump unexploited firmware, could use additional attention, as well as possibly expanding it to flash firmware, similiar to regular cloud-cutter as well.  A port to bash/linux may also be useful.

### Device dumps
You can also contribute device dumps by [making an issue](https://github.com/tuya-cloudcutter/tuya-cloudcutter/issues) with a your device dump attached, **but be aware if your device was already onboarded on your WiFi AP**:
- If you don't want your SSID and/or SSID password to be out there, then it's best to dump a device that was onboarded on a dummy AP that you don't mind leaking the parameters for. Otherwise, you may also configure it on a dummy access point a few times before dumping it. This will greatly lower the chances of accidental leakage to anyone working on the building a profile from your device flash dump, **but it is never zero in this case**. As a rule of thumb, it's better to dump a fresh device which has been configured with a dummy AP, but if you still want to dump one that's in use on your home AP then know that you always run the risk of leaking your SSID and password.
- Another option, when having a device paired to SmartLife/TuyaSmart, is to open the app, click the pencil icon in the top-right corner, choose `Remove Device` and click `Disconnect and wipe data`.

~~Note that a dump made on a device which has been already activated on Tuya's app using any working SSID and password would simplify profile building a lot for contributors, so if possible please try to do so.~~
Flash dumps of devices that have never been joined to Smart Life (or disconnected with a data wipe) are now generally acceptable. In order to not potentially leak personal information, that may be the preferred way.

Tools to dump flash from devices:
- https://github.com/tuya-cloudcutter/bk7231tools
- https://github.com/tuya-cloudcutter/lightleak (wireless dumping, still in development; testing is appreciated)

**Note:** other tools, such as hid_download_py or BkWriter, create incomplete dumps, or have data out-of-order which makes processing more difficult.  Please use bk7231tools instead.

- **Example dump command:** `bk7231tools read_flash -d COM5 device-make-and-model.bin`
- Since bk7231tools v1.0.0, the `-s` and `-c` parameters are not needed (additionally, `-c` is deprecated in favor of `-l/--length <bytes>`). The program now reads the entire flash contents by default.
- A valid dump for a standard 2M BK7231 should be 2,097,152 bytes.  If your dump is any other size, it is probably incomplete!

Additionally, device profiles require a proper Datapoint ID (DPID) schema for local configuration with stock firmware. These can be pulled directly from flash on a device (config region starts at 0x1EF000 on BK7231 devices) if it has been configured to communicate with Tuya servers at least once, or through the profiler-builder scripts with the aid of an active Smart Life account.  Profile builder's pull-schema.py script will walk you through the process.  If you are not comfortable with this, just submit the full 2 MiB bin in an issue and a schema will be pulled and added.

### Testing if a device is exploitable
If you'd like to check if a device is exploitable, one way to lower the chance of having to pry open a device that's not exploitable is testing it out with [this test script](./proof-of-concept/test_device_exploitable.py). **The downside to this test is that it won't tell you if the device is BK7231 based or not, since it seems that RTL87{1,2}0 devices are also exploitable but so far no work has been done to support them.**

## Previous work
- [Smart Home - Smart Hack (35c3 talk)](https://media.ccc.de/v/35c3-9723-smart_home_-_smart_hack) by Michael Steigerwald from [VRUST](https://www.vtrust.de/).
- [tuya-convert](https://github.com/ct-Open-Source/tuya-convert) - MQTT code for triggering firmware updates inspired by their work.
- [tinytuya](https://github.com/jasonacox/tinytuya) - modified version of the library is used to communicate with devices after exploitation.
