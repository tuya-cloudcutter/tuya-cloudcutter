# Tuya Cloudcutter

This repository contains the toolchain to exploit a wireless vulnerability that can jailbreak some of the latest smart devices built with the Beken BK7231 (BK7231T,BK7231N) or Realtek RTL8720CF chipsets under various brand names by Tuya. The vulnerability as well as the exploitation tooling were identified and created by [Khaled Nassar](https://rb9.nl/) and [Tom Clement](https://github.com/tjclement) with support from [Jilles Groenendijk](https://jilles.com/).

Our tool disconnects Tuya devices from the cloud, allowing them to run completely locally. Additionally, it can be used to flash custom firmware to devices over-the-air.

ℹ️ Do you like this tool? Please consider giving it a star on Github so it reaches more people. ✨

## ⚠️ WARNING⚠️

**Using Tuya CloudCutter means that you will NO LONGER be able to use Tuya's apps and servers. Be absolutely sure that you are never going to use them again!**

Additionally, please be aware that this software is experimental and provided without any guarantees from the authors strictly for personal and educational use. If you will still use it, then you agree that:

1. You understand what the software is doing
2. You choose to use it at your own risk
3. The authors cannot be held accountable for any damages that arise

## How does it work?

If you're curious about the vulnerability and how the exploit chain works, here's the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) and the [proof of concept script](./proof-of-concept/poc.py).

## Requirements

- A device with a stand-alone wifi adapter (but not be your primary source of networking, ethernet is preferred for that)
- An account with sudo / elevated privileges - An account capable of making network setting changes.
- NetworkManager / nmcli - This is used to scan for Tuya APs, connect to them, and host a CloudCutter AP to run the exploit.  If you run into issues, make sure your NetworkManager service is started.  You may need to use the `-r` parameter if you continue to have issues.
- Docker / Docker CLI package - This is used to create a controlled python environment to handle and run the exploit
- An active internet connection (Somewhat optional) - This is used to download the packages to build the docker container and to download new device profiles.

## Usage

Check out [usage instructions](./INSTRUCTIONS.md) for info about **flashing custom firmware** and local **cloud-less usage (detaching)**. There are also [some host specific instructions for setups on devices like a Raspberry Pi](./HOST_SPECIFIC_INSTRUCTIONS.md).

## Supported devices

