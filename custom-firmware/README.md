# Custom Firmware
This is the directory you may place custom firmware for flashing. The selectable list will be automatically filtered to binaries that match your chosen profile. If you need newer or more custom firmware, you can add them here, abiding by the naming rules below. Custom firmware must be in the format of either Tuya's `UG` bin file for OTA or the `.uf2` file format.

## Naming rules
If you place custom files here, they must include either `bk7231t` or `bk7231n` in the file name which will allow Tuya-CloudCutter to verify you are flashing a firmware that matches the profile you are using.

## Included 3rd party firmware
For convenience, binaries from the two most prevelant options, [ESPHome (Kickstart version by LibreTiny)](https://github.com/libretiny-eu/esphome-kickstart) and [OpenBeken (OpenBK7231T_App)](https://github.com/openshwprojects/OpenBK7231T_App) have been included automatically. All included binaries will flash your device with a firmware that will put the device into AP mode where you must connect and configure the device as appropriate.

### ESPHome (Kickstart by LibreTiny)
The AP provided by this firmware will start with `kickstart-` followed by the chip family name. You can connect with no password and configure your network information. Once connected you can enter the captive portal at IP address 192.168.4.1 where you will be able join the device to your local network. Once joined to your network, you can scan pin functionality and flash a custom updated firmware (with the .uf2 format) with a more customized configuration.

* See https://www.youtube.com/watch?v=sSj8f-HCHQ0&t=497s for a video guide about configuring Kickstart and generating ESPHome configuration automatically.
* See https://github.com/libretiny-eu/esphome-kickstart for other guides and support.
* See https://github.com/libretiny-eu/esphome-kickstart/releases for the most recent binaries.

### OpenBeken (OpenBK7231T_App)
The AP provided by this firmware will start with `OpenBK` followed by the chip family name and part of the device's MAC address. Once connected you can enter the captive portal at IP address 192.168.4.1 where you will be able to join the device to your local network. Once joined to your network, you can begin configuring your device and use all tools available to OpenBeken.

* See https://www.youtube.com/watch?v=WunlqIMAdgw for a video guide about configuring OpenBeken, and finding pins and drivers automatically.
* See https://github.com/openshwprojects/OpenBK7231T_App for other guides and support.
* See https://github.com/openshwprojects/OpenBK7231T_App/releases for the most recent binaries.
