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
make system-icons
```

`make system-icons` converts the user-provided `win95-winxp_icons-master/icons/*.ico`
pack into PNG sizes used by the Aurora desktop.

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

The image path is not complete until Buildroot package recipes for Aurora components are added. The current files define the target architecture, systemd base, Wayland stack, Mesa, PipeWire, NetworkManager, Flatpak, libinput, seatd, and Aurora rootfs overlay.

For the fast Apple Silicon QEMU desktop:

```sh
make firefox-qemu-arm64
make run-fast-qemu
```

For x86-64 hosts and compatibility testing:

```sh
make firefox-qemu
make run-firefox-qemu
```

Both profiles boot Linux with the graphical Aurora desktop, Firefox, VSCodium,
Explorer, Settings, archive handling, and package tools.
