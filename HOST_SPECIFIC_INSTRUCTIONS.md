# Raspberry Pi

## Generic (Zero 2W, 3, or 4)

Use these instruction if:

- You plan on plugging your pi into a monitor and using a keyboard
- Or, you plan on plugging you pi in with ethernet and using SSH over that ethernet connection

Steps:

1. Use Raspberry Pi Imager to burn "Raspberry Pi OS Lite (32 Bit)" to an SD card
   - A 4GB SD card is required to have enough space for the OS and building the Docker image.
   - If using SSH, enable it (using the installer or making an empty file `ssh` on the boot partition)
2. Access the pi (SSH or keyboard + monitor)
3. Install git `sudo apt update && sudo apt install git`
4. Clone tuya-cloudcutter repo `git clone https://github.com/tuya-cloudcutter/tuya-cloudcutter`
5. Go to cloned tuya-cloudcutter repo `cd tuya-cloudcutter`
6. Install the host requirements (Docker and iw) `sudo ./install-requirements.sh`
   - If Docker was just installed, log out and back in (or reboot) so your user picks up the `docker` group.
7. (Optional as independent step) In the cloudcutter directory, build the docker image `sudo docker build --network=host -t cloudcutter .`
8. Run CloudCutter with `sudo ./tuya-cloudcutter.sh ...` (refer to [usage instructions](./INSTRUCTIONS.md))
   - The WiFi adapter defaults to `wlan0`; pass `-w <adapter>` to use a different one. It is moved fully into the container for the duration of the run, so no NetworkManager configuration is required.

## Pi Zero 2W with SSH over USB

Use these instructions if:

- You would like to SSH to the Pi Zero 2W using USB

Steps:

1. Use Raspberry Pi Imager to burn "Raspberry Pi OS Lite (32 Bit)" to an SD card
   - A 4GB SD card is required to have enough space for the OS and building the Docker image.
   - Set a hostname like `piusb` (something you'll remember)
   - Enable SSH (using the installer or making an empty file `ssh` on the boot partition)
2. Edit `config.txt` and `cmdline.txt` on the boot partition to enable USB SSG (Gadget Mode)
   - Add `dtoverlay=dwc2` to the very end of `config.txt`
   - Add `modules-load=dwc2,g_ether` in `cmdline.txt` after `rootwait` before anything else.
   - Ref: https://learn.adafruit.com/turning-your-raspberry-pi-zero-into-a-usb-gadget/ethernet-gadget
   - Ref: https://desertbot.io/blog/headless-pi-zero-ssh-access-over-usb-windows
3. Power the Pi and connect with Micro USB cable to a computer
   - May need to get the right drivers: https://raspberrypi.stackexchange.com/questions/89400/cannot-ssh-raspberry-pi-zero-w-on-windows-via-usb
4. Connect using ssh to `piusb.local` (or whatever hostname you chose)
5. Share your computers network with the Pi
6. Install git `sudo apt update && sudo apt install git`
7. Clone tuya-cloudcutter repo `git clone https://github.com/tuya-cloudcutter/tuya-cloudcutter`
8. Go to cloned tuya-cloudcutter repo `cd tuya-cloudcutter`
9. Install the host requirements (Docker and iw) `sudo ./install-requirements.sh`
   - If Docker was just installed, log out and back in (or reboot) so your user picks up the `docker` group.
10. (Optional as independent step) In the cloudcutter directory, build the docker image `sudo docker build --network=host -t cloudcutter .`
11. Run CloudCutter with `sudo ./tuya-cloudcutter.sh ...` (refer to [usage instructions](./INSTRUCTIONS.md))
    - The WiFi adapter defaults to `wlan0`; pass `-w <adapter>` to use a different one. It is moved fully into the container for the duration of the run, so no NetworkManager configuration is required.
