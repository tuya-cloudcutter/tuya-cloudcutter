# Raspberry Pi

## Generic (Zero 2W, 3, or 4)

Use these instruction if:

- You plan on plugging your pi into a monitor and using a keyboard
- Or, you plan on plugging you pi in with ethernet and using SSH over that ethernet connection

Steps:

1. Use Raspberry Pi Imager to burn "Raspberry Pi OS Lite (32 Bit)" to an SD card
	- As of this note, 2022-04-04 build of Bullseye
	- A 4GB SD card is required to have enough space for the OS and building the Docker image.
	- If using SSH, enable it (using the installer or making an empty file `ssh` on the boot partition)
2. Access the pi (SSH or keyboard + monitor)
3. Install Network Manager (only reboot once all files are in place)
	- `sudo apt update && sudo apt install network-manager`
	- `sudo nano /etc/dhcpcd.conf` then add line `denyinterfaces wlan0`
	- `sudo nano /etc/NetworkManager/NetworkManager.conf` and make it look exactly like
```
[main]
plugins=ifupdown,keyfile
dhcp=internal

[ifupdown]
managed=true
```
4. Reboot the pi `sudo reboot` then reaccess.
5. Make sure network manager is enabled and running:
	- `sudo systemctl enable NetworkManager.service`
	- `sudo systemctl start NetworkManager.service`
7. Install Docker with `curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh`
8. Install git `sudo apt install git`
9. Clone tuya-cloudcutter repo `git clone https://github.com/tuya-cloudcutter/tuya-cloudcutter`
10. Go to cloned tuya-cloudcutter repo `cd tuya-cloudcutter`
11. (Optional as independent step) In the cloudcutter directory, build the docker image `sudo docker build --network=host -t cloudcutter .`
12. Run cloudcutter with `sudo ./tuya-cloudcutter.sh -r ...` (refer to [usage instructions](./INSTRUCTIONS.md))

## Pi Zero 2W with SSH over USB

Use these instructions if:

- You would like to SSH to the Pi Zero 2W using USB

Steps:

1. Use Raspberry Pi Imager to burn "Raspberry Pi OS Lite (32 Bit)" to an SD card
	- As of this note, 2022-04-04 build of Bullseye
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
6. Install Network Manager (only reboot once all files are in place)
	- `sudo apt update && sudo apt install network-manager`
	- `sudo nano /etc/dhcpcd.conf` then add line `denyinterfaces wlan0`
	- `sudo nano /etc/NetworkManager/NetworkManager.conf` and make it look exactly like
```
[main]
plugins=ifupdown,keyfile
dhcp=internal

[ifupdown]
managed=true

[keyfile]
unmanaged-devices=interface-name:usb*
```
7. Reboot the Pi `sudo reboot` then reconnect over ssh
8. Install Docker with `curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh`
9. Install git `sudo apt install git`
10. Clone tuya-cloudcutter repo `git clone https://github.com/tuya-cloudcutter/tuya-cloudcutter`
11. Go to cloned tuya-cloudcutter repo `cd tuya-cloudcutter`
12. (Optional as independent step) In the cloudcutter directory, build the docker image `sudo docker build --network=host -t cloudcutter .`
13. Run cloudcutter with `sudo ./tuya-cloudcutter.sh -r ...` (refer to [usage instructions](./INSTRUCTIONS.md))
