# AuroraOS Networking

AuroraOS uses NetworkManager for Ethernet and Wi-Fi. Aurora owns the user
experience, while Linux owns the hardware drivers, supplicant, DHCP, DNS, and
connection profile storage.

## Wi-Fi Connection

`aurora-wifi-connect` is the AuroraOS 98 command/launcher for wireless setup.
It maps directly to `nmcli`:

- `aurora-wifi-connect list` scans visible access points.
- `aurora-wifi-connect connect "SSID"` connects to an open or saved network.
- `aurora-wifi-connect connect "SSID" "PASSWORD"` creates or updates a secured
  profile.
- `aurora-wifi-connect disconnect` disconnects Wi-Fi.
- `aurora-wifi-connect status` shows NetworkManager device status.

The graphical shell should wrap this command with a classic pixel dialog:
network list, signal strength, security state, password field, Connect,
Disconnect, Refresh, and Advanced buttons.
