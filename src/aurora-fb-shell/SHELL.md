AuroraOS Shell (Framebuffer)
===========================

The real Aurora shell - a native C framebuffer UI that runs on Linux without X11 or Wayland.

Usage
-----

### Keyboard Shortcuts

Menu Navigation:
  Arrow Keys    - Move menu selection
  Return/Space  - Activate selected item
  Escape        - Close menu/dialog
  Tab           - Toggle start menu

Quick Launches:
  B             - Launch Web Browser (Chromium)
  T             - Launch Terminal (xterm)
  E             - Launch File Explorer
  D             - Launch Directory/File Manager
  P             - Launch Package Center
  N             - Show Network Status
  S             - Show System Status

System:
  G             - Settings
  Q             - Quit

Mouse:
  Click Desktop Icons  - Open applications
  Click Start Menu     - Navigate programs
  Click Dialogs        - Interact with windows

Building
--------

Compile:
  gcc -std=c11 -Wall -Wextra -O2 src/aurora-fb-shell/aurora_fb_shell.c -o aurora-shell

Running
-------

In QEMU:
  make run-linux-qemu

On Real Hardware:
  ./aurora-shell

The shell requires:
  /dev/fb0           - Framebuffer device
  /dev/console       - Console input (optional)
  /dev/input/mice    - Mouse input (optional)

Applications Launched
---------------------

Web Browser:    chromium-browser https://google.com
Terminal:       xterm -bg black -fg '#55ff55'
File Manager:   pcmanfm ~
Package Center: gnome-software

Make sure these are installed in your Buildroot image:
  BR2_PACKAGE_CHROMIUM_BROWSER=y
  BR2_PACKAGE_XTERM=y
  BR2_PACKAGE_PCMANFM=y
  BR2_PACKAGE_GNOME_SHELL=y (or similar)

Performance
-----------

Design goals:
  - <700MB idle RAM (with apps)
  - <10s boot time
  - 60fps desktop interactions
  - Instant responsiveness

Optimizations implemented:
  - Network status caching (5s TTL)
  - Double-fork for clean app launching
  - Responsive 100ms poll timeout
  - Non-blocking socket I/O
  - Efficient framebuffer writes
  - Zombie process reaping

Features
--------

✓ Full Windows 98-style pixelated UI
✓ Interactive start menu with programs
✓ Network connectivity detection
✓ Real program launching (browsers, terminals, file managers)
✓ Multiple dialogs and tabs
✓ Mouse and keyboard support
✓ Graceful shutdown
✓ System status display
✓ Clean error reporting to stderr

Architecture
------------

Main Loop:
  1. Poll for keyboard/mouse input (100ms timeout)
  2. Handle input events (keyboard/mouse clicks)
  3. Repaint framebuffer as needed
  4. Background applications run detached

Program Launching:
  Shell → Fork → Fork (grandchild for app) → Parent exits → App runs detached
  
This ensures shell remains responsive while apps run independently.

Network Detection:
  - Attempts non-blocking socket connection to 8.8.8.8:53
  - Results cached for 5 seconds
  - Status displayed on demand (press 'N')

Debugging
---------

Start with stderr enabled:
  ./aurora-shell 2>&1 | tee shell.log

Messages logged:
  aurora-shell: starting AuroraOS shell
  aurora-shell: loading N frames...
  aurora-shell: opening framebuffer device
  aurora-shell: keyboard initialized
  aurora-shell: mouse initialized
  aurora-shell: checking network connectivity...
  aurora-shell: network CONNECTED
  aurora-shell: initialization complete
  aurora-shell: launching web browser...

Future Enhancements
-------------------

Phase 2:
  - Real Wayland compositor integration
  - Multi-window management
  - Window decorations and resizing
  - Drag & drop support
  - Configuration files

Phase 3:
  - System tray with network/battery/volume
  - Settings application
  - File manager with drag/drop
  - Terminal with proper shell integration

Phase 4:
  - Package manager UI
  - System monitor
  - Screensaver
  - Theme customization

---

AuroraOS 2026 - Pixel-perfect desktop operating system
