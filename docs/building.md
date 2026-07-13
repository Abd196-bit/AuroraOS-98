# Building AuroraOS

## Developer Build

The native component scaffold can be built with the repository Makefile:

```sh
make native
```

If Meson is available, the same scaffold can also be built with:

```sh
meson setup build-native
meson compile -C build-native
```

This builds:

- `aurora-compositor`
- `aurora-shell`
- `aurora-pi-hardwared`

These are scaffolds, not the finished compositor or shell.

## Icons

Generate project icons:

```sh
make icons
make provided-icons
make system-icons
```

`make provided-icons` extracts the icon artwork visible in the user-provided reference screenshot into `assets/icons/provided/` and stages it into the rootfs overlay during `make rootfs`.

`make system-icons` converts the user-provided `win95-winxp_icons-master/icons/*.ico` pack into PNG sizes used by the Aurora shell prototype.

## Root Filesystem Overlay

Prepare the Aurora rootfs overlay:

```sh
make rootfs
```

This stages:

- MSW98UI fonts
- `click.wav`
- systemd user units
- Pi hardware daemon unit
- package policy files

## Raspberry Pi Images

The repository includes initial Buildroot defconfigs:

- `distro/buildroot/raspberrypi4_defconfig`
- `distro/buildroot/raspberrypi5_defconfig`
- `distro/buildroot/x86_64_chromium_defconfig`

The image path is not complete until Buildroot package recipes for Aurora components are added. The current files define the target architecture, systemd base, Wayland stack, Mesa, PipeWire, NetworkManager, Flatpak, libinput, seatd, and Aurora rootfs overlay.

For the laptop/QEMU full graphical profile with real Chromium:

```sh
make chromium-rootfs-check
BUILDROOT_DIR=/path/to/buildroot make full-chromium-image
make run-full-chromium-qemu
```

This is the profile where Chromium runs. The framebuffer initramfs is only the
fast visible shell/input preview.

## QEMU Progress Preview

Until the full Raspberry Pi image is bootable, use the QEMU progress preview:

```sh
make qemu-progress
make run-qemu-progress
```

This boots a tiny firmware-level status screen over QEMU serial output that shows the current AuroraOS bring-up state. It is intentionally not the final OS shell.

## QEMU GUI Preview

Use this to see the current pixelated Aurora shell direction in QEMU:

```sh
make qemu-gui
make run-qemu-gui
```

The GUI preview is a bootable VGA screen-buffer demo. It is not Linux yet; it exists so the visual direction can be inspected while the Raspberry Pi Linux image path is built out.

For the larger laptop-sized icon preview using the provided icon pack:

```sh
make qemu-icon-gui
make run-qemu-icon-gui
```

This boots a 640x480 VBE graphics preview with desktop icons, Start menu, application icons, and taskbar.

## Linux-Based QEMU Prototype

Build and run the Linux-based Aurora prototype:

```sh
make linux-qemu
make run-linux-qemu
```

This boots an Alpine Linux kernel with a custom Aurora initramfs. It starts Aurora directly from `/init`.

Keyboard controls inside QEMU:

- `1`: redraw desktop
- `2`: hide menu
- `3`: show menu
- `s`: show Linux status
- `q`: power off
