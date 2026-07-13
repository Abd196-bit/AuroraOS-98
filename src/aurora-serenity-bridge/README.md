# Aurora Serenity Bridge

This directory is the Linux adaptation boundary for any SerenityOS-inspired
work. It is intentionally not a SerenityOS fork.

AuroraOS must remain Linux-based. Code in this area may:

- inspect vendored SerenityOS source under `third_party/serenity`
- document equivalent Aurora Linux services
- prototype Aurora widgets that follow the same classic/pixel discipline
- generate migration notes for Explorer, Settings, Package Center, and shell UX

Code in this area must not:

- depend on SerenityOS kernel APIs
- require Serenity's WindowServer
- replace Linux packaging with Serenity ports
- ship Serenity branding as Aurora branding

The production path is Aurora-owned Linux components:

- `aurora-compositor`
- `aurora-shell`
- `aurora-explorer`
- `aurora-package-center`
- `aurora-settings`
- `aurora-terminal`
- `aurora-pi-hardwared`

