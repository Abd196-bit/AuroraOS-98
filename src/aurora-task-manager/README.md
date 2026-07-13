# Aurora Task Manager

Aurora Task Manager is the Linux implementation of the classic system monitor
workflow.

Serenity reference:

- `third_party/serenity/Userland/Applications/SystemMonitor`

Linux backends:

- `/proc`
- cgroups
- systemd metadata
- NetworkManager statistics
- Raspberry Pi temperature/fan data from `aurora-pi-hardwared`

Required views:

- Applications
- Processes
- Performance
- Networking
- Startup/session services
- Pi CPU/GPU/fan status

The UI must remain pixelated, square, and keyboard/mouse first.
