# Aurora Explorer

Aurora Explorer is the native file manager and shell namespace browser.

Required views:

- home
- desktop
- documents
- downloads
- mounted disks
- removable media
- network locations
- installed applications
- Raspberry Pi hardware tools

Explorer should use mature Linux filesystem APIs and avoid custom storage abstractions unless they improve usability or compatibility.

## Serenity-Informed Behavior

Reference: `third_party/serenity/Userland/Applications/FileManager`.

Aurora Explorer ports the behavior, not the OS dependency:

- My Computer namespace
- directory icon/list views
- properties dialogs
- copy/move/delete progress
- mounted disks and removable media
- network locations
- Control Panel and Pi tools namespaces

Linux backends remain POSIX filesystem APIs, mount/device discovery, and
NetworkManager integration.
