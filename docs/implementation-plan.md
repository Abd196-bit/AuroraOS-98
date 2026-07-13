# AuroraOS Implementation Plan

## Phase 0: Raspberry Pi Bring-Up

- create bootable Pi 4 and Pi 5 image
- boot to systemd
- enable DRM/KMS, Mesa, libinput, PipeWire, NetworkManager
- stage supplied pixel UI assets into `/usr/share/aurora/assets`
- start Aurora Login Manager or direct developer session

## Phase 1: Display and Shell

- implement wlroots compositor
- implement Aurora server-side decorations
- implement desktop surface
- implement taskbar
- implement start menu
- implement shell sound events
- enforce integer scaling

## Phase 2: Core Apps

- Aurora Explorer
- Aurora Settings
- Aurora Control Panel
- Aurora Terminal
- Aurora Task Manager
- Aurora Package Center

## Phase 3: Compatibility

- native package install flow
- Flatpak install/update flow
- AppImage registration and removal
- optional installer framework

## Phase 4: Raspberry Pi Tools

- DBus API for hardware daemon
- GPIO Manager
- Camera Tools
- UART Terminal
- SPI/I2C Tools
- CPU/GPU Monitor
- Fan Control

## Phase 5: Installer and Updates

- Aurora Installer
- Aurora Update Manager
- recovery partition policy
- atomic or staged update strategy

## Done Criteria

AuroraOS is not considered real until it boots on Raspberry Pi hardware into Aurora Shell without relying on a hosted desktop environment.
