# Graphics Stack

AuroraOS targets Raspberry Pi first, so the graphics stack must be simple, direct, and measurable.

## Pi 4

- KMS/DRM
- vc4/v3d Mesa stack
- Wayland compositor
- libinput
- PipeWire for screen capture and audio/video routing

## Pi 5

- KMS/DRM
- v3d Mesa stack
- Wayland compositor
- libinput
- PipeWire

## Shell Rendering Rules

- Aurora shell chrome is pixel rendered.
- Scale factors are integer only.
- No fractional titlebar geometry.
- No blurred shadows.
- No transparency.
- No rounded clipping.

## Third-Party Apps

Linux apps run through Wayland where possible. XWayland may be added for compatibility, but it is not part of the core identity.
