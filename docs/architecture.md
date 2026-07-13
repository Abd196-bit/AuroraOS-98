# AuroraOS Architecture

AuroraOS is a product layer on top of a Linux base system. The kernel and mature Linux services stay Linux. The experience above that layer is Aurora-owned.

## System Layers

```text
Aurora applications
Aurora Explorer, Package Center, Settings, Terminal, Pi Tools
Aurora Shell: desktop, taskbar, start menu, notification center
Aurora Window Manager and Wayland compositor
Wayland protocols, PipeWire, NetworkManager, systemd user services
Linux kernel, Mesa, DRM/KMS, input, audio, networking, storage
Hardware: Raspberry Pi 4/5 and x86-64 PCs
```

## Component Ownership

### Aurora Compositor

Owns Wayland display output, input routing, window placement, focus, keyboard shortcuts, frame scheduling, and shell protocols.

Architecture direction:

- Wayland-first
- wlroots-based unless a later proof shows a custom compositor stack is justified
- server-side decorations for Aurora-managed windows
- strict rectangular window geometry
- integer-scale output handling
- no animation that risks missed frames on Raspberry Pi hardware

### Aurora Window Manager

Integrated with the compositor, not a separate X11-style window manager.

Responsibilities:

- classic title bars
- minimize, maximize, close
- taskbar window grouping
- Alt+Tab
- keyboard-first focus traversal
- context menus
- modal dialog stacking
- per-window compatibility metadata

### Aurora Shell

Owns the desktop experience:

- desktop icons
- taskbar
- start menu
- system tray
- notification center
- session shutdown dialogs
- shell sound events
- first-run setup handoff

The shell must not become a general application framework. It is the OS surface.

### Aurora Explorer

Explorer is the shell file manager and namespace browser.

It provides:

- files and folders
- mounted disks
- removable media
- network locations
- installed applications
- Raspberry Pi device tools

Explorer should use Linux file APIs directly where possible and add Aurora namespace views only where they improve usability.

### Aurora Package Center

Package Center is a compatibility frontend, not a new package ecosystem.

It coordinates:

- native packages
- Flatpak
- AppImage registration
- updates
- installed apps
- optional installers

### Aurora Settings and Control Panel

Aurora has both:

- Settings: task-oriented pages for common configuration
- Control Panel: dense classic modules for advanced users

Both write to the same backend settings services.

Networking is backed by NetworkManager. Aurora exposes it through Network
Neighborhood, Control Panel, and the `aurora-wifi-connect` Wi-Fi Connection
tool, which maps scan, connect, disconnect, and status actions to `nmcli`.

### Aurora Login Manager and Installer

These must visually match the shell but run with tighter security boundaries.

Login Manager:

- local users
- keyboard layout
- session selection
- shutdown/restart

Installer:

- disk selection
- target platform detection
- base image install
- bootloader setup
- optional default application selection

## Compatibility Policy

AuroraOS should run Linux applications whenever possible. Do not fork mature apps just to make them look classic.

Supported app paths:

- native packages
- Flatpak
- AppImage

Bundled defaults:

- Chromium
- LibreOffice
- GIMP, Krita, Inkscape
- Blender
- VSCodium, Git, GCC, Clang, CMake
- Audacity, LMMS
- VLC, Kdenlive
- Godot

Aurora-owned apps exist where the OS needs integration: Explorer, Package Center, Settings, Control Panel, Task Manager, Terminal, Installer, Updater, and Pi tools.

## Boot Target

The boot path should avoid avoidable daemons.

Target sequence:

1. firmware / bootloader
2. Linux kernel
3. systemd
4. hardware services
5. Aurora Login Manager
6. Aurora Compositor
7. Aurora Shell

The shell must be useful before background indexing, update checks, or optional services finish.
