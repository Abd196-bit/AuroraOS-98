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

## Required Behavior

Aurora Explorer provides:

- My Computer namespace
- directory icon/list views
- properties dialogs
- copy/move/delete progress
- mounted disks and removable media
- network locations
- Control Panel and Pi tools namespaces

It uses POSIX filesystem APIs, mount/device discovery, and NetworkManager integration.
