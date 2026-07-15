# Raspberry Pi Integration

AuroraOS supports Raspberry Pi 4 and Raspberry Pi 5 as first-class targets, not as generic low-end PCs.

## Hardware Test Image

`make pi-test-image` creates an experimental Pi 4/5 `.img.xz` using Alpine's
official Raspberry Pi firmware and kernel with the current Aurora RAM desktop.
It is intended to validate display, USB input, Ethernet/Wi-Fi detection, and the
desktop startup path before the persistent Buildroot image is complete.

Requirements and limitations:

- Raspberry Pi 4 or Pi 5 with at least 4 GB RAM
- microSD card with at least 2 GB capacity
- no persistence across reboot
- Ethernet recommended for the first test
- physical boot verification is still required

Flash the downloaded `.img.xz` directly with Raspberry Pi Imager by choosing
**Use custom**, selecting the archive, and writing it to the microSD card. You
can also use `xz` and `dd` on Linux:

```sh
xz -dc AuroraOS-98-Pi4-Pi5-test-0.1.img.xz | \
  sudo dd of=/dev/sdX bs=4M conv=fsync status=progress
```

Replace `/dev/sdX` with the whole microSD device. Writing to the wrong device
will destroy its contents.

### Generic 5-inch 800x480 HDMI display

Build the dedicated HDMI0 profile with:

```sh
make pi-test-image-800x480
```

This profile disables the firmware splash and firmware-selected display mode,
then forces the current KMS setting `video=HDMI-A-1:800x480M@60D` from
`cmdline.txt`. It also replaces the inherited QEMU Xorg mode list with an
800x480-only mode and enables verbose kernel boot output for hardware diagnosis.
Connect the display to the port labelled HDMI0. Use the standard image for
displays that provide a working EDID.

## Pi Tools

Aurora Pi Tools provides:

- GPIO Manager
- Camera Tools
- UART Terminal
- SPI Tools
- I2C Tools
- CPU/GPU Monitor
- Fan Control

## Architecture

Pi hardware tools should be separate privileged services with unprivileged UI clients.

```text
Aurora Pi Tools UI
DBus API
aurora-pi-hardwared
Linux gpio/i2c/spi/serial/video interfaces
Raspberry Pi hardware
```

## Security

Do not run the whole desktop as root for hardware access.

Use:

- DBus service boundaries
- polkit rules
- hardware groups where appropriate
- explicit permission prompts for risky actions

## Performance

Pi tools must not poll aggressively.

Default monitor cadence:

- CPU/GPU/RAM: 1 second
- temperature: 2 seconds
- fan: 2 seconds
- GPIO state: event-driven where possible
