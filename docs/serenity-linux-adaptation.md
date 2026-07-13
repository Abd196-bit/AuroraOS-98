# SerenityOS To AuroraOS Linux Adaptation

AuroraOS stays Linux-based. SerenityOS is not Linux: it has its own kernel,
system calls, ports tree, services, filesystem assumptions, and GUI stack.
The correct path is not to boot SerenityOS and call it AuroraOS. The correct
path is to use SerenityOS as a reference implementation for a cohesive classic
desktop, then build an Aurora-owned Linux shell and compositor.

## Hard Boundary

Do not import Serenity's kernel, init model, system server contracts, or device
stack into AuroraOS.

Current reference checkout:

- path: `third_party/serenity`
- upstream: `https://github.com/SerenityOS/serenity`
- commit inspected: `34127407`
- license: BSD 2-Clause, copyright SerenityOS developers

AuroraOS keeps:

- Linux kernel
- systemd
- Wayland/DRM/KMS
- PipeWire
- NetworkManager
- Linux package compatibility
- Flatpak and AppImage support

## Candidate Serenity Areas

These areas can inform AuroraOS, subject to license review and technical port
cost:

- classic desktop interaction patterns
- app/menu organization
- file manager behavior
- pixel icon discipline
- widget sizing and spacing discipline
- source organization for small native utilities

Relevant source directories in the checkout:

- `third_party/serenity/Userland/Libraries/LibGUI`
- `third_party/serenity/Userland/Applications`
- `third_party/serenity/Userland/Services/WindowServer`
- `third_party/serenity/Ports`

These areas should not be directly reused for AuroraOS Linux:

- Serenity kernel
- LibC syscall layer
- WindowServer protocol
- LaunchServer/SystemServer assumptions
- Serenity ports build system as the base package model

## Aurora Linux Replacement Map

| Serenity concept | AuroraOS Linux replacement |
| --- | --- |
| Kernel | Linux kernel |
| WindowServer | Aurora compositor on Wayland/wlroots |
| SystemServer | systemd units and Aurora services |
| LibGUI widgets | Aurora pixel toolkit or native shell widgets |
| FileManager | Aurora Explorer using Linux filesystem APIs |
| Software ports | Native packages, Flatpak, AppImage, optional installers |
| Settings applets | Aurora Settings and Control Panel |

## Porting Rule

Every imported idea must satisfy one of AuroraOS' design rules:

- improves usability
- improves performance
- improves compatibility
- improves developer experience

The import must also preserve Aurora identity:

- no Microsoft assets
- no Serenity branding in the product UI
- no rounded modern controls
- no transparency
- pixelated artwork only

## First Implementation Step

The first Linux implementation remains the QEMU framebuffer shell:

- boots a Linux kernel
- renders Aurora pixel desktop frames
- supports keyboard and mouse input
- opens prototype app/control-panel dialogs
- uses the provided fonts and icons

The longer-term implementation target is:

1. keep the framebuffer shell as boot/demo fallback
2. build Aurora compositor on Linux DRM/Wayland
3. implement Aurora widgets with the same pixel rules
4. port only license-compatible Serenity-style behavior where it improves the OS
