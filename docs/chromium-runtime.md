# Chromium Runtime

Chromium does not render directly to the Linux framebuffer. The QEMU
framebuffer image is a tiny initramfs shell used to prove boot, input, menus,
and classic UI behavior.

Real Chromium requires a full graphical Linux userspace:

- Linux kernel
- DRM/KMS
- Wayland compositor or X11 server
- fontconfig and fonts
- shared memory
- GPU/software rendering libraries
- Chromium package and runtime dependencies

AuroraOS 98 therefore has two run profiles:

- `linux-qemu`: fast framebuffer shell preview
- `full-chromium-image`: Linux rootfs with Aurora compositor/session and Chromium

Chromium belongs in the full image, not the raw framebuffer initramfs.

See `docs/full-chromium-rootfs.md` for the x86-64 QEMU profile and Buildroot
runner.
