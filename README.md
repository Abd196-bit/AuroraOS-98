# AuroraOS 98

AuroraOS 98 is an experimental Linux operating-system environment for x86-64 PCs and Raspberry Pi hardware. It combines a classic desktop workflow with current Linux application compatibility: real windows, a Start menu, desktop icons, multiple workspaces, a graphical control center, and standard Linux software underneath.

> **Project status:** active development preview. The x86-64 QEMU image is runnable today. Raspberry Pi images, the production Wayland compositor, persistent installation, and update infrastructure are still under development.

![AuroraOS 98 desktop](docs/screenshots/desktop.png)

## What works in the QEMU preview

- Linux 6.18 kernel and Alpine Linux userspace
- Xorg with the Aurora JWM desktop session
- 1440x900 desktop with large-interface scaling
- Start menu, taskbar, desktop icons, four workspaces, and keyboard launch shortcuts
- supplied Aurora pixel cursor theme built from `assets/cursors/aurora-pointer.png`
- supplied MS W98 UI pixel font across the desktop, controls, and application chrome
- real Firefox ESR with QEMU NAT networking
- real VSCodium, packaged for Alpine/musl
- PCManFM graphical file explorer
- native graphical Aurora Settings, Package Center, Task View, and System Monitor
- Wine launcher for Windows executables
- handlers for `.deb`, AppImage, shell scripts, and Linux executables
- Python 3 and pip
- NetworkManager tools, Wi-Fi controls for real hardware, and QEMU Ethernet networking
- ALSA/QEMU audio plumbing and Aurora interface sounds

## Real Firefox

AuroraOS bundles Firefox ESR with working QEMU NAT networking. This capture shows the browser loading a live external site inside the guest OS.

![Firefox ESR running inside AuroraOS 98](docs/screenshots/firefox.png)

## Real VSCodium

AuroraOS bundles Alpine's native VSCodium package. It is not Lite XL, Lapce, a screenshot, or a fake editor window.

![VSCodium running inside AuroraOS 98](docs/screenshots/vscodium.png)

Press `F8` inside the VM to launch VSCodium. Press `F9` to open Aurora Settings.

## Aurora Settings

Settings is a native graphical application with System, Network & Wi-Fi, Sound, Appearance, Apps, and Workspaces pages.

![Aurora Settings](docs/screenshots/settings.png)

## Run it

### Requirements

- macOS or Linux host
- Python 3
- QEMU x86-64
- `cpio`, `lz4`, `bsdtar`, and `make`
- at least 8 GB of free disk space for a clean build
- at least 6 GB of RAM assigned to the VM

On macOS with Homebrew:

```sh
brew install qemu lz4 libarchive
```

Build the Linux kernel/initramfs prerequisites and the graphical image:

```sh
make linux-qemu
python3 tools/build_firefox_qemu.py --build
```

Run AuroraOS 98:

```sh
make run-firefox-qemu
```

The first clean build downloads roughly 620 MB of Alpine packages. The generated image is written to:

```text
build/firefox-qemu/aurora-firefox-initramfs.cpio.lz4
```

Build products are intentionally excluded from Git because the current image is close to 1 GB.

## Architecture

The runnable preview and the production architecture are intentionally separated.

| Layer | QEMU preview today | Production direction |
| --- | --- | --- |
| Kernel | Linux | Linux |
| Userspace | Alpine initramfs | Persistent Linux root filesystem |
| Display | Xorg framebuffer | Wayland |
| Window manager | JWM | Aurora compositor/window manager |
| Desktop icons | iDesk | Aurora Desktop |
| Settings and system tools | Native Tk applications | Modular Aurora services and frontends |
| Networking | NetworkManager tools/QEMU NAT | NetworkManager with hardware Wi-Fi |
| Audio | ALSA/QEMU audio | PipeWire |
| Packages | Alpine packages in RAM preview | Native packages, Flatpak, and AppImage |

The initramfs preview is useful for developing and testing the complete desktop interaction loop. It is not a substitute for the persistent production root filesystem.

## Repository map

```text
assets/                 Aurora icons, artwork, fonts, and sound metadata
docs/                   Architecture, platform, behavior, and build notes
distro/                 Raspberry Pi and image definitions
packaging/               Default-app and optional-installer policy
rootfs-overlay/          Files overlaid onto production root filesystems
src/                     Aurora compositor, shell, services, and app sources
systemd/                 System and user service definitions
tools/                   QEMU image builders and development utilities
```

## Design direction

AuroraOS is keyboard-and-mouse first. The interface uses square windows, clear title bars, compact controls, visible state, and a desktop workflow instead of mobile-style navigation. The current preview uses a dark high-DPI theme while the design system and original Aurora artwork continue to evolve.

Every feature must improve at least one of usability, performance, compatibility, or developer experience.

## Known limitations

- The QEMU preview runs from RAM; changes are not persistent after shutdown.
- QEMU exposes Ethernet NAT, not the Mac's physical Wi-Fi radio.
- Unity Hub is proprietary and is represented by an official installer flow rather than redistributed in the base image.
- Raspberry Pi 4/5 boot images are not release-ready.
- The full Wayland/systemd/PipeWire production session is architectural work in progress.

## License and assets

Original AuroraOS source code is licensed under
[GPL-3.0-or-later](LICENSE). External applications and third-party material
keep their own licenses and copyright terms. The AuroraOS license does not
relicense fonts, sounds, screenshots, icons, artwork, or reference material
unless an accompanying file explicitly states otherwise. Raw third-party
reference repositories, downloaded package archives, and local icon-source
collections are excluded from this repository.
