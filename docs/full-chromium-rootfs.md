# Full Chromium Rootfs

AuroraOS 98 has two QEMU paths:

- `linux-qemu`: tiny Linux framebuffer shell for fast UI/input progress.
- `full-chromium-image`: full graphical Linux rootfs for real Chromium.

Real Chromium belongs in the full rootfs because it needs Wayland or X11,
fontconfig, shared memory, GPU/software rendering libraries, DBus, NSS, GTK,
and normal Linux userspace services.

The x86-64 QEMU profile is:

```sh
distro/buildroot/x86_64_chromium_defconfig
```

It keeps Linux as the base and includes systemd, Wayland/wlroots, Mesa,
libinput, NetworkManager, PipeWire, Flatpak, and Chromium. The SerenityOS repo
is used only as a behavior and UI reference. It is not the kernel, libc, or app
runtime.

The rootfs overlay adds:

- `/etc/aurora/session.toml`
- `/usr/bin/aurora-open-chromium`
- `/usr/share/applications/aurora-chromium.desktop`
- `aurora-chromium.service`

The launcher resolves `chromium`, `chromium-browser`, or
`chromium-browser-stable` and starts it with the Wayland Ozone backend.

Build and run:

```sh
make rootfs
make chromium-rootfs-check
BUILDROOT_DIR=/path/to/buildroot make full-chromium-image
make run-full-chromium-qemu
```

`make full-chromium-image` is a Linux-host build. On macOS, the target stops
early with a clear error instead of starting an invalid Chromium toolchain
build. The generated disk image can still be run from QEMU once it exists.

The build output is expected under:

```sh
build/full-chromium/images/
```

On machines without a Buildroot checkout, `make chromium-rootfs-check` still
verifies the Aurora profile and tells you what is missing. It does not pretend
the framebuffer initramfs can launch Chromium.
