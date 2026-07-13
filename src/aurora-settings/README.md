# Aurora Settings and Control Panel

Aurora has two configuration surfaces:

- Settings for common task-oriented configuration
- Control Panel for dense advanced modules

Both surfaces share backend services and must not duplicate configuration logic.

## Serenity-Informed Behavior

Reference: SerenityOS `Settings` and `*Settings` applications.

Aurora ports the control organization to Linux services:

- display -> DRM/KMS and compositor settings
- keyboard/mouse -> libinput and keymaps
- network -> NetworkManager
- sound -> PipeWire
- users/session -> systemd and Linux account APIs
- Pi tools -> `aurora-pi-hardwared`
