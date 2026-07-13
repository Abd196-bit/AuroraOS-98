# Aurora Terminal

Aurora Terminal is the default terminal application.

Requirements:

- pixelated UI chrome
- keyboard-first behavior
- fast startup
- standard shell compatibility
- configurable font scale using integer steps

## Serenity-Informed Behavior

Reference: `third_party/serenity/Userland/Applications/Terminal`.

Aurora Terminal keeps the classic fast terminal workflow but uses Linux PTYs and
standard shells. It must not invent a Serenity-specific command environment.
