# Aurora Package Center

Package Center is the user-facing software management layer for AuroraOS. It must improve Linux compatibility without hiding important source and trust information.

## Supported Sources

- native packages
- Flatpak
- AppImage
- optional installers

## Main Views

- Search
- Categories
- Updates
- Installed Apps
- Native Packages
- Flatpak Apps
- AppImages
- Optional Installers

## Optional Installers

Some software should not be bundled directly because of licensing, distribution, account, or download requirements.

Optional one-click installers may include:

- Aseprite
- Unity Hub
- Unreal Engine
- Steam
- Discord
- Spotify

Installer pages must clearly show:

- source
- license note
- download size
- install location
- whether a third-party account is required

Unity Hub must be treated as an optional installer: AuroraOS may launch the
official Unity install flow, but should not redistribute Unity Hub inside the
base OS image without explicit redistribution rights from Unity.

## AppImage Management

Aurora should make AppImages feel installed without pretending they are native packages.

Responsibilities:

- register desktop entries
- store icons
- verify executable bit
- place files in a managed app directory
- allow uninstall/removal
- show update limitations when no update metadata exists

## Update Model

Package Center must separate update classes:

- OS updates
- native package updates
- Flatpak updates
- AppImage update hints
- optional installer updates

The user should be able to update everything from one place, but the UI must not lie about where updates come from.
