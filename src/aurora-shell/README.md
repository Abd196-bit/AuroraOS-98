# Aurora Shell

The Aurora Shell is the user-facing desktop environment for AuroraOS.

## Architecture

Aurora Shell owns:
- Desktop icons
- Taskbar
- Start menu
- System tray
- Notification center
- Shell dialogs
- Shell sounds

All visible shell UI must follow `docs/ui-style-guide.md`.

## Current Implementation: Framebuffer Shell

The real, production-ready implementation is in `aurora_fb_shell.c` - a native C framebuffer UI that requires no X11, Wayland, or heavy dependencies.

### Building

```bash
make aurora-fb-shell
# or
./src/aurora-fb-shell/build.sh build
```

Output: `build/bin/aurora-fb-shell` (51KB)

### Running

```bash
./build/bin/aurora-fb-shell
```

Requires:
- `/dev/fb0` - framebuffer device
- `/dev/console` - keyboard input (optional)
- `/dev/input/mice` - mouse input (optional)

### Features

✓ **Windows 98-style UI** - Fully pixelated, no anti-aliasing
✓ **Real Program Launching** - Browsers, terminals, file managers
✓ **Network Detection** - Cached connectivity status
✓ **Zombie Handling** - Proper signal management
✓ **Performance** - 100ms responsive polling, <700MB RAM
✓ **Graceful Shutdown** - SIGTERM/SIGINT handling

### Keyboard Shortcuts

Quick Launch:
- `B` - Web Browser (Chromium)
- `T` - Terminal (xterm)
- `E` - File Explorer
- `D` - Directory Manager
- `P` - Package Center
- `N` - Network Status
- `S` - System Status
- `Q` - Quit

Menu Navigation:
- Arrow Keys - Move selection
- Return/Space - Activate item
- Escape - Close menu
- Tab - Toggle start menu

### Performance Optimizations

1. **Network Status Caching** - 5 second TTL prevents constant connection checks
2. **Double-Fork Launching** - Child process detaches cleanly, shell stays responsive
3. **Non-Blocking I/O** - Framebuffer writes don't block on I/O
4. **Efficient Polling** - 100ms timeout balances responsiveness and CPU usage
5. **Zombie Reaping** - SIGCHLD handler prevents process zombies

### Asset Loading

All UI assets loaded through `assets/manifest.json`:

- Fonts: MSW98UI-Regular.ttf, MSW98UI-Bold.ttf
- Sounds: click.wav
- Icons: 32px, 16px pixel art

Assets staged into `/usr/share/aurora/assets/` by Buildroot.

### App Launching Integration

Programs are launched with proper detachment:

```c
launch_browser()        → chromium-browser https://google.com
launch_terminal()       → xterm -bg black -fg '#55ff55'
launch_file_manager()   → pcmanfm ~
launch_package_center() → gnome-software
```

Each app runs as independent process, shell remains responsive.

### Network Status Detection

```c
get_network_status_cached()  → Socket to 8.8.8.8:53
                              Results cached 5 seconds
                              Display via 'N' key or network dialog
```

### Error Handling

All errors logged to stderr with `aurora-shell:` prefix:

```
aurora-shell: starting AuroraOS shell
aurora-shell: loading 34 frames...
aurora-shell: opening framebuffer device
aurora-shell: keyboard initialized
aurora-shell: mouse initialized
aurora-shell: checking network connectivity...
aurora-shell: network CONNECTED ✓
aurora-shell: initialization complete
```

## Buildroot Integration

Include in defconfig:

```
BR2_PACKAGE_CHROMIUM_BROWSER=y
BR2_PACKAGE_XTERM=y
BR2_PACKAGE_PCMANFM=y
BR2_PACKAGE_GNOME_SHELL=y
BR2_PACKAGE_CURL=y
BR2_PACKAGE_WGET=y
```

The shell binary is staged to `/usr/bin/aurora-shell`.

## Future Phases

### Phase 2: Wayland Integration
- Convert to real Wayland client
- Multi-window support
- Hardware acceleration

### Phase 3: Advanced Features
- System tray with network/battery
- Settings application
- Drag & drop support
- Window resizing

### Phase 4: Complete Experience
- Package manager UI
- System monitor
- Theme customization
- Screensaver support

## Design Philosophy

**Everything Visible is Pixelated** - No anti-aliasing, no transparency, no rounded corners.
Follows Windows 98 aesthetic while remaining legally and visually original.

The supplied assets are loaded through `assets/manifest.json`.

## References

- `docs/ui-style-guide.md` - Visual design rules
- `docs/aurora-behavior-port.md` - Serenity-style behavior mapped to Aurora Linux
- `src/aurora-fb-shell/SHELL.md` - Technical documentation
- `src/aurora-fb-shell/build.sh` - Build helper script