- Unpatched Beken BK7231T (WB3S, WB3L, WB2S, etc)
- Unpatched Beken BK7231N (CB3S, CB3L, CB2S, CBU, etc)
- Unpatched Realtek RTL8710BN (WR1, WR2, WR3, WR3E, etc)
  - Note: SDK 2.0.0 (oldest RTL8710BN devices) does not appear to be vulnerable, see the [Unsupported devices](#unsupported-devices) list below.
  - This platform is also newer, and may require full firmware dumps to support more devices.
  - Devices have 2 profile for every version, but only one will work for each device.  See [the FAQ entry](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/FAQ#why-do-rtl8710bn-devices-have-two-profiles-for-every-version) for more information.
- Unpatched Realtek RTL8720CF (WBR1, WBR2, WBR3, WBRU, etc)
  - Note: This platform is newer, and we may not be able to generate profiles for all devices until more samples have been collected.  Please feel free to submit full dumps to [issues](https://github.com/tuya-cloudcutter/tuya-cloudcutter/issues).  Additionally, even if vulnerable, some devices may not be able to be exploited if required addresses within the exploit chain contain a null byte.
- Devices with [known secret values](running-with-known-secrets.md)

## Unsupported devices

- [Patched Beken BK7231T devices](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/Known-Patched-Firmware#bk7231t)
- [Patched Beken BK7231N devices](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/Known-Patched-Firmware#bk7231n)
- [Non-Vulnerable (SDK 2.0.0) or Patched Realtek RTL8710BN devices](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/Known-Patched-Firmware#rtl8710bn)
- [Patched Realtek RTL8720CF devices](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/Known-Patched-Firmware#rtl8720cf)

## FAQ

Please see the [FAQ](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/FAQ) section of the wiki for the most up-to-date questions and answers.  This will cover many things like how to get your device into pairing mode, how to find more information about your device like the current firmware installed, and is expanding as new questions are asked/answered.  Additionally, you may want to consider searching [issues](https://github.com/tuya-cloudcutter/tuya-cloudcutter/issues?q=is%3Aissue).

## Patched devices

Tuya has patched their SDK as of February 2022.  Any device with a firmware compiled against a patched SDK will not be exploitable, but you can still apply 3rd party firmware via serial.  For a list of known patched firmware/devices, see the [known patched firmware](https://github.com/tuya-cloudcutter/tuya-cloudcutter/wiki/Known-Patched-Firmware) wiki page.

## Contribution

We'd be happy to receive your contributions! One way to contribute if you already know your way around some binary exploitation or would like to get your hands into it is by building device profiles to support more exploitable devices. Check out the [detailed writeup](https://rb9.nl/posts/2022-03-29-light-jailbreaking-exploiting-tuya-iot-devices/) for the information about the vulnerability and exploit chain.

Additional work on expanding the [Lightleak](https://github.com/tuya-cloudcutter/lightleak) project, which can dump unexploited firmware, could use additional attention, as well as possibly expanding it to flash firmware, similiar to regular cloud-cutter as well.  A port to bash/linux may also be useful.

### Device dumps

You can also contribute device dumps by [making an issue](https://github.com/tuya-cloudcutter/tuya-cloudcutter/issues) with a your device dump attached, **but be aware if your device was already onboarded on your WiFi AP**:

- If you don't want your SSID and/or SSID password to be out there, then it's best to dump a device that was onboarded on a dummy AP that you don't mind leaking the parameters for. Otherwise, you may also configure it on a dummy access point a few times before dumping it. This will greatly lower the chances of accidental leakage to anyone working on the building a profile from your device flash dump, **but it is never zero in this case**. As a rule of thumb, it's better to dump a fresh device which has been configured with a dummy AP, but if you still want to dump one that's in use on your home AP then know that you always run the risk of leaking your SSID and password.
- Another option, when having a device paired to SmartLife/TuyaSmart, is to open the app, click the pencil icon in the top-right corner, choose `Remove Device` and click `Disconnect and wipe data`.

Flash dumps of devices that have never been joined to Smart Life (or disconnected with a data wipe) are now generally acceptable. In order to not potentially leak personal information, that may be the preferred way.

Tools to dump flash from devices:

- [ltchiptool](https://docs.libretiny.eu/docs/flashing/tools/ltchiptool/) - universal flashing/dumping GUI tool (Beken, RTL8720CF)
- [BK7231Flasher](https://github.com/openshwprojects/BK7231GUIFlashTool) - GUI tool for firmware backup and flashing OpenBeken (Beken, RTL8720CF)
- [bk7231tools](https://github.com/tuya-cloudcutter/bk7231tools) - original toolset for dumping and analyzing Beken binaries (Beken-only)
- [Lightleak](https://github.com/tuya-cloudcutter/lightleak) - wireless dumping, still in development; testing is appreciated (Beken-only)

**Note:** other tools, such as hid_download_py or BkWriter, create incomplete dumps, or have data out-of-order which makes processing more difficult.  Please use the tools outlined above instead.

- **Example dump command:** `bk7231tools read_flash -d COM5 device-make-and-model.bin`
- Since bk7231tools v1.0.0, the `-s` and `-c` parameters are not needed (additionally, `-c` is deprecated in favor of `-l/--length <bytes>`). The program now reads the entire flash contents by default.
- A valid dump for a standard 2M BK7231 should be 2,097,152 bytes.  If your dump is any other size, it is probably incomplete!

Additionally, device profiles require a proper Datapoint ID (DPID) schema for local configuration with stock firmware. These can be pulled directly from flash on a device (config region starts at 0x1EF000 on BK7231 devices) if it has been configured to communicate with Tuya servers at least once, or through the profiler-builder scripts with the aid of an active Smart Life account.  Profile builder's pull-schema.py script will walk you through the process.  If you are not comfortable with this, just submit the full 2 MiB bin in an issue and a schema will be pulled and added.

### Testing if a device is exploitable

If you'd like to check if a device is exploitable, one way to lower the chance of having to pry open a device that's not exploitable is testing it out with [this test script](./proof-of-concept/test_device_exploitable.py). **The downside to this test is that it won't tell you if the device is BK7231, RTL8720CF, or based on some other chipset.**

## Previous work

- [Smart Home - Smart Hack (35c3 talk)](https://media.ccc.de/v/35c3-9723-smart_home_-_smart_hack) by Michael Steigerwald from [VRUST](https://www.vtrust.de/).
- [tuya-convert](https://github.com/ct-Open-Source/tuya-convert) - MQTT code for triggering firmware updates inspired by their work.
- [tinytuya](https://github.com/jasonacox/tinytuya) - modified version of the library is used to communicate with devices after exploitation.

## Special Thanks

A big thank you to all who have provided meaningful contributions to the success of the Tuya CloudCutter project.  Those include, but are not limited to

- [Khaled Nassar](https://rb9.nl/) - Founder, exploit researcher, original script
- [Tom Clement](https://github.com/tjclement) - Founder, exploit researcher, original script
- [Jilles Groenendijk](https://jilles.com/) - Support for original tooling for dumping firmware
- [Kuba Szczodrzyński](https://github.com/kuba2k2/) - Lightleak, script improvements, additional tooling, LibreTiny/ESPHome implementation, and more.
- [divadiow](https://github.com/divadiow) - Firmware dump collection and device support organization
- [Jeremy Salwen](https://github.com/jeremysalwen/) - Exploit expansion to the RTL8710BN and RTL8720CF platforms.

and many other [contributors](https://github.com/tuya-cloudcutter/tuya-cloudcutter/graphs/contributors) (and [here](https://github.com/tuya-cloudcutter/tuya-cloudcutter.github.io/graphs/contributors)) over the years!
