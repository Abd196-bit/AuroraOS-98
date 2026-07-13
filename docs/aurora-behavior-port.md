# Aurora Behavior Port

This document is the concrete behavior map from SerenityOS-style classic
desktop patterns to AuroraOS Linux components. It is not a kernel swap.
Everything here is implemented either in the current framebuffer shell
prototype or assigned to an Aurora Linux component.

## Current Linux Prototype

Implemented in `src/aurora-fb-shell/aurora_fb_shell.c`:

- Linux kernel/initramfs boot in QEMU
- framebuffer rendering through `/dev/fb0`
- keyboard input through `/dev/console`
- mouse input through `/dev/input/mice`
- Start menu and submenu navigation
- dialog/window close behavior
- System Properties tab switching
- app launch fallback commands for browser, terminal, file manager, package center
- network status probe with caching
- child process cleanup for launched apps

## Window Behavior

Serenity reference:

- `third_party/serenity/Userland/Services/WindowServer/WindowManager.cpp`
- `third_party/serenity/Userland/Services/WindowServer/WindowFrame.cpp`
- `third_party/serenity/Userland/Services/WindowServer/MenuManager.cpp`

Aurora Linux implementation:

- framebuffer prototype: static generated windows plus hit-tested controls
- Wayland target: `aurora-compositor`

Required Aurora behavior:

- square title bars
- close/minimize/maximize hit targets
- keyboard focus traversal
- modal dialogs above parent windows
- Alt+Tab style switcher
- taskbar activation and restore
- no transparent effects
- integer-scaled shell chrome

## Widget Behavior

Serenity reference:

- `LibGUI/Button.cpp`
- `LibGUI/Menu.cpp`
- `LibGUI/MenuItem.cpp`
- `LibGUI/TabWidget.cpp`
- `LibGUI/Dialog.cpp`
- `LibGUI/FilePicker.cpp`
- `LibGUI/IconView.cpp`

Aurora Linux implementation:

- framebuffer prototype: generated pixel frames plus native hit-testing
- Wayland target: Aurora pixel toolkit

Required Aurora behavior:

- 3D bevel buttons
- pressed/released state
- keyboard activation with Enter/Space
- Escape closes menus/dialogs
- arrow keys move menu selection
- tabs switch with mouse and keyboard shortcuts
- icon view opens the selected object
- all focus states are visible and pixelated

## Shell Behavior

Serenity reference:

- `FileManager/DesktopWidget.cpp`
- `WindowServer/MenuManager.cpp`
- `WindowServer/AppletManager.cpp`

Aurora Linux implementation:

- `aurora-shell`
- `aurora-fb-shell`

Required Aurora behavior:

- desktop icons launch namespace targets
- Start menu opens from taskbar and keyboard
- Programs submenu exposes core apps
- taskbar buttons activate windows
- shutdown dialog is explicit
- shell remains responsive while apps launch

## Explorer Behavior

Serenity reference:

- `Applications/FileManager`
- `LibGUI/FileSystemModel.h`
- `LibGUI/FileIconProvider.h`

Aurora Linux implementation:

- `aurora-explorer`
- Linux filesystem APIs

Required Aurora behavior:

- My Computer root
- home, documents, downloads, desktop
- mounted disks and removable media
- network locations
- installed applications
- Control Panel namespace
- Raspberry Pi hardware tools
- file properties dialogs
- copy/move/delete progress dialogs

## Package Center Behavior

Serenity reference:

- `Ports`
- application organization under `Userland/Applications`

Aurora Linux implementation:

- `aurora-package-center`
- native package backend
- Flatpak backend
- AppImage registration
- optional installer metadata

Required Aurora behavior:

- search
- categories
- installed apps
- updates
- one-click optional installers
- clear licensing/distribution messaging
- never replace Linux package managers with Serenity ports

## Settings And Control Panel Behavior

Serenity reference:

- `Applications/Settings`
- `Applications/*Settings`

Aurora Linux implementation:

- `aurora-settings`
- Control Panel modules backed by Linux services

Required Aurora behavior:

- Settings: task-oriented common controls
- Control Panel: dense advanced controls
- shared backend state
- display, keyboard, mouse, network, sound
- Pi GPIO/camera/UART/SPI/I2C/fan modules
- package/update settings

## Terminal Behavior

Serenity reference:

- `Applications/Terminal`

Aurora Linux implementation:

- `aurora-terminal`

Required Aurora behavior:

- fast launch
- standard shell compatibility
- pixelated chrome
- integer font scaling
- copy/paste keyboard support
- no custom shell language

## Task Manager Behavior

Serenity reference:

- `Applications/SystemMonitor`

Aurora Linux implementation:

- `aurora-task-manager`
- Linux `/proc`
- cgroups
- systemd process metadata

Required Aurora behavior:

- process list
- CPU/RAM graphs
- per-process details
- kill/end-task workflow
- disk/network summaries
- Raspberry Pi CPU/GPU temperature and fan state

## Run And Help Behavior

Serenity reference:

- `Applications/Run`
- `Applications/Help`

Aurora Linux implementation:

- shell Run dialog
- Aurora help viewer

Required Aurora behavior:

- Run opens commands/apps using Linux PATH
- Help opens local Aurora documentation
- both support keyboard-first operation

