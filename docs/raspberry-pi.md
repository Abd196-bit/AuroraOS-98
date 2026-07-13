# Raspberry Pi Integration

AuroraOS supports Raspberry Pi 4 and Raspberry Pi 5 as first-class targets, not as generic low-end PCs.

## Pi Tools

Aurora Pi Tools provides:

- GPIO Manager
- Camera Tools
- UART Terminal
- SPI Tools
- I2C Tools
- CPU/GPU Monitor
- Fan Control

## Architecture

Pi hardware tools should be separate privileged services with unprivileged UI clients.

```text
Aurora Pi Tools UI
DBus API
aurora-pi-hardwared
Linux gpio/i2c/spi/serial/video interfaces
Raspberry Pi hardware
```

## Security

Do not run the whole desktop as root for hardware access.

Use:

- DBus service boundaries
- polkit rules
- hardware groups where appropriate
- explicit permission prompts for risky actions

## Performance

Pi tools must not poll aggressively.

Default monitor cadence:

- CPU/GPU/RAM: 1 second
- temperature: 2 seconds
- fan: 2 seconds
- GPIO state: event-driven where possible
