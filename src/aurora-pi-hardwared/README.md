# aurora-pi-hardwared

Privileged Raspberry Pi hardware service for AuroraOS.

This daemon owns hardware access that the desktop must not perform directly:

- GPIO
- camera
- UART
- SPI
- I2C
- CPU/GPU temperature
- fan control

The UI talks to this daemon over DBus. The daemon enforces permissions through polkit and hardware groups.
