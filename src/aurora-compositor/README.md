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

## Serenity-Informed Behavior

Reference behavior comes from SerenityOS `WindowServer`, but Aurora implements it
on Linux:

- `WindowManager.cpp` -> Aurora focus, stacking, placement
- `WindowFrame.cpp` -> square Aurora title bars and hit testing
- `MenuManager.cpp` -> keyboard/mouse menu routing

Aurora must keep Wayland, DRM/KMS, and libinput as the real backends.
