# Aurora Compositor

Native Wayland compositor and Aurora Window Manager.

Initial technical direction:

- wlroots-based compositor core
- DRM/KMS output path
- libinput input path
- xdg-shell support for Linux application compatibility
- Aurora shell protocol for taskbar, desktop, start menu, and notifications
- integer output scaling only for shell chrome

This is not a theme layer. It owns window placement, focus, decorations, and shell integration.

Aurora uses Wayland, DRM/KMS, and libinput as its native backends.
