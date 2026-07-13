#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build" / "firefox-qemu"
APK_DIR = BASE / "apks"
ROOTFS = BASE / "rootfs"
OUT = BASE / "aurora-firefox-initramfs.cpio.lz4"
MODULES_SRC = ROOT / "build" / "linux-base" / "initramfs-root" / "lib" / "modules"
VSCODIUM_FLAC_COMPAT_URL = "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/x86_64/libflac-1.4.3-r1.apk"
REPOS = {
    "main": "https://dl-cdn.alpinelinux.org/alpine/edge/main/x86_64",
    "community": "https://dl-cdn.alpinelinux.org/alpine/edge/community/x86_64",
    "testing": "https://dl-cdn.alpinelinux.org/alpine/edge/testing/x86_64",
}

WANTED = [
    "alpine-base",
    "alsa-utils",
    "dbus",
    "dbus-x11",
    "feh",
    "font-dejavu",
    "firefox-esr",
    "jwm",
    "mesa-dri-gallium",
    "networkmanager-cli",
    "networkmanager-tui",
    "networkmanager-wifi",
    "desktop-file-utils",
    "dpkg",
    "file",
    "flac-libs",
    "pcmanfm",
    "py3-pip",
    "python3-tkinter",
    "python3",
    "vscodium",
    "wine",
    "iw",
    "idesk",
    "xdg-utils",
    "wireless-tools",
    "wpa_supplicant",
    "xclock",
    "xcursor-themes",
    "xinit",
    "xmessage",
    "xsetroot",
    "xterm",
    "xorg-server",
    "xf86-input-evdev",
    "xf86-input-libinput",
    "xf86-video-fbdev",
]

DEFAULT_APPS = [
    ("Browser", "Firefox", "firefox-esr", "Installed in this QEMU image"),
    ("Programming", "VSCodium", "aurora-code", "Real VSCodium editor installed in this QEMU image"),
    ("Game Dev", "Unity Hub Installer", "aurora-unity-hub", "Official Unity Hub installer flow"),
    ("Aurora", "Explorer", "aurora-explorer", "File manager"),
    ("Aurora", "Settings", "aurora-settings", "Unified settings app"),
    ("Aurora", "Package Center", "aurora-package-center", "Installer and app registry"),
    ("Aurora", "Task View", "aurora-task-view", "Workspace overview"),
    ("Aurora", "System Monitor", "aurora-system-monitor", "Live CPU, RAM, network, and storage view"),
    ("Aurora", "Terminal", "aurora-terminal", "Shell"),
    ("Aurora", "Run Windows EXE", "aurora-run-exe", "Wine launcher for Windows executables"),
    ("Aurora", "Install DEB", "aurora-run-deb", "Debian package installer"),
]

OPTIONAL_INSTALLERS = []


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def split_deps(raw: str) -> list[str]:
    deps = []
    for token in raw.split():
        if token.startswith("!"):
            continue
        token = token.split(":", 1)[1] if token.startswith("cmd:") else token
        deps.append(token)
    return deps


def dep_key(dep: str) -> str:
    if dep.startswith("/"):
        return dep
    if dep.startswith("so:"):
        return dep.split("=", 1)[0]
    return re.split(r"[<>=~]", dep, maxsplit=1)[0]


def parse_indexes() -> tuple[dict[str, dict], dict[str, str]]:
    by_name: dict[str, dict] = {}
    provides: dict[str, str] = {}
    for repo, base_url in REPOS.items():
        data = fetch(f"{base_url}/APKINDEX.tar.gz")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            text = archive.extractfile("APKINDEX").read().decode()
        for block in text.strip().split("\n\n"):
            item: dict[str, str] = {"repo": repo, "base_url": base_url}
            for line in block.splitlines():
                if len(line) > 2 and line[1] == ":":
                    item[line[0]] = line[2:]
            name = item.get("P")
            if not name:
                continue
            by_name[name] = item
            provides[name] = name
            for provided in item.get("p", "").split():
                provides[dep_key(provided)] = name
    return by_name, provides


def resolve_packages(by_name: dict[str, dict], provides: dict[str, str]) -> list[dict]:
    resolved: set[str] = set()
    queue = list(WANTED)
    while queue:
        requested = queue.pop(0)
        key = dep_key(requested)
        name = by_name.get(key, {}).get("P") or provides.get(key)
        if not name:
            if key.startswith("/") or key.startswith("so:"):
                continue
            raise RuntimeError(f"cannot resolve APK dependency: {requested}")
        if name in resolved:
            continue
        item = by_name[name]
        resolved.add(name)
        queue.extend(split_deps(item.get("D", "")))
    return [by_name[name] for name in sorted(resolved)]


def download_packages(packages: list[dict]) -> list[Path]:
    APK_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for item in packages:
        filename = f"{item['P']}-{item['V']}.apk"
        path = APK_DIR / filename
        if not path.exists():
            url = f"{item['base_url']}/{filename}"
            print(f"downloading {filename}")
            path.write_bytes(fetch(url))
        paths.append(path)
    return paths


def reset_rootfs() -> None:
    if ROOTFS.exists():
        for path in ROOTFS.rglob("*"):
            if path.is_symlink():
                continue
            try:
                path.chmod(path.stat().st_mode | 0o700)
            except (FileNotFoundError, PermissionError):
                pass
        for attempt in range(3):
            try:
                shutil.rmtree(ROOTFS)
                break
            except OSError:
                if attempt == 2:
                    subprocess.run(["rm", "-rf", str(ROOTFS)], check=True)
                time.sleep(0.5)
    for path in ["bin", "sbin", "usr/bin", "usr/sbin", "etc/X11", "root", "proc", "sys", "dev", "run", "tmp", "var/log"]:
        (ROOTFS / path).mkdir(parents=True, exist_ok=True)


def extract_packages(paths: list[Path]) -> None:
    for path in paths:
        run(["bsdtar", "-xf", str(path), "-C", str(ROOTFS)])


def install_vscodium_flac_compat() -> None:
    """Electron currently links FLAC ABI 12 while Alpine Edge ships ABI 14."""
    if (ROOTFS / "usr/lib/libFLAC.so.12").exists():
        return
    package = BASE / "compat" / "libflac-1.4.3-r1.apk"
    package.parent.mkdir(parents=True, exist_ok=True)
    if not package.exists():
        package.write_bytes(fetch(VSCODIUM_FLAC_COMPAT_URL))
    run(["bsdtar", "-xf", str(package), "-C", str(ROOTFS)])
    if MODULES_SRC.exists():
        dst = ROOTFS / "lib" / "modules"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(MODULES_SRC, dst, symlinks=True, ignore_dangling_symlinks=True)
        normalize_kernel_modules(dst)


def normalize_kernel_modules(modules_root: Path) -> None:
    """BusyBox modprobe in the initramfs cannot insmod Alpine's .ko.gz files."""
    if not modules_root.exists():
        return
    for compressed in sorted(modules_root.rglob("*.ko.gz")):
        plain = compressed.with_suffix("")
        with gzip.open(compressed, "rb") as src, plain.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        plain.chmod(compressed.stat().st_mode)
        compressed.unlink()
    for metadata in modules_root.rglob("modules.*"):
        if metadata.is_dir():
            continue
        try:
            text = metadata.read_text()
        except UnicodeDecodeError:
            continue
        metadata.write_text(text.replace(".ko.gz", ".ko"))


def write_file(path: str, content: str, mode: int = 0o644) -> None:
    dst = ROOTFS / path.lstrip("/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content)
    dst.chmod(mode)


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def write_app_surface() -> None:
    apps = DEFAULT_APPS + OPTIONAL_INSTALLERS
    icon_dir = ROOTFS / "usr" / "share" / "aurora" / "icons"
    if icon_dir.exists():
        shutil.rmtree(icon_dir)
    shutil.copytree(ROOT / "assets" / "icons" / "system", icon_dir, symlinks=True, ignore_dangling_symlinks=True)
    media_dir = ROOTFS / "usr" / "share" / "aurora"
    sound_dir = media_dir / "sounds"
    sound_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "IMG_0249.jpg", media_dir / "wallpaper.jpg")
    shutil.copy2(ROOT / "click.wav", sound_dir / "click.wav")

    font_dir = ROOTFS / "usr" / "share" / "fonts" / "aurora"
    font_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "MSW98UI-Regular copy.ttf", font_dir / "MSW98UI-Regular.ttf")
    shutil.copy2(ROOT / "MSW98UI-Bold copy.ttf", font_dir / "MSW98UI-Bold.ttf")
    write_file(
        "/etc/fonts/conf.d/99-aurora-fonts.conf",
        """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <alias>
    <family>sans-serif</family>
    <prefer><family>MS W98 UI</family></prefer>
  </alias>
  <alias>
    <family>system-ui</family>
    <prefer><family>MS W98 UI</family></prefer>
  </alias>
</fontconfig>
""",
    )

    cursor_source = ROOT / "assets" / "cursors" / "aurora-pointer.png"
    cursor_theme = ROOTFS / "usr" / "share" / "icons" / "AuroraPixel"
    cursor_dir = cursor_theme / "cursors"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cursor_source, cursor_theme / "Arrow1.png")
    (cursor_theme / "index.theme").write_text(
        "[Icon Theme]\nName=Aurora Pixel Cursor\nInherits=whiteglass\n"
    )
    cursor_config = cursor_theme / "cursor.conf"
    cursor_config.write_text("48 1 1 Arrow1.png\n")
    xcursorgen = shutil.which("xcursorgen") or "/opt/X11/bin/xcursorgen"
    subprocess.run(
        [xcursorgen, str(cursor_config), str(cursor_dir / "left_ptr")],
        cwd=cursor_theme,
        check=True,
    )
    for cursor_alias in ("default", "arrow", "top_left_arrow"):
        alias = cursor_dir / cursor_alias
        if alias.exists() or alias.is_symlink():
            alias.unlink()
        alias.symlink_to("left_ptr")

    write_file(
        "/usr/bin/aurora-click",
        """#!/bin/sh
(aplay -D default -q /usr/share/aurora/sounds/click.wav >/tmp/aurora-click.log 2>&1 || aplay -q /usr/share/aurora/sounds/click.wav >>/tmp/aurora-click.log 2>&1 || true) &
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-run-clicked",
        """#!/bin/sh
/usr/bin/aurora-click
exec "$@"
""",
        0o755,
    )

    def with_click(command: str) -> str:
        return f"/usr/bin/aurora-run-clicked {command}"

    launchers = {
        "settings": "/usr/bin/aurora-settings",
        "explorer": "/usr/bin/aurora-file-manager",
        "code": "/usr/bin/aurora-code",
        "unity-hub": "/usr/bin/aurora-unity-hub",
        "task-view": "/usr/bin/aurora-task-view",
        "package-center": "/usr/bin/aurora-package-center",
        "terminal": "xterm",
        "firefox": "/usr/bin/aurora-firefox",
    }
    for launcher_name, launcher_command in launchers.items():
        write_file(
            f"/usr/bin/aurora-launch-{launcher_name}",
            f"""#!/bin/sh
/usr/bin/aurora-click
exec {launcher_command}
""",
            0o755,
        )

    def icon_for(category: str, command: str) -> str:
        if command in {"firefox-esr", "chromium"}:
            return "package-48.png"
        if category == "Office":
            return "documents-48.png"
        if category == "Graphics":
            return "graphics-48.png"
        if category == "3D":
            return "desktop-48.png"
        if category == "Programming":
            return "terminal-48.png"
        if category == "Audio":
            return "audio-48.png"
        if category == "Video":
            return "video-48.png"
        if category == "Raspberry Pi":
            return "pi-tools-48.png"
        if category == "Optional":
            return "package-center-48.png"
        if "explorer" in command:
            return "explorer-48.png"
        if "settings" in command:
            return "settings-48.png"
        if "control" in command:
            return "control-panel-48.png"
        if "terminal" in command:
            return "terminal-48.png"
        if "text" in command:
            return "text-editor-48.png"
        if "disk" in command:
            return "disk-48.png"
        if "package" in command:
            return "package-center-48.png"
        return "folder-48.png"

    rows = "\n".join(
        f"<tr><td>{category}</td><td>{name}</td><td><code>{command}</code></td><td>{status}</td></tr>"
        for category, name, command, status in apps
    )
    groups: dict[str, list[tuple[str, str, str, str]]] = {}
    for app in apps:
        groups.setdefault(app[0], []).append(app)
    grouped_sections = []
    for category, items in groups.items():
        tiles = "\n".join(
            f"""<button class="app-tile" onclick="showApp('{name}', '{status}')">
  <img src="icons/{icon_for(category, command)}" alt="">
  <span>{name}</span>
  <small>{status}</small>
</button>"""
            for _, name, command, status in items
        )
        grouped_sections.append(f"<section class=\"category\"><h2>{category}</h2><div class=\"tiles\">{tiles}</div></section>")
    write_file(
        "/usr/share/aurora/app-center.html",
        f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>AuroraOS 98 Package Center</title>
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; min-height: 100%; background: #111 url("wallpaper.jpg") center/cover fixed no-repeat; color: #f3f3f3; font: 20px "MS W98 UI", sans-serif; }}
body {{ padding: 10px; }}
button, input {{ font: inherit; }}
.window {{ border: 1px solid #333; background: #202020; box-shadow: 0 0 0 1px #000; }}
.title {{ height: 48px; display: flex; align-items: center; justify-content: space-between; padding: 7px 9px 7px 12px; background: #0078d7; color: #fff; font-weight: bold; }}
.title-left {{ display: flex; align-items: center; gap: 8px; }}
.title-left img {{ width: 16px; height: 16px; }}
.controls {{ display: flex; gap: 3px; }}
.control {{ width: 36px; height: 26px; padding: 0; background: #0078d7; border: 1px solid #0078d7; color: #fff; line-height: 12px; }}
.control:hover, .toolbtn:hover, .sideitem:hover, .app-tile:hover {{ background: #2d2d2d; border-color: #3a96dd; }}
.menubar {{ height: 28px; display: flex; align-items: center; gap: 24px; padding: 0 10px; background: #2b2b2b; border-bottom: 1px solid #000; color: #ddd; }}
.toolbar {{ display: flex; align-items: center; gap: 8px; padding: 8px; background: #252525; border-bottom: 1px solid #000; }}
.toolbtn {{ min-width: 84px; padding: 5px 10px; border-radius: 0; border: 1px solid #4b4b4b; background: #333; color: #f3f3f3; }}
.content {{ display: grid; grid-template-columns: 240px 1fr; min-height: 680px; border-top: 1px solid #333; }}
.sidebar {{ padding: 10px; border-right: 1px solid #111; background: #191919; }}
.sidebar h3 {{ margin: 0 0 10px; font-size: 20px; }}
.sideitem {{ display: flex; align-items: center; gap: 8px; width: 100%; margin-bottom: 6px; padding: 7px; text-align: left; border: 1px solid transparent; background: transparent; color: #f3f3f3; }}
.sideitem.active {{ background: #0078d7; color: #fff; border-color: #0078d7; }}
.sideitem img {{ width: 24px; height: 24px; }}
.main {{ padding: 10px; overflow: auto; }}
h1 {{ margin: 0 0 12px; font-size: 32px; }}
h2 {{ margin: 18px 0 10px; font-size: 23px; }}
.note {{ border: 1px solid #3c3c3c; background: #111; color: #f3f3f3; padding: 8px; margin: 8px 0 12px; }}
.category {{ margin-bottom: 12px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }}
.app-tile {{ min-height: 150px; padding: 12px 9px; border-radius: 0; border: 1px solid #3c3c3c; background: #2a2a2a; color: #f3f3f3; text-align: center; }}
.app-tile:active {{ background: #005a9e; border-color: #3a96dd; padding: 10px 6px 6px 8px; }}
.app-tile img {{ width: 56px; height: 56px; display: block; margin: 0 auto 8px; }}
.app-tile span {{ display: block; font-weight: bold; min-height: 42px; }}
.app-tile small {{ display: block; color: #cfcfcf; font-size: 14px; line-height: 1.25; }}
table {{ width: 100%; border-collapse: collapse; background: #181818; margin-top: 10px; }}
th, td {{ border: 1px solid #3c3c3c; padding: 4px 6px; text-align: left; }}
th {{ background: #0078d7; color: #fff; }}
code {{ font: inherit; }}
.statusbar {{ display: grid; grid-template-columns: 1fr 160px 90px; gap: 4px; padding: 4px; border-top: 1px solid #000; background: #1f1f1f; }}
.statusbar div {{ border: 1px solid #333; padding: 3px 6px; background: #252525; }}
.toast {{ position: fixed; right: 22px; bottom: 48px; width: 360px; border: 1px solid #0078d7; background: #202020; color: #fff; padding: 10px; box-shadow: 4px 4px #000; display: none; }}
</style>
<script>
function clickSound() {{
  const audio = document.getElementById('click-sound');
  if (!audio) return;
  audio.currentTime = 0;
  audio.play().catch(() => {{}});
}}
function showApp(name, status) {{
  const box = document.getElementById('toast');
  box.innerHTML = '<b>' + name + '</b><br>' + status + '<br><br>Launcher registered in AuroraOS 98.';
  box.style.display = 'block';
  setTimeout(() => box.style.display = 'none', 3500);
}}
window.addEventListener('DOMContentLoaded', () => {{
  document.querySelectorAll('button').forEach((button) => button.addEventListener('click', clickSound));
}});
</script>
</head>
<body>
<audio id="click-sound" src="sounds/click.wav" preload="auto"></audio>
<div class="window">
<div class="title"><div class="title-left"><img src="icons/package-center-16.png" alt="">Aurora Package Center</div><div class="controls"><button class="control">_</button><button class="control">□</button><button class="control">X</button></div></div>
<div class="menubar"><span>File</span><span>Edit</span><span>View</span><span>Apps</span><span>Help</span></div>
<div class="toolbar"><button class="toolbtn">Back</button><button class="toolbtn">Search</button><button class="toolbtn">Updates</button><button class="toolbtn">Install</button><span>Location: aurora://package-center/all-apps</span></div>
<div class="content">
<aside class="sidebar">
<h3>Categories</h3>
<button class="sideitem active"><img src="icons/package-center-48.png" alt="">All Apps</button>
<button class="sideitem"><img src="icons/package-48.png" alt="">Installed</button>
<button class="sideitem"><img src="icons/graphics-48.png" alt="">Graphics</button>
<button class="sideitem"><img src="icons/terminal-48.png" alt="">Developer</button>
<button class="sideitem"><img src="icons/pi-tools-48.png" alt="">Raspberry Pi</button>
<button class="sideitem"><img src="icons/settings-48.png" alt="">Settings</button>
</aside>
<main class="main">
<h1>AuroraOS 98 Apps</h1>
<div class="note">Real Firefox ESR is running inside QEMU. This Package Center shows every Aurora default app, Pi tool, and optional installer with classic pixel UI controls.</div>
{''.join(grouped_sections)}
<h2>Package Registry</h2>
<table>
<thead><tr><th>Category</th><th>App</th><th>Launcher</th><th>Status</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</main>
</div>
<div class="statusbar"><div>44 launchers registered</div><div>Source: native / Flatpak / AppImage</div><div>Ready</div></div>
</div>
<div id="toast" class="toast"></div>
</body>
</html>
""",
    )
    app_list = "\n".join(f"{category:14} {name:22} {command:24} {status}" for category, name, command, status in apps)
    write_file(
        "/usr/share/aurora/app-list.txt",
        "AuroraOS 98 App Registry\n"
        "========================\n\n"
        f"{app_list}\n\n"
        "Right-click the desktop for the Aurora app menu.\n"
        "Firefox opens the Package Center page automatically.\n",
    )
    write_file(
        "/usr/bin/aurora-app-info",
        """#!/bin/sh
name="$1"
status="$2"
xmessage -center -title "AuroraOS 98" "$name

$status

This launcher is registered in AuroraOS 98.
Large third-party and workstation apps install in the full Linux rootfs profile." 2>/dev/null || true
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-open-package-center",
        """#!/bin/sh
exec /usr/bin/aurora-package-center
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-firefox",
        """#!/bin/sh
url="${1:-file:///usr/share/aurora/app-center.html}"
exec firefox-esr --no-remote --new-window "$url"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-package-center",
        """#!/bin/sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

network_up() {
  modprobe af_packet 2>/dev/null || true
  modprobe virtio_net 2>/dev/null || true
  netdev=eth0
  [ -e /sys/class/net/"$netdev" ] || netdev=$(ls /sys/class/net 2>/dev/null | grep -v "^lo$" | head -n 1)
  if [ -n "$netdev" ]; then
    ip link set "$netdev" up 2>/dev/null || true
    udhcpc -i "$netdev" -s /usr/share/udhcpc/default.script -q -t 8 -n 2>/dev/null || true
  fi
  printf "nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n" >/etc/resolv.conf
}

apk_ready() {
  mkdir -p /lib/apk/db /var/cache/apk /etc/apk
  touch /lib/apk/db/installed /lib/apk/db/world
  if ! grep -q "dl-cdn.alpinelinux.org/alpine/edge/main" /etc/apk/repositories 2>/dev/null; then
    printf "https://dl-cdn.alpinelinux.org/alpine/edge/main\\nhttps://dl-cdn.alpinelinux.org/alpine/edge/community\\n" >/etc/apk/repositories
  fi
}

install_pkg_terminal() {
  label="$1"
  pkg="$2"
  exec xterm -geometry 112x32+100+90 -title "Aurora Package Center - Installing" -e sh -c '
    export PATH=/sbin:/bin:/usr/sbin:/usr/bin
    label="$1"
    pkg="$2"
    clear
    echo "Aurora Package Center"
    echo "====================="
    echo
    echo "Installing: $label"
    echo "Package:    $pkg"
    echo
    modprobe af_packet 2>/dev/null || true
    modprobe virtio_net 2>/dev/null || true
    netdev=eth0
    [ -e /sys/class/net/"$netdev" ] || netdev=$(ls /sys/class/net 2>/dev/null | grep -v "^lo$" | head -n 1)
    if [ -n "$netdev" ]; then
      ip link set "$netdev" up 2>/dev/null || true
      udhcpc -i "$netdev" -s /usr/share/udhcpc/default.script -q -t 8 -n 2>/dev/null || true
    fi
    printf "nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n" >/etc/resolv.conf
    mkdir -p /lib/apk/db /var/cache/apk /etc/apk
    touch /lib/apk/db/installed /lib/apk/db/world
    if ! grep -q "dl-cdn.alpinelinux.org/alpine/edge/main" /etc/apk/repositories 2>/dev/null; then
      printf "https://dl-cdn.alpinelinux.org/alpine/edge/main\\nhttps://dl-cdn.alpinelinux.org/alpine/edge/community\\n" >/etc/apk/repositories
    fi
    echo "Updating package index..."
    apk --initdb update
    echo
    echo "Installing package..."
    apk --initdb add $pkg
    echo
    echo "Done. Press Enter to close."
    read line
  ' sh "$label" "$pkg"
}

while :; do
  /usr/bin/aurora-click
  xmessage -center -title "Aurora Package Center" \
    -buttons "VSCodium:8,Firefox:14,Unity Hub:16,Python+pip:5,Wine EXE:11,Explorer:15,Internet:12,Custom APK:13,Close:0" \
    "Aurora Package Center

Network source: QEMU wired NAT through the Mac internet connection.
Install target: live RAM rootfs preview.

Preinstalled apps open directly. Custom APK installs are experimental in this RAM preview and show command logs."
  case "$?" in
    5) xmessage -center -title "Python + pip" "Python and pip are already installed.

$(python3 --version 2>/dev/null)
$(pip --version 2>/dev/null)" 2>/dev/null || true ;;
    8) /usr/bin/aurora-code & ;;
    11) /usr/bin/aurora-run-exe ;;
    12) network_up; wget -q -O /tmp/aurora-net-test.html http://example.com/ && msg="Internet: WORKING" || msg="Internet: NOT CONNECTED"; xmessage -center -title "Aurora Package Center" "$msg" 2>/dev/null || true ;;
    13) exec xterm -geometry 96x20+150+140 -title "Custom APK Package" -e sh -c 'printf "APK package name: "; read pkg; [ -n "$pkg" ] && /usr/bin/aurora-package-install-custom "$pkg"' ;;
    14) /usr/bin/aurora-firefox & ;;
    15) /usr/bin/aurora-file-manager /tmp/firefox-home & ;;
    16) /usr/bin/aurora-unity-hub & ;;
    *) exit 0 ;;
  esac
done
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-package-install-custom",
        """#!/bin/sh
label="$1"
pkg="$1"
exec xterm -geometry 112x32+100+90 -title "Aurora Package Center - Installing" -e sh -c '
  export PATH=/sbin:/bin:/usr/sbin:/usr/bin
  pkg="$1"
  modprobe af_packet 2>/dev/null || true
  ip link set eth0 up 2>/dev/null || true
  udhcpc -i eth0 -s /usr/share/udhcpc/default.script -q -t 8 -n 2>/dev/null || true
  printf "nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n" >/etc/resolv.conf
  mkdir -p /lib/apk/db /var/cache/apk /etc/apk
  touch /lib/apk/db/installed /lib/apk/db/world
  printf "https://dl-cdn.alpinelinux.org/alpine/edge/main\\nhttps://dl-cdn.alpinelinux.org/alpine/edge/community\\n" >/etc/apk/repositories
  clear
  echo "Installing custom APK package: $pkg"
  echo
  apk --initdb update && apk --initdb add "$pkg"
  echo
  echo "Press Enter to close."
  read line
' sh "$pkg"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-unity-hub",
        """#!/bin/sh
/usr/bin/aurora-click
xmessage -center -buttons "Open Official Installer:1,Close:0" -title "Unity Hub Installer" "Unity Hub is not bundled in this RAM preview.

Reason:
Unity Hub is proprietary software distributed by Unity through official Linux installer channels. AuroraOS can provide a launcher/installer, but should not redistribute Unity Hub inside the base OS image.

The full AuroraOS rootfs should install Unity Hub into persistent storage. This QEMU initramfs is for the desktop shell preview." 2>/dev/null
if [ "$?" = 1 ]; then
  exec /usr/bin/aurora-firefox "https://docs.unity.com/en-us/hub/install-hub-linux"
fi
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-run-exe",
        """#!/bin/sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin
if ! command -v wine >/dev/null 2>&1; then
  xmessage -center -title "Aurora Run EXE" "Wine is not installed yet.

Open Package Center and choose Windows EXE support." 2>/dev/null || true
  exit 0
fi
file=$(xmessage -center -print -title "Aurora Run EXE" -buttons "/tmp/firefox-home/Downloads:2,/tmp:3,Cancel:0" "Choose where the EXE is.

Explorer is the normal path: open Downloads and double-click the .exe file.")
rc=$?
case "$rc" in
  2) /usr/bin/aurora-file-manager /tmp/firefox-home/Downloads & ;;
  3) /usr/bin/aurora-file-manager /tmp & ;;
esac
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-show-apps",
        """#!/bin/sh
xmessage -center -title "AuroraOS 98 Apps" "$(cat /usr/share/aurora/app-list.txt)" 2>/dev/null || true
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-wifi-connect",
        """#!/bin/sh
if command -v nmcli >/dev/null 2>&1; then
  case "${1:-status}" in
    list|scan)
      nmcli radio wifi on >/dev/null 2>&1 || true
      exec nmcli --fields IN-USE,SSID,SIGNAL,SECURITY dev wifi list
      ;;
    connect)
      ssid="${2:-}"
      password="${3:-}"
      if [ -z "$ssid" ]; then
        echo "Usage: aurora-wifi-connect connect \"SSID\" \"PASSWORD\""
        exit 2
      fi
      nmcli radio wifi on
      if [ -n "$password" ]; then
        exec nmcli dev wifi connect "$ssid" password "$password"
      fi
      exec nmcli dev wifi connect "$ssid"
      ;;
    disconnect)
      exec nmcli device disconnect wlan0
      ;;
    *)
      exec nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status
      ;;
  esac
fi

cat <<'EOF'
AuroraOS 98 Wi-Fi Connection
============================

This QEMU preview has a virtual wired adapter, not a Wi-Fi radio.

In the full AuroraOS image on a laptop or Raspberry Pi:
  Start -> Control Panel -> Network -> Wi-Fi Connection

Commands:
  aurora-wifi-connect list
  aurora-wifi-connect connect "SSID" "PASSWORD"
  aurora-wifi-connect disconnect
  aurora-wifi-connect status

Backend:
  NetworkManager / nmcli

Press Enter to close.
EOF
read line
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-open-wifi",
        """#!/bin/sh
exec /usr/bin/aurora-settings
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-settings",
        """#!/bin/sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

click() { /usr/bin/aurora-click >/dev/null 2>&1 || true; }

network_up() {
  ip link set eth0 up >/dev/null 2>&1 || true
  udhcpc -i eth0 -s /usr/share/udhcpc/default.script -q -t 5 -n >/tmp/aurora-network-action.log 2>&1 || true
  printf 'nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n' >/etc/resolv.conf
}

panel_system() {
  total=$(awk '/MemTotal/ { printf "%d MB", $2/1024 }' /proc/meminfo 2>/dev/null)
  avail=$(awk '/MemAvailable/ { printf "%d MB", $2/1024 }' /proc/meminfo 2>/dev/null)
  xmessage -center -buttons "OK:0" -title "Aurora Settings - System" "AuroraOS 98 Preview

Kernel: $(uname -r)
Desktop: JWM shell
Memory: $avail available / $total total
Downloads: /tmp/firefox-home/Downloads

Firefox, Wine, pip, PCManFM, Package Center, and a code editor are installed in this QEMU image." 2>/dev/null || true
}

panel_network() {
  network_up
  status=$(nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status 2>/dev/null || ip addr show)
  wifi=$(nmcli -t -f SSID,SIGNAL,SECURITY device wifi list 2>/dev/null | sed 's/:/    /g' | head -n 12)
  [ -n "$wifi" ] || wifi="No Wi-Fi radio exposed in this QEMU VM. QEMU uses wired NAT through the Mac internet connection."
  internet=$(wget -q -O /tmp/aurora-net-test.html http://example.com/ >/dev/null 2>&1 && echo "WORKING" || echo "NOT CONNECTED")
  xmessage -center -buttons "Refresh Wired:2,Join Wi-Fi:3,Close:0" -title "Aurora Settings - Network" "Network

Internet: $internet

Devices:
$status

Wi-Fi:
$wifi

QEMU normally exposes wired NAT, not the Mac Wi-Fi card. Real Wi-Fi lists show on Raspberry Pi/laptop hardware or with USB Wi-Fi passthrough." 2>/dev/null
  rc=$?
  [ "$rc" = 2 ] && panel_network
  [ "$rc" = 3 ] && /usr/bin/aurora-wifi-ui &
}

panel_sound() {
  xmessage -center -buttons "Play Test:2,Close:0" -title "Aurora Settings - Sound" "Sound

Output: QEMU ES1370 / host CoreAudio
Click sound: /usr/share/aurora/sounds/click.wav

If Firefox audio is silent, check QEMU was launched with -audiodev coreaudio and ES1370." 2>/dev/null
  [ "$?" = 2 ] && click
}

panel_apps() {
  xmessage -center -buttons "Package Center:2,Close:0" -title "Aurora Settings - Apps" "Installed apps

Firefox ESR
VSCodium: installed VS Code-compatible editor
Aurora Explorer: PCManFM file manager
Package Center: native APK installer
Wine: Windows EXE support
dpkg: DEB installer
Python + pip: installed

Downloads open from Explorer and route .exe, .AppImage, .deb, scripts, and Linux executables." 2>/dev/null
  [ "$?" = 2 ] && /usr/bin/aurora-package-center &
}

panel_task_view() {
  xmessage -center -buttons "Desktop 1:11,Desktop 2:12,Desktop 3:13,Desktop 4:14,Close:0" -title "Aurora Settings - Task View" "Task View

Desktop 1: Main apps and browser
Desktop 2: Files and downloads
Desktop 3: Development
Desktop 4: System tools

Task View opens only when clicked from the taskbar or Start menu." 2>/dev/null
  rc=$?
  case "$rc" in
    11) jwm -desktop 1 ;;
    12) jwm -desktop 2 ;;
    13) jwm -desktop 3 ;;
    14) jwm -desktop 4 ;;
  esac
}

while :; do
  click
  xmessage -center -buttons "System:10,Network/Wi-Fi:11,Sound:12,Appearance:13,Task View:14,Apps:15,Explorer:16,Close:0" -title "Aurora Settings" "Aurora Settings

One control app for AuroraOS 98.

Choose a settings area." 2>/dev/null
  case "$?" in
    10) panel_system ;;
    11) panel_network ;;
    12) panel_sound ;;
    13) xmessage -center -title "Aurora Appearance" "Wallpaper: /usr/share/aurora/wallpaper.jpg
Theme: AuroraOS 98 dark classic
Window manager: JWM" 2>/dev/null || true ;;
    14) panel_task_view ;;
    15) panel_apps ;;
    16) /usr/bin/aurora-file-manager /tmp/firefox-home & ;;
    *) exit 0 ;;
  esac
done
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-settings-network",
        """#!/bin/sh
root=/tmp/aurora-settings
mkdir -p "$root/cgi-bin"
cp /usr/share/aurora/sounds/click.wav "$root/click.wav" 2>/dev/null || true
cp /usr/share/aurora/wallpaper.jpg "$root/wallpaper.jpg" 2>/dev/null || true
cat > "$root/cgi-bin/network.cgi" <<'CGI'
#!/bin/sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

decode() {
  value=${1//+/ }
  printf '%b' "${value//%/\\x}"
}

field() {
  key="$1"
  printf '%s' "$QUERY_STRING" | tr '&' '\\n' | awk -F= -v k="$key" '$1 == k { print substr($0, length(k) + 2); exit }'
}

html_escape() {
  sed -e 's/&/\\&amp;/g' -e 's/</\\&lt;/g' -e 's/>/\\&gt;/g' -e 's/"/\\&quot;/g'
}

action=$(field action)
ssid=$(decode "$(field ssid)")
password=$(decode "$(field password)")
message=""

case "$action" in
  wired)
    ip link set eth0 up >/tmp/aurora-network-action.log 2>&1 || true
    nmcli device connect eth0 >>/tmp/aurora-network-action.log 2>&1 || true
    udhcpc -i eth0 -s /usr/share/udhcpc/default.script -q -t 8 -n >>/tmp/aurora-network-action.log 2>&1 || true
    printf 'nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n' >/etc/resolv.conf
    message="Wired install network refreshed."
    ;;
  wifi-on)
    nmcli radio wifi on >/tmp/aurora-network-action.log 2>&1 || true
    nmcli device wifi rescan >>/tmp/aurora-network-action.log 2>&1 || true
    message="Wi-Fi scan requested."
    ;;
  wifi-off)
    nmcli radio wifi off >/tmp/aurora-network-action.log 2>&1 || true
    message="Wi-Fi disabled."
    ;;
  sound-test)
    /usr/bin/aurora-click
    message="Played the Aurora click sound through ALSA."
    ;;
  connect)
    if [ -n "$ssid" ]; then
      nmcli radio wifi on >/tmp/aurora-network-action.log 2>&1 || true
      if [ -n "$password" ]; then
        nmcli device wifi connect "$ssid" password "$password" >>/tmp/aurora-network-action.log 2>&1
      else
        nmcli device wifi connect "$ssid" >>/tmp/aurora-network-action.log 2>&1
      fi
      message="Connection attempted for $ssid."
    else
      message="Type a network name first."
    fi
    ;;
esac

echo "Content-Type: text/html"
echo
cat <<'HTML'
<!doctype html><html><head><meta charset="utf-8"><title>Aurora Settings</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#111 url("/wallpaper.jpg") center/cover fixed no-repeat;color:#f3f3f3;font:21px "MS W98 UI",Arial,sans-serif}.window{width:1220px;max-width:calc(100vw - 24px);margin:12px auto;background:#1f1f24;border:1px solid #353542;box-shadow:0 12px 34px #000}.title{height:58px;background:#0078d7;color:#fff;font-size:26px;font-weight:700;padding:13px 20px}.nav{display:flex;gap:10px;padding:14px 18px;background:#18181d;border-bottom:1px solid #333}.nav button{font:inherit;color:#eee;background:#2b2b33;border:1px solid #454553;padding:12px 16px}.nav button.active{background:#0078d7;border-color:#3195e6}.main{padding:20px;min-height:720px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.section{background:#292933;border:1px solid #3c3c48;padding:18px;margin-bottom:16px}.wide{grid-column:1/-1}.row{display:grid;grid-template-columns:230px 1fr;gap:16px;margin-bottom:12px;align-items:center}.value{background:#17171b;border:1px solid #3c3c48;padding:12px}.btn,input{font:inherit}.btn{padding:12px 16px;background:#333742;color:#f3f3f3;border:1px solid #555b6a}.btn:hover{background:#404755;border-color:#3a96dd}.btn:active{background:#005a9e}input{width:100%;padding:12px;border:1px solid #555;background:#111;color:#fff}table{width:100%;border-collapse:collapse;background:#18181d}th,td{border:1px solid #3c3c48;padding:12px;text-align:left}th{background:#0078d7;color:#fff}.note{background:#15151a;border:1px solid #3c3c48;padding:14px}.msg{background:#111;border:1px solid #0078d7;padding:12px;margin-bottom:14px}.actions{display:flex;gap:12px;flex-wrap:wrap}.storage{height:44px;display:grid;grid-template-columns:26% 17% 1% 1% 34% 14% 7%;overflow:hidden;border:1px solid #424250}.storage span:nth-child(1){background:#ff4343}.storage span:nth-child(2){background:#ff9b2e}.storage span:nth-child(3){background:#ffd400}.storage span:nth-child(4){background:#30d158}.storage span:nth-child(5){background:#8a8a8a}.storage span:nth-child(6){background:#aaa}.storage span:nth-child(7){background:#555}.desktops{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.desktop{height:110px;background:#111;border:2px solid #444;display:flex;align-items:center;justify-content:center}.desktop.active{border-color:#0078d7;background:#08345a}h1{font-size:40px;margin:0 0 18px}h2{font-size:28px;margin:0 0 14px}
</style><script>function clickSound(){const a=document.getElementById('click-sound');if(a){a.currentTime=0;a.play().catch(()=>{});}}window.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('button').forEach(b=>b.addEventListener('click',clickSound)));</script></head><body><audio id="click-sound" src="/click.wav" preload="auto"></audio><div class="window"><div class="title">Aurora Settings</div><div class="nav"><button class="active">System</button><button>Network</button><button>Sound</button><button>Appearance</button><button>Task View</button><button>Apps</button></div><div class="main"><h1>System</h1>
HTML
if [ -n "$message" ]; then
  printf '<div class="msg">%s</div>\\n' "$(printf '%s' "$message" | html_escape)"
fi
cat <<'HTML'
<div class="grid">
<div class="section wide"><h2>Storage</h2><div class="row"><div>Macintosh HD</div><div class="value">Aurora preview rootfs in RAM</div></div><div class="storage"><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div><p class="note">Applications, documents, developer files, system data, and cache are shown in one Settings app.</p></div>
<div class="section"><h2>Sound</h2><div class="row"><div>Output</div><div class="value">QEMU ES1370 / CoreAudio</div></div><form method="get" action="/cgi-bin/network.cgi"><input type="hidden" name="action" value="sound-test"><button class="btn" type="submit">Play Click Sound</button></form></div>
<div class="section"><h2>Task View</h2><div class="desktops"><div class="desktop active">Desktop 1</div><div class="desktop">Desktop 2</div><div class="desktop">Desktop 3</div><div class="desktop">Desktop 4</div></div><p class="note">Use the taskbar Task View button or the desktop pager to switch workspaces.</p></div>
<div class="section wide"><h2>Network</h2>
HTML
if command -v nmcli >/dev/null 2>&1; then
  nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status 2>/dev/null | awk 'NR > 1 { printf "<div class=\\"row\\"><div>%s</div><div class=\\"value\\">%s / %s / %s</div></div>\\n", $1, $2, $3, $4 }'
else
  echo '<div class="row"><div>Backend</div><div class="value">NetworkManager is not installed.</div></div>'
fi
if wget -q -O /tmp/aurora-net-test.html http://example.com/ >/dev/null 2>&1; then
  echo '<div class="row"><div>Internet</div><div class="value">Working: app downloads can use QEMU wired NAT.</div></div>'
else
  echo '<div class="row"><div>Internet</div><div class="value">Not connected yet. Click Refresh Wired Install Network.</div></div>'
fi
cat <<'HTML'
<form method="get" action="/cgi-bin/network.cgi"><input type="hidden" name="action" value="wired"><button class="btn" type="submit">Refresh Wired Install Network</button></form>
<p class="note">In QEMU, app downloads use the wired NAT adapter. Your Mac Wi-Fi is not a guest Wi-Fi card. Real Wi-Fi lists appear on Raspberry Pi/laptops or with USB Wi-Fi passthrough.</p>
</div>
<div class="section"><h2>Wi-Fi</h2><div class="actions">
<form method="get" action="/cgi-bin/network.cgi"><input type="hidden" name="action" value="wifi-on"><button class="btn" type="submit">Turn On / Scan</button></form>
<form method="get" action="/cgi-bin/network.cgi"><input type="hidden" name="action" value="wifi-off"><button class="btn" type="submit">Turn Off</button></form>
</div><br><table><tr><th></th><th>Network Name</th><th>Signal</th><th>Security</th></tr>
HTML
rows=""
if command -v nmcli >/dev/null 2>&1; then
  rows=$(nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list 2>/dev/null | awk -F: '
    NF >= 4 {
      inuse=$1; ssid=$2; signal=$3; security=$4;
      if (ssid == "") ssid="Hidden network";
      gsub("&","&amp;",ssid); gsub("<","&lt;",ssid); gsub(">","&gt;",ssid);
      printf "<tr><td>%s</td><td>%s</td><td>%s%%</td><td>%s</td></tr>\\n", inuse, ssid, signal, security;
    }')
fi
if [ -n "$rows" ]; then
  printf '%s\\n' "$rows"
else
  cat <<'HTML'
<tr><td></td><td>No Wi-Fi radio exposed</td><td>0%</td><td>Use hardware Wi-Fi or USB passthrough</td></tr>
HTML
fi
cat <<'HTML'
</table><h3>Join Network</h3>
<form method="get" action="/cgi-bin/network.cgi"><input type="hidden" name="action" value="connect">
<div class="row"><label>Network Name</label><input name="ssid" autocomplete="off"></div>
<div class="row"><label>Password</label><input name="password" type="password"></div>
<button class="btn" type="submit">Connect</button></form>
</div></div></div></div></body></html>
HTML
CGI
chmod +x "$root/cgi-bin/network.cgi"
if ! [ -f /tmp/aurora-settings-httpd.pid ] || ! kill -0 "$(cat /tmp/aurora-settings-httpd.pid)" 2>/dev/null; then
  busybox httpd -p 127.0.0.1:8098 -h "$root"
  pidof httpd | awk '{print $1; exit}' >/tmp/aurora-settings-httpd.pid 2>/dev/null || true
fi
exec firefox-esr --no-remote --new-window "http://127.0.0.1:8098/cgi-bin/network.cgi"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-wifi-ui",
"""#!/bin/sh
exec /usr/bin/aurora-settings
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-file-manager",
        """#!/bin/sh
root="${1:-/tmp/firefox-home/Downloads}"
mkdir -p /tmp/firefox-home/Downloads /tmp/firefox-home/Desktop /tmp/firefox-home/Documents /tmp/firefox-home/Applications /tmp/firefox-home/Pictures /tmp/firefox-home/.config/pcmanfm/default /tmp/firefox-home/.config/libfm /tmp/firefox-home/.config/gtk-3.0
if [ ! -f /tmp/firefox-home/.config/pcmanfm/default/pcmanfm.conf ]; then
  cat >/tmp/firefox-home/.config/pcmanfm/default/pcmanfm.conf <<'EOF'
[config]
bm_open_method=0

[volume]
mount_on_startup=1
mount_removable=1
autorun=0

[ui]
always_show_tabs=0
max_tab_chars=32
win_width=1180
win_height=720
splitter_pos=230
media_in_new_tab=0
desktop_folder_new_win=0
change_tab_on_drop=1
close_on_unmount=1
focus_previous=1
side_pane_mode=places
view_mode=icon
show_hidden=0
sort=name;ascending;
toolbar=newtab;navigation;home;
show_statusbar=1
pathbar_mode_buttons=0

[desktop]
wallpaper_mode=crop
wallpaper_common=1
wallpaper=/usr/share/aurora/wallpaper.jpg
desktop_bg=#111111
desktop_fg=#f3f3f3
desktop_shadow=#000000
show_wm_menu=0
sort=name;ascending;
show_documents=0
EOF
fi
if [ ! -f /tmp/firefox-home/.config/libfm/libfm.conf ]; then
  cat >/tmp/firefox-home/.config/libfm/libfm.conf <<'EOF'
[config]
single_click=0
use_trash=1
confirm_del=1
terminal=xterm
archiver=xarchiver

[ui]
big_icon_size=72
small_icon_size=32
pane_icon_size=32
thumbnail_size=160
show_thumbnail=1
shadow_hidden=1
EOF
fi
if [ ! -f /tmp/firefox-home/.config/gtk-3.0/settings.ini ]; then
  cat >/tmp/firefox-home/.config/gtk-3.0/settings.ini <<'EOF'
[Settings]
gtk-theme-name=Raleigh
gtk-icon-theme-name=hicolor
gtk-font-name=MS W98 UI 17
gtk-application-prefer-dark-theme=1
gtk-enable-animations=0
EOF
fi
export HOME=/tmp/firefox-home
export XDG_CONFIG_HOME=/tmp/firefox-home/.config
export XDG_DATA_HOME=/tmp/firefox-home/.local/share
export XDG_RUNTIME_DIR=/run/user/0
export DISPLAY="${DISPLAY:-:0}"
export GTK_THEME=Adwaita:dark

if command -v pcmanfm >/dev/null 2>&1; then
  if command -v dbus-launch >/dev/null 2>&1; then
    eval "$(dbus-launch --sh-syntax 2>/dev/null)" || true
  fi
  pcmanfm --new-win "$root" >/tmp/aurora-pcmanfm.log 2>&1 && exit 0
  pcmanfm "$root" >>/tmp/aurora-pcmanfm.log 2>&1 && exit 0
fi

exec xterm -geometry 104x34+86+76 -title "AuroraOS File Explorer" -bg '#111111' -fg '#f3f3f3' -fa 'MS W98 UI' -fs 14 -e sh -c 'cd "$1" 2>/dev/null || cd /tmp/firefox-home; echo "PCManFM did not stay open; showing fallback file list."; echo; ls -lah; echo; echo "Press Enter to close."; read line' sh "$root"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-desktop-icons",
        """#!/bin/sh
export HOME=/tmp/firefox-home
export XDG_CONFIG_HOME=/tmp/firefox-home/.config
export XDG_DATA_HOME=/tmp/firefox-home/.local/share
export XDG_RUNTIME_DIR=/run/user/0
export DISPLAY="${DISPLAY:-:0}"
export GTK_THEME=Adwaita:dark
mkdir -p /tmp/firefox-home/Desktop /tmp/firefox-home/.config/pcmanfm/default /tmp/firefox-home/.config/libfm
chmod +x /tmp/firefox-home/Desktop/*.desktop 2>/dev/null || true
if command -v idesk >/dev/null 2>&1; then
  mkdir -p /tmp/firefox-home/.idesktop
  cat >/tmp/firefox-home/.ideskrc <<'EOF'
table Config
  FontName: MS W98 UI
  FontSize: 16
  FontColor: #ffffff
  ToolTip.FontSize: 13
  ToolTip.FontColor: #ffffff
  ToolTip.BackColor: #202020
  ToolTip.CaptionOnHover: true
  Locked: false
  Transparency: 100
  Shadow: true
  ShadowColor: #000000
  ShadowX: 2
  ShadowY: 2
  SnapShadow: false
  IconSnap: false
  SnapWidth: 120
  SnapHeight: 112
  SnapOrigin: TopLeft
  SnapShadowTrans: 200
  CaptionOnHover: false
end
table Actions
  Lock: control right doubleClk
  Reload: middle doubleClk
  Drag: left hold
  EndDrag: left singleClk
  Execute[0]: left doubleClk
end
EOF
  make_link() {
    file="$1" caption="$2" icon="$3" x="$4" y="$5" command="$6"
    cat >"/tmp/firefox-home/.idesktop/$file.lnk" <<EOF
table Icon
  Caption: $caption
  ToolTip.Caption: Open $caption
  Icon: /usr/share/aurora/icons/$icon
  X: $x
  Y: $y
  Command[0]: $command
end
EOF
  }
  make_link explorer "Aurora Explorer" explorer-48.png 180 60 /usr/bin/aurora-explorer
  make_link firefox "Firefox" network-48.png 180 190 /usr/bin/aurora-firefox
  make_link code "VSCodium" text-editor-48.png 180 320 /usr/bin/aurora-code
  make_link settings "Settings" settings-48.png 180 450 /usr/bin/aurora-settings
  make_link packages "Package Center" package-center-48.png 180 580 /usr/bin/aurora-package-center
  make_link terminal "Terminal" terminal-48.png 430 60 /usr/bin/aurora-terminal
  make_link taskview "Task View" taskbar-48.png 430 190 /usr/bin/aurora-task-view
  exec idesk
fi
if [ ! -f /tmp/firefox-home/.config/pcmanfm/default/pcmanfm.conf ]; then
  cat >/tmp/firefox-home/.config/pcmanfm/default/pcmanfm.conf <<'EOF'
[config]
bm_open_method=0

[volume]
mount_on_startup=1
mount_removable=1
autorun=0

[ui]
view_mode=icon
big_icon_size=72
small_icon_size=32
pane_icon_size=32
show_hidden=0
sort=name;ascending;

[desktop]
wallpaper_mode=crop
wallpaper_common=1
wallpaper=/usr/share/aurora/wallpaper.jpg
desktop_bg=#111111
desktop_fg=#f3f3f3
desktop_shadow=#000000
show_wm_menu=0
sort=name;ascending;
show_documents=0
EOF
fi
if [ ! -f /tmp/firefox-home/.config/libfm/libfm.conf ]; then
  cat >/tmp/firefox-home/.config/libfm/libfm.conf <<'EOF'
[config]
single_click=0
use_trash=1
confirm_del=1
terminal=xterm

[ui]
big_icon_size=72
small_icon_size=32
pane_icon_size=32
thumbnail_size=160
show_thumbnail=1
EOF
fi
if [ ! -f /tmp/firefox-home/.config/user-dirs.dirs ]; then
  cat >/tmp/firefox-home/.config/user-dirs.dirs <<'EOF'
XDG_DESKTOP_DIR="/tmp/firefox-home/Desktop"
XDG_DOWNLOAD_DIR="/tmp/firefox-home/Downloads"
XDG_DOCUMENTS_DIR="/tmp/firefox-home/Documents"
XDG_PICTURES_DIR="/tmp/firefox-home/Pictures"
EOF
fi
if command -v pcmanfm >/dev/null 2>&1; then
  if command -v dbus-launch >/dev/null 2>&1; then
    eval "$(dbus-launch --sh-syntax 2>/dev/null)" || true
  fi
  exec pcmanfm --desktop --profile default
fi
exit 0
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-explorer",
        """#!/bin/sh
exec /usr/bin/aurora-file-manager "$@"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-code",
        """#!/bin/sh
workspace="${1:-/tmp/firefox-home/Documents}"
mkdir -p "$workspace"
export HOME=/tmp/firefox-home
export XDG_CONFIG_HOME=/tmp/firefox-home/.config
export XDG_DATA_HOME=/tmp/firefox-home/.local/share
export XDG_RUNTIME_DIR=/run/user/0
export DISPLAY="${DISPLAY:-:0}"
export ELECTRON_OZONE_PLATFORM_HINT=x11
if command -v codium >/dev/null 2>&1; then
  codium --no-sandbox --disable-chromium-sandbox --disable-gpu \
    --disable-dev-shm-usage --ozone-platform=x11 \
    --user-data-dir=/tmp/firefox-home/.config/VSCodium "$workspace" \
    >/tmp/aurora-vscodium.log 2>&1
  rc=$?
  xmessage -center -title "VSCodium launch error" "VSCodium exited with status $rc.

$(tail -n 18 /tmp/aurora-vscodium.log 2>/dev/null)" 2>/dev/null || true
  exit "$rc"
fi
xmessage -center -title "VSCodium" "VSCodium is missing from this image.

Expected command:
  /usr/bin/codium" 2>/dev/null || true
""",
        0o755,
    )
    write_file(
        "/usr/bin/code",
        """#!/bin/sh
exec /usr/bin/aurora-code "$@"
""",
        0o755,
    )
    write_file(
        "/usr/bin/vscodium",
        """#!/bin/sh
exec /usr/bin/aurora-code "$@"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-open-downloaded-file",
        """#!/bin/sh
file="$1"
[ -n "$file" ] || exit 0
case "$file" in
  *.exe|*.EXE|*.msi|*.MSI)
    exec /usr/bin/aurora-run-exe-file "$file"
    ;;
  *.AppImage|*.appimage)
    exec /usr/bin/aurora-run-appimage "$file"
    ;;
  *.deb|*.DEB)
    exec /usr/bin/aurora-run-deb-file "$file"
    ;;
  *.sh)
    chmod +x "$file" 2>/dev/null || true
    xmessage -center -buttons "Run:1,Cancel:0" -title "Run Script" "Run this script?

$file" 2>/dev/null
    [ "$?" = 1 ] || exit 0
    exec xterm -geometry 100x30+100+90 -title "Run Script" -e sh -c '"$1"; echo; echo "Press Enter to close."; read line' sh "$file"
    ;;
esac
if [ -x "$file" ]; then
  xmessage -center -buttons "Run:1,Cancel:0" -title "Run Linux App" "Run this executable?

$file" 2>/dev/null
  [ "$?" = 1 ] || exit 0
  exec xterm -geometry 100x30+100+90 -title "Run Linux App" -e sh -c '"$1"; echo; echo "Press Enter to close."; read line' sh "$file"
fi
exec xdg-open "$file"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-run-exe-file",
        """#!/bin/sh
exe="$1"
if ! command -v wine >/dev/null 2>&1; then
  xmessage -center -title "Windows EXE Support" "Wine is not installed.

Open Package Center and choose Windows EXE support." 2>/dev/null || true
  exit 0
fi
xmessage -center -buttons "Run with Wine:1,Cancel:0" -title "Run Windows EXE" "Run this Windows executable with Wine?

$exe" 2>/dev/null
[ "$?" = 1 ] || exit 0
exec wine "$exe"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-run-appimage",
        """#!/bin/sh
app="$1"
chmod +x "$app" 2>/dev/null || true
xmessage -center -buttons "Run:1,Cancel:0" -title "Run AppImage" "Run this AppImage?

$app" 2>/dev/null
[ "$?" = 1 ] || exit 0
exec xterm -geometry 100x30+100+90 -title "Run AppImage" -e sh -c '"$1"; echo; echo "Press Enter to close."; read line' sh "$app"
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-run-deb-file",
        """#!/bin/sh
deb="$1"
xmessage -center -buttons "Install:1,Cancel:0" -title "Install DEB Package" "Install this Debian package?

$deb

Install logs will open in a separate window." 2>/dev/null
[ "$?" = 1 ] || exit 0
exec xterm -geometry 120x34+80+70 -title "Install DEB Package" -e sh -c '
echo "AuroraOS DEB installer"
echo "======================"
echo
echo "Package: $1"
echo
if ! command -v dpkg >/dev/null 2>&1; then
  echo "dpkg is not installed in this image."
else
  echo "Running: dpkg -i $1"
  echo
  dpkg -i "$1"
  code=$?
  echo
  if [ "$code" -eq 0 ]; then
    echo "Install finished."
  else
    echo "Install failed. Many .deb packages require Debian/glibc dependencies."
    echo "Use native APK packages for system components where possible."
  fi
fi
echo
echo "Press Enter to close."
read line
' sh "$deb"
""",
        0o755,
    )
    write_file(
        "/usr/share/applications/aurora-open-downloaded-file.desktop",
        """[Desktop Entry]
Type=Application
Name=Aurora Open Downloaded File
Exec=/usr/bin/aurora-open-downloaded-file %f
Terminal=false
NoDisplay=false
MimeType=application/octet-stream;application/x-ms-dos-executable;application/x-msdownload;application/vnd.microsoft.portable-executable;application/vnd.appimage;application/vnd.debian.binary-package;application/x-deb;application/x-executable;application/x-shellscript;text/x-shellscript;
""",
    )
    write_file(
        "/usr/share/applications/aurora-run-exe-file.desktop",
        """[Desktop Entry]
Type=Application
Name=Run Windows EXE
Exec=/usr/bin/aurora-run-exe-file %f
Terminal=false
NoDisplay=false
MimeType=application/octet-stream;application/x-ms-dos-executable;application/x-msdownload;application/vnd.microsoft.portable-executable;
""",
    )
    write_file(
        "/usr/share/applications/aurora-explorer.desktop",
        """[Desktop Entry]
Type=Application
Name=Aurora Explorer
Comment=Browse files, downloads, applications, and mounted drives
Exec=/usr/bin/aurora-explorer
Icon=folder
Terminal=false
Categories=System;FileManager;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-code.desktop",
        """[Desktop Entry]
Type=Application
Name=VSCodium
Comment=AuroraOS 98 code editor
Exec=/usr/bin/aurora-launch-code
Icon=accessories-text-editor
Terminal=false
Categories=Development;IDE;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-unity-hub.desktop",
        """[Desktop Entry]
Type=Application
Name=Unity Hub Installer
Comment=Open the official Unity Hub Linux installer flow
Exec=/usr/bin/aurora-launch-unity-hub
Icon=applications-games
Terminal=false
Categories=Development;GameDevelopment;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-package-center.desktop",
        """[Desktop Entry]
Type=Application
Name=Aurora Package Center
Comment=Install and manage native packages
Exec=/usr/bin/aurora-launch-package-center
Icon=system-software-install
Terminal=false
Categories=System;PackageManager;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-settings.desktop",
        """[Desktop Entry]
Type=Application
Name=Settings
Comment=Configure AuroraOS
Exec=/usr/bin/aurora-launch-settings
Icon=preferences-system
Terminal=false
Categories=Settings;System;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-task-view.desktop",
        """[Desktop Entry]
Type=Application
Name=Task View
Comment=Show desktops and running tasks
Exec=/usr/bin/aurora-launch-task-view
Icon=preferences-desktop
Terminal=false
Categories=System;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-terminal.desktop",
        """[Desktop Entry]
Type=Application
Name=Terminal
Comment=Open a shell
Exec=/usr/bin/aurora-launch-terminal
Icon=utilities-terminal
Terminal=false
Categories=System;TerminalEmulator;AuroraOS98;
""",
    )
    write_file(
        "/usr/share/applications/aurora-run-appimage.desktop",
        """[Desktop Entry]
Type=Application
Name=Run AppImage
Exec=/usr/bin/aurora-run-appimage %f
Terminal=false
NoDisplay=true
MimeType=application/vnd.appimage;application/x-executable;
""",
    )
    write_file(
        "/usr/share/applications/aurora-run-deb.desktop",
        """[Desktop Entry]
Type=Application
Name=Install DEB Package
Exec=/usr/bin/aurora-run-deb-file %f
Terminal=false
NoDisplay=false
MimeType=application/vnd.debian.binary-package;application/x-deb;
""",
    )
    write_file(
        "/usr/share/aurora/mimeapps.list",
        """[Default Applications]
application/x-ms-dos-executable=aurora-run-exe-file.desktop
application/x-msdownload=aurora-run-exe-file.desktop
application/vnd.microsoft.portable-executable=aurora-run-exe-file.desktop
application/octet-stream=aurora-open-downloaded-file.desktop
application/vnd.appimage=aurora-run-appimage.desktop
application/vnd.debian.binary-package=aurora-run-deb.desktop
application/x-deb=aurora-run-deb.desktop
application/x-executable=aurora-open-downloaded-file.desktop
application/x-shellscript=aurora-open-downloaded-file.desktop
text/x-shellscript=aurora-open-downloaded-file.desktop

[Added Associations]
application/octet-stream=aurora-open-downloaded-file.desktop;aurora-run-exe-file.desktop;
application/x-ms-dos-executable=aurora-run-exe-file.desktop;aurora-open-downloaded-file.desktop;
application/x-msdownload=aurora-run-exe-file.desktop;aurora-open-downloaded-file.desktop;
application/vnd.microsoft.portable-executable=aurora-run-exe-file.desktop;aurora-open-downloaded-file.desktop;
application/vnd.debian.binary-package=aurora-run-deb.desktop;aurora-open-downloaded-file.desktop;
application/x-deb=aurora-run-deb.desktop;aurora-open-downloaded-file.desktop;
""",
    )
    write_file(
        "/usr/share/aurora/firefox-user.js",
        """user_pref("browser.download.folderList", 2);
user_pref("browser.download.dir", "/tmp/firefox-home/Downloads");
user_pref("browser.download.useDownloadDir", true);
user_pref("browser.download.alwaysOpenPanel", false);
user_pref("browser.helperApps.neverAsk.saveToDisk", "application/x-ms-dos-executable,application/x-msdownload,application/vnd.microsoft.portable-executable,application/vnd.appimage,application/vnd.debian.binary-package,application/x-deb,application/octet-stream,application/x-executable,application/x-sh");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.startup.page", 0);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.tabs.warnOnClose", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("app.update.enabled", false);
user_pref("extensions.update.enabled", false);
user_pref("signon.rememberSignons", false);
user_pref("media.autoplay.default", 0);
""",
    )
    write_file(
        "/usr/bin/aurora-widgets",
        """#!/bin/sh
while :; do
  now=$(date "+%I:%M:%S %p")
  mem=$(awk '/MemAvailable/ { printf "%d MB available", $2/1024 }' /proc/meminfo 2>/dev/null)
  xmessage -center -buttons "Refresh:1,Explorer:2,Package Center:3,Close:0" -title "AuroraOS Widgets" "AuroraOS 98 Widgets

Clock:   $now
System:  $(uname -r)
Memory:  $mem
Network: QEMU Ethernet / NetworkManager Wi-Fi tool
Storage: initramfs preview" 2>/dev/null
  case "$?" in
    1) continue ;;
    2) /usr/bin/aurora-file-manager /tmp/firefox-home & ;;
    3) /usr/bin/aurora-package-center & ;;
    *) exit 0 ;;
  esac
done
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-task-view",
        """#!/bin/sh
/usr/bin/aurora-click
xmessage -center -buttons "Desktop 1:1,Desktop 2:2,Desktop 3:3,Desktop 4:4,Close:0" -title "AuroraOS Task View" "AuroraOS Task View

Desktop 1  Apps and browser
Desktop 2  Files and downloads
Desktop 3  Development
Desktop 4  System tools

Use the taskbar workspace buttons or choose a desktop here." 2>/dev/null
case "$?" in
  1) jwm -desktop 1 ;;
  2) jwm -desktop 2 ;;
  3) jwm -desktop 3 ;;
  4) jwm -desktop 4 ;;
esac
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-system-monitor",
        """#!/bin/sh
while :; do
  total=$(grep MemTotal /proc/meminfo | tr -s " " | cut -d" " -f2)
  avail=$(grep MemAvailable /proc/meminfo | tr -s " " | cut -d" " -f2)
  used=$((total - avail))
  mem="$((used / 1024)) MB / $((total / 1024)) MB"
  load=$(cut -d" " -f1-3 /proc/loadavg 2>/dev/null)
  ipaddr=$(ip -4 addr show eth0 2>/dev/null | awk "/inet / {print \\$2; exit}")
  [ -n "$ipaddr" ] || ipaddr="not connected"
  xmessage -center -buttons "Refresh:1,Close:0" -title "AuroraOS System Monitor" "AuroraOS System Monitor

CPU
  Load: $load
  Graph:  _..--..__..---.._

RAM
  $mem
  Graph:  __..---...__..--

Network
  eth0: $ipaddr
  QEMU user networking shares the host internet connection.

Storage
  Rootfs: RAM initramfs
  Downloads: /tmp/firefox-home/Downloads

System Info
  AuroraOS 98 preview
  Linux: $(uname -r)
  WM: JWM + Aurora shell tools" 2>/dev/null
  [ "$?" = 1 ] || exit 0
done
""",
        0o755,
    )
    write_file(
        "/usr/bin/aurora-control-center",
        r'''#!/usr/bin/python3
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MODE = sys.argv[1] if len(sys.argv) > 1 else "settings"
HOME = "/tmp/firefox-home"
BG, PANEL, PANEL2 = "#171717", "#202020", "#292929"
TEXT, MUTED, BLUE = "#f4f4f4", "#bdbdbd", "#0878d1"

def run(command, background=True):
    subprocess.run(["/usr/bin/aurora-click"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    if background:
        subprocess.Popen(command)
    else:
        subprocess.run(command)

def read(path, fallback="Unavailable"):
    try:
        with open(path) as handle:
            return handle.read().strip()
    except OSError:
        return fallback

def button(parent, text, command, width=None):
    widget = tk.Button(parent, text=text, command=command, bg="#343434", fg=TEXT,
                       activebackground=BLUE, activeforeground="white", bd=1,
                       relief="solid", padx=16, pady=10, font=("MS W98 UI", 14),
                       cursor="hand2")
    if width:
        widget.configure(width=width)
    return widget

class AuroraApp(tk.Tk):
    def __init__(self, title, size="1180x760"):
        super().__init__()
        self.title(title)
        self.geometry(size)
        self.minsize(920, 620)
        self.configure(bg=BG)
        self.option_add("*Font", ("MS W98 UI", 14))
        self.option_add("*Foreground", TEXT)
        self.option_add("*Background", BG)
        self.bind_all("<Button-1>", lambda _e: subprocess.Popen(
            ["/usr/bin/aurora-click"], stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL), add="+")

    def heading(self, parent, title, subtitle=""):
        tk.Label(parent, text=title, bg=BG, fg=TEXT,
                 font=("MS W98 UI", 27, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        if subtitle:
            tk.Label(parent, text=subtitle, bg=BG, fg=MUTED,
                     font=("MS W98 UI", 14), anchor="w").pack(fill="x", pady=(0, 20))

    def card(self, parent, title):
        frame = tk.Frame(parent, bg=PANEL, bd=1, relief="solid", padx=18, pady=16)
        tk.Label(frame, text=title, bg=PANEL, fg=TEXT,
                 font=("MS W98 UI", 18, "bold"), anchor="w").pack(fill="x", pady=(0, 12))
        return frame

class Settings(AuroraApp):
    pages = ["System", "Network & Wi-Fi", "Sound", "Appearance", "Apps", "Workspaces"]

    def __init__(self):
        super().__init__("Aurora Settings")
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        sidebar = tk.Frame(shell, bg="#151515", width=330, padx=14, pady=18)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="Aurora Settings", bg="#151515", fg=TEXT,
                 font=("MS W98 UI", 19, "bold"), anchor="w").pack(fill="x", padx=8, pady=(4, 22))
        self.content = tk.Frame(shell, bg=BG, padx=30, pady=26)
        self.content.pack(side="left", fill="both", expand=True)
        for name in self.pages:
            button(sidebar, name, lambda n=name: self.show(n)).pack(fill="x", pady=4)
        self.show("System")

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def row(self, parent, name, value):
        line = tk.Frame(parent, bg=PANEL, pady=8)
        line.pack(fill="x")
        tk.Label(line, text=name, bg=PANEL, fg=MUTED, width=20, anchor="w").pack(side="left")
        tk.Label(line, text=value, bg=PANEL, fg=TEXT, anchor="w").pack(side="left", fill="x", expand=True)

    def show(self, name):
        self.clear()
        getattr(self, "page_" + name.lower().replace(" & ", "_").replace(" ", "_"))()

    def page_system(self):
        self.heading(self.content, "System", "AuroraOS 98 device information and quick actions")
        card = self.card(self.content, "About this computer")
        card.pack(fill="x", pady=(0, 16))
        self.row(card, "Operating system", "AuroraOS 98 Linux preview")
        self.row(card, "Kernel", os.uname().release)
        self.row(card, "Computer", os.uname().machine + " QEMU PC")
        mem = read("/proc/meminfo").splitlines()[0].replace("MemTotal:", "").strip()
        self.row(card, "Memory", mem)
        actions = self.card(self.content, "Quick actions")
        actions.pack(fill="x")
        for label, cmd in [("Open Explorer", ["/usr/bin/aurora-explorer"]),
                           ("Open Package Center", ["/usr/bin/aurora-package-center"]),
                           ("Open Terminal", ["/usr/bin/aurora-terminal"])]:
            button(actions, label, lambda c=cmd: run(c)).pack(fill="x", pady=4)

    def page_network_wifi(self):
        self.heading(self.content, "Network & Wi-Fi", "Connections provided by NetworkManager")
        card = self.card(self.content, "Connection status")
        card.pack(fill="x", pady=(0, 16))
        try:
            status = subprocess.check_output(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], text=True).strip()
        except Exception:
            status = "NetworkManager status unavailable"
        tk.Label(card, text=status or "No network devices", bg=PANEL, fg=TEXT,
                 justify="left", anchor="w").pack(fill="x")
        actions = tk.Frame(card, bg=PANEL)
        actions.pack(fill="x", pady=(16, 0))
        button(actions, "Refresh connection", lambda: run(["sh", "-c", "ip link set eth0 up; udhcpc -i eth0 -q -t 5 -n"])).pack(side="left", padx=(0, 10))
        button(actions, "Scan Wi-Fi", self.scan_wifi).pack(side="left")
        note = self.card(self.content, "QEMU networking")
        note.pack(fill="x")
        tk.Label(note, text="QEMU shares the Mac internet connection through a virtual Ethernet adapter.\nReal Wi-Fi networks appear on Raspberry Pi, laptops, or with a USB Wi-Fi adapter passed through.",
                 bg=PANEL, fg=MUTED, justify="left", anchor="w").pack(fill="x")

    def scan_wifi(self):
        try:
            result = subprocess.check_output(["nmcli", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"], text=True).strip()
        except Exception:
            result = "No Wi-Fi radio is available in this QEMU machine."
        messagebox.showinfo("Available Wi-Fi networks", result or "No networks found")

    def page_sound(self):
        self.heading(self.content, "Sound", "Output volume and interface sounds")
        card = self.card(self.content, "Output")
        card.pack(fill="x")
        self.row(card, "Device", "QEMU ES1370 / host audio")
        scale = tk.Scale(card, from_=0, to=100, orient="horizontal", length=600,
                         bg=PANEL, fg=TEXT, troughcolor="#444", highlightthickness=0)
        scale.set(80)
        scale.pack(fill="x", pady=12)
        button(card, "Play test sound", lambda: run(["/usr/bin/aurora-click"])).pack(anchor="w")

    def page_appearance(self):
        self.heading(self.content, "Appearance", "Desktop scale, wallpaper, and window style")
        card = self.card(self.content, "Current appearance")
        card.pack(fill="x")
        self.row(card, "Wallpaper", "/usr/share/aurora/wallpaper.jpg")
        self.row(card, "Interface scale", "Large (144 DPI)")
        self.row(card, "Window manager", "JWM")
        self.row(card, "Theme", "Aurora dark classic")

    def page_apps(self):
        self.heading(self.content, "Apps", "Installed applications and file handlers")
        card = self.card(self.content, "Default applications")
        card.pack(fill="x")
        for app in ["Firefox ESR", "VSCodium", "PCManFM Explorer", "Wine", "Python + pip", "Aurora Package Center"]:
            self.row(card, app, "Installed")
        button(self.content, "Open Package Center", lambda: run(["/usr/bin/aurora-package-center"])).pack(anchor="w", pady=16)

    def page_workspaces(self):
        self.heading(self.content, "Workspaces", "Four independent desktops for organizing windows")
        grid = tk.Frame(self.content, bg=BG)
        grid.pack(fill="both", expand=True)
        for index in range(1, 5):
            preview = tk.Frame(grid, bg=PANEL2, bd=2, relief="solid", width=360, height=190)
            preview.grid(row=(index-1)//2, column=(index-1)%2, padx=10, pady=10, sticky="nsew")
            preview.grid_propagate(False)
            tk.Label(preview, text=f"Desktop {index}", bg=PANEL2, fg=TEXT,
                     font=("MS W98 UI", 20, "bold")).pack(expand=True)
            button(preview, "Switch", lambda i=index: run(["jwm", "-desktop", str(i)])).pack(pady=14)
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

class PackageCenter(AuroraApp):
    apps = [
        ("Firefox ESR", "Web browser", "Installed", ["/usr/bin/aurora-firefox"]),
        ("VSCodium", "VS Code-compatible developer editor", "Installed", ["/usr/bin/aurora-code"]),
        ("Explorer", "Graphical file manager", "Installed", ["/usr/bin/aurora-explorer"]),
        ("Python + pip", "Programming runtime", "Installed", ["/usr/bin/aurora-terminal"]),
        ("Windows EXE Support", "Wine compatibility layer", "Installed", ["/usr/bin/aurora-run-exe"]),
        ("Unity Hub", "Official proprietary installer", "Get", ["/usr/bin/aurora-unity-hub"]),
    ]
    def __init__(self):
        super().__init__("Aurora Package Center")
        body = tk.Frame(self, bg=BG, padx=30, pady=26)
        body.pack(fill="both", expand=True)
        self.heading(body, "Package Center", "Open installed software or add Linux packages")
        search = tk.Entry(body, bg="#2a2a2a", fg=TEXT, insertbackground=TEXT, relief="solid", bd=1)
        search.insert(0, "Search applications")
        search.pack(fill="x", ipady=10, pady=(0, 16))
        listing = tk.Frame(body, bg=BG)
        listing.pack(fill="both", expand=True)
        for row, (name, description, state, cmd) in enumerate(self.apps):
            card = tk.Frame(listing, bg=PANEL, bd=1, relief="solid", padx=16, pady=12)
            card.grid(row=row, column=0, sticky="ew", pady=5)
            tk.Label(card, text=name, bg=PANEL, fg=TEXT, font=("MS W98 UI", 17, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
            tk.Label(card, text=description, bg=PANEL, fg=MUTED, anchor="w").grid(row=1, column=0, sticky="w")
            button(card, "Open" if state == "Installed" else state, lambda c=cmd: run(c), width=10).grid(row=0, column=1, rowspan=2, padx=8)
            card.grid_columnconfigure(0, weight=1)
        listing.grid_columnconfigure(0, weight=1)
        button(body, "Install custom APK package", self.custom).pack(anchor="e", pady=(14, 0))
    def custom(self):
        dialog = tk.Toplevel(self)
        dialog.title("Install Linux package")
        dialog.geometry("560x220")
        dialog.configure(bg=PANEL)
        tk.Label(dialog, text="Alpine package name", bg=PANEL, fg=TEXT, font=("MS W98 UI", 18, "bold")).pack(anchor="w", padx=22, pady=(22, 10))
        entry = tk.Entry(dialog, bg="#111", fg=TEXT, insertbackground=TEXT)
        entry.pack(fill="x", padx=22, ipady=8)
        button(dialog, "Install", lambda: run(["/usr/bin/aurora-package-install-custom", entry.get()])).pack(anchor="e", padx=22, pady=18)

class TaskView(AuroraApp):
    def __init__(self):
        super().__init__("Task View", "1120x650")
        body = tk.Frame(self, bg=BG, padx=28, pady=26)
        body.pack(fill="both", expand=True)
        self.heading(body, "Task View", "Choose a desktop")
        grid = tk.Frame(body, bg=BG)
        grid.pack(fill="both", expand=True)
        labels = ["Apps & browser", "Files & downloads", "Development", "System tools"]
        for index, label in enumerate(labels, 1):
            preview = tk.Frame(grid, bg=PANEL2, bd=2, relief="solid", width=500, height=210)
            preview.grid(row=(index-1)//2, column=(index-1)%2, padx=10, pady=10, sticky="nsew")
            preview.grid_propagate(False)
            tk.Label(preview, text=f"Desktop {index}", bg=PANEL2, fg=TEXT, font=("MS W98 UI", 22, "bold")).pack(pady=(40, 8))
            tk.Label(preview, text=label, bg=PANEL2, fg=MUTED).pack()
            button(preview, "Switch desktop", lambda i=index: (run(["jwm", "-desktop", str(i)]), self.destroy())).pack(pady=20)
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

class Monitor(AuroraApp):
    def __init__(self):
        super().__init__("Aurora System Monitor", "920x650")
        self.body = tk.Frame(self, bg=BG, padx=30, pady=26)
        self.body.pack(fill="both", expand=True)
        self.heading(self.body, "System Monitor", "Live Linux system status")
        self.labels = {}
        for key in ["CPU load", "Memory", "Network", "Storage", "Kernel"]:
            card = self.card(self.body, key)
            card.pack(fill="x", pady=5)
            self.labels[key] = tk.Label(card, bg=PANEL, fg=TEXT, anchor="w")
            self.labels[key].pack(fill="x")
        self.refresh()
    def refresh(self):
        load = read("/proc/loadavg").split()[:3]
        info = read("/proc/meminfo").splitlines()
        vals = {line.split(":", 1)[0]: line.split(":", 1)[1].strip() for line in info if ":" in line}
        total = int(vals.get("MemTotal", "0 kB").split()[0])
        available = int(vals.get("MemAvailable", "0 kB").split()[0])
        disk = shutil.disk_usage("/")
        self.labels["CPU load"].configure(text="  ".join(load))
        self.labels["Memory"].configure(text=f"{(total-available)//1024} MB used / {total//1024} MB")
        self.labels["Network"].configure(text="QEMU Ethernet through host NAT")
        self.labels["Storage"].configure(text=f"{disk.used//(1024**2)} MB used / {disk.total//(1024**2)} MB")
        self.labels["Kernel"].configure(text=os.uname().release)
        self.after(1500, self.refresh)

if MODE == "settings":
    app = Settings()
elif MODE == "packages":
    app = PackageCenter()
elif MODE == "taskview":
    app = TaskView()
else:
    app = Monitor()
app.mainloop()
''',
        0o755,
    )
    for path, mode in (
        ("/usr/bin/aurora-settings", "settings"),
        ("/usr/bin/aurora-settings-network", "settings"),
        ("/usr/bin/aurora-wifi-ui", "settings"),
        ("/usr/bin/aurora-package-center", "packages"),
        ("/usr/bin/aurora-task-view", "taskview"),
        ("/usr/bin/aurora-system-monitor", "monitor"),
        ("/usr/bin/aurora-widgets", "monitor"),
    ):
        write_file(path, f'''#!/bin/sh
export HOME=/tmp/firefox-home
export DISPLAY="${{DISPLAY:-:0}}"
export XDG_RUNTIME_DIR=/run/user/0
exec /usr/bin/aurora-control-center {mode}
''', 0o755)
    def menu_command(name: str, status: str) -> str:
        if name == "Wi-Fi Connection":
            return "/usr/bin/aurora-launch-settings"
        if name == "Settings":
            return "/usr/bin/aurora-launch-settings"
        if name == "Control Panel":
            return "/usr/bin/aurora-launch-settings"
        if name == "Package Center":
            return "/usr/bin/aurora-launch-package-center"
        if name == "Firefox":
            return "/usr/bin/aurora-launch-firefox"
        if name == "Run Windows EXE":
            return with_click("/usr/bin/aurora-run-exe")
        if name in {"File Explorer", "Explorer"}:
            return "/usr/bin/aurora-launch-explorer"
        if name in {"VS Code", "Code Editor", "VSCodium"}:
            return "/usr/bin/aurora-launch-code"
        if name == "Unity Hub Installer":
            return "/usr/bin/aurora-launch-unity-hub"
        if name in {"Aurora Terminal", "Terminal"}:
            return "/usr/bin/aurora-launch-terminal"
        if name == "Task View":
            return "/usr/bin/aurora-launch-task-view"
        if name == "System Monitor":
            return with_click("/usr/bin/aurora-system-monitor")
        if name == "Install DEB":
            return with_click("/usr/bin/aurora-app-info 'Install DEB' 'Double-click a .deb file in Explorer to install it.'")
        return with_click(f"/usr/bin/aurora-app-info {shell_quote(name)} {shell_quote(status)}")

    menu_items = "\n".join(
        f"""    <item label="{name}">
      <action name="Execute"><command>{menu_command(name, status)}</command></action>
    </item>"""
        for _, name, _, status in apps
    )
    write_file(
        "/etc/xdg/openbox/menu.xml",
        f"""<?xml version="1.0" encoding="UTF-8"?>
<openbox_menu xmlns="http://openbox.org/3.4/menu">
  <menu id="root-menu" label="AuroraOS 98">
    <item label="Aurora Package Center">
      <action name="Execute"><command>/usr/bin/aurora-open-package-center</command></action>
    </item>
    <item label="Show All Apps">
      <action name="Execute"><command>/usr/bin/aurora-show-apps</command></action>
    </item>
{menu_items}
    <separator />
    <item label="Exit QEMU Session">
      <action name="Exit" />
    </item>
  </menu>
</openbox_menu>
""",
    )
    primary_menu_names = {"Explorer", "Settings", "Task View", "Package Center", "Terminal"}
    jwm_items = "\n".join(
        f"""      <Program label="{name}">{menu_command(name, status)}</Program>"""
        for _, name, _, status in apps if name not in primary_menu_names
    )
    write_file(
        "/etc/jwm/aurora.jwmrc",
        f"""<?xml version="1.0"?>
<JWM>
  <RootMenu onroot="12">
    <Program label="Explorer">/usr/bin/aurora-launch-explorer</Program>
    <Program label="Settings">/usr/bin/aurora-launch-settings</Program>
    <Program label="Task View">/usr/bin/aurora-launch-task-view</Program>
    <Program label="Package Center">/usr/bin/aurora-launch-package-center</Program>
    <Program label="Terminal">/usr/bin/aurora-launch-terminal</Program>
    <Separator />
{jwm_items}
    <Separator />
    <Exit label="Shut Down AuroraOS 98" confirm="false" />
  </RootMenu>

  <Tray x="0" y="-1" height="82" autohide="false">
    <TrayButton label="Start">root:1</TrayButton>
    <TrayButton label="Task View">exec:/usr/bin/aurora-launch-task-view</TrayButton>
    <TrayButton label="Explorer">exec:/usr/bin/aurora-launch-explorer</TrayButton>
    <TrayButton label="Firefox">exec:/usr/bin/aurora-launch-firefox</TrayButton>
    <TrayButton label="Code">exec:/usr/bin/aurora-launch-code</TrayButton>
    <TrayButton label="Settings">exec:/usr/bin/aurora-launch-settings</TrayButton>
    <TrayButton label="Store">exec:/usr/bin/aurora-launch-package-center</TrayButton>
    <TaskList maxwidth="620" />
    <TrayButton label="1">exec:jwm -desktop 1</TrayButton>
    <TrayButton label="2">exec:jwm -desktop 2</TrayButton>
    <TrayButton label="3">exec:jwm -desktop 3</TrayButton>
    <TrayButton label="4">exec:jwm -desktop 4</TrayButton>
    <Dock />
    <Clock format="%I:%M %p">xclock</Clock>
  </Tray>

  <Desktops width="4" height="1" />
  <WindowStyle>
    <Font>MS W98 UI-18</Font>
    <Width>2</Width>
    <Height>46</Height>
    <Active>
      <Text>#ffffff</Text>
      <Title>#2d2d2d:#202020</Title>
      <Outline>#1f1f1f</Outline>
    </Active>
    <Inactive>
      <Text>#d0d0d0</Text>
      <Title>#2d2d2d:#2d2d2d</Title>
      <Outline>#1f1f1f</Outline>
    </Inactive>
  </WindowStyle>
  <TaskListStyle>
    <Font>MS W98 UI-18</Font>
    <ActiveForeground>#ffffff</ActiveForeground>
    <ActiveBackground>#0b4ba5</ActiveBackground>
    <Foreground>#f3f3f3</Foreground>
    <Background>#1f1f1f</Background>
  </TaskListStyle>
  <TrayStyle>
    <Font>MS W98 UI-18</Font>
    <Background>#1f1f1f</Background>
    <Foreground>#ffffff</Foreground>
  </TrayStyle>
  <MenuStyle>
    <Font>MS W98 UI-18</Font>
    <Foreground>#f3f3f3</Foreground>
    <Background>#202020</Background>
    <ActiveForeground>#ffffff</ActiveForeground>
    <ActiveBackground>#0078d7</ActiveBackground>
  </MenuStyle>
  <Background type="solid">#111111</Background>
  <FocusModel>click</FocusModel>
  <Key key="F8">exec:/usr/bin/aurora-launch-code</Key>
  <Key key="F9">exec:/usr/bin/aurora-launch-settings</Key>
  <ButtonClose>X</ButtonClose>
  <ButtonMax>□</ButtonMax>
  <ButtonMin>_</ButtonMin>
</JWM>
""",
    )
    applications = ROOTFS / "usr" / "share" / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    for category, name, command, status in apps:
        desktop_id = command.replace("/", "-")
        if (applications / f"{desktop_id}.desktop").exists():
            continue
        write_file(
            f"/usr/share/applications/{desktop_id}.desktop",
            f"""[Desktop Entry]
Type=Application
Name={name}
Comment=AuroraOS 98 {category} launcher
Exec=/usr/bin/aurora-app-info {shell_quote(name)} {shell_quote(status)}
Terminal=false
Categories=AuroraOS98;{category.replace(" ", "")};
""",
        )


def force_busybox_applets() -> None:
    applets = [
        "awk",
        "cat",
        "chmod",
        "clear",
        "cp",
        "cut",
        "date",
        "httpd",
        "ifconfig",
        "ip",
        "kill",
        "ln",
        "ls",
        "grep",
        "head",
        "mkdir",
        "mknod",
        "mdev",
        "modprobe",
        "mount",
        "mv",
        "pidof",
        "ping",
        "printf",
        "route",
        "sed",
        "sh",
        "sleep",
        "touch",
        "tr",
        "udhcpc",
        "uname",
        "wget",
    ]
    busybox = ROOTFS / "bin" / "busybox"
    if not busybox.exists():
        raise RuntimeError("busybox is missing from Firefox rootfs")
    for applet in applets:
        link = ROOTFS / "bin" / applet
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to("busybox")


def configure_rootfs() -> None:
    install_vscodium_flac_compat()
    force_busybox_applets()
    normalize_kernel_modules(ROOTFS / "lib" / "modules")
    write_app_surface()
    write_file(
        "/etc/apk/repositories",
        """https://dl-cdn.alpinelinux.org/alpine/edge/main
https://dl-cdn.alpinelinux.org/alpine/edge/community
""",
    )
    large_cursor = """#define aurora_cursor_width 32
#define aurora_cursor_height 32
#define aurora_cursor_x_hot 1
#define aurora_cursor_y_hot 1
static unsigned char aurora_cursor_bits[] = {
  0x01,0x00,0x00,0x00,
  0x03,0x00,0x00,0x00,
  0x07,0x00,0x00,0x00,
  0x0f,0x00,0x00,0x00,
  0x1f,0x00,0x00,0x00,
  0x3f,0x00,0x00,0x00,
  0x7f,0x00,0x00,0x00,
  0xff,0x00,0x00,0x00,
  0xff,0x01,0x00,0x00,
  0xff,0x03,0x00,0x00,
  0xff,0x07,0x00,0x00,
  0xff,0x0f,0x00,0x00,
  0xff,0x1f,0x00,0x00,
  0xff,0x3f,0x00,0x00,
  0xff,0x7f,0x00,0x00,
  0xff,0xff,0x00,0x00,
  0xff,0x1f,0x00,0x00,
  0xbf,0x0f,0x00,0x00,
  0x9f,0x0f,0x00,0x00,
  0x8f,0x0f,0x00,0x00,
  0x87,0x0f,0x00,0x00,
  0x83,0x0f,0x00,0x00,
  0x81,0x0f,0x00,0x00,
  0x80,0x0f,0x00,0x00,
  0x00,0x0f,0x00,0x00,
  0x00,0x0f,0x00,0x00,
  0x00,0x0f,0x00,0x00,
  0x00,0x06,0x00,0x00,
  0x00,0x00,0x00,0x00,
  0x00,0x00,0x00,0x00,
  0x00,0x00,0x00,0x00,
  0x00,0x00,0x00,0x00
};
"""
    write_file("/usr/share/aurora/cursors/arrow.xbm", large_cursor)
    write_file("/usr/share/aurora/cursors/arrow-mask.xbm", large_cursor.replace("aurora_cursor_bits", "aurora_cursor_mask_bits"))
    write_file(
        "/etc/X11/xorg.conf",
        """Section "Device"
    Identifier "Framebuffer"
    Driver "fbdev"
    Option "fbdev" "/dev/fb0"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device "Framebuffer"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "1280x800" "1366x768" "1024x768" "1920x1080" "2560x1440" "3840x2160"
    EndSubSection
EndSection
""",
    )
    write_file(
        "/root/.xinitrc",
        """#!/bin/sh
export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export MOZ_ENABLE_WAYLAND=0
export MOZ_DISABLE_CONTENT_SANDBOX=1
export GDK_DPI_SCALE=1.25
export GDK_SCALE=1
export QT_SCALE_FACTOR=1.25
export XCURSOR_THEME=AuroraPixel
export XCURSOR_SIZE=48
printf 'Xft.dpi: 144\nXcursor.size: 48\nXcursor.theme: AuroraPixel\n' >/tmp/firefox-home/.Xresources
xrdb -merge /tmp/firefox-home/.Xresources 2>/dev/null || true
feh --bg-fill /usr/share/aurora/wallpaper.jpg >/tmp/aurora-xinit-wallpaper.log 2>&1 || true
exec jwm -f /etc/jwm/aurora.jwmrc
""",
        0o755,
    )
    write_file(
        "/init",
        """#!/bin/busybox sh
export PATH=/sbin:/bin:/usr/sbin:/usr/bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || true
mkdir -p /dev/pts /dev/shm /run /tmp /root /var/log /var/lib/dbus
mount -t devpts devpts /dev/pts 2>/dev/null || true
mount -t tmpfs tmpfs /dev/shm 2>/dev/null || true
mount -t tmpfs tmpfs /run 2>/dev/null || true
mount -t tmpfs tmpfs /tmp 2>/dev/null || true
mkdir -p /run/user/0 /run/dbus /tmp/.X11-unix /tmp/firefox-home /tmp/firefox-home/profile /tmp/firefox-home/Downloads /tmp/firefox-home/Desktop /tmp/firefox-home/Documents /tmp/firefox-home/Applications /tmp/firefox-home/Pictures /tmp/firefox-home/.config /tmp/firefox-home/.local/share/applications /var/log /var/lib/dbus
chmod 700 /run/user/0
chmod 700 /tmp/firefox-home /tmp/firefox-home/profile
cat >/tmp/firefox-home/.gtkrc-2.0 <<'EOF'
gtk-theme-name="AuroraDark"
gtk-font-name="MS W98 UI 14"
gtk-icon-theme-name="Adwaita"
EOF
mkdir -p /tmp/firefox-home/.config/gtk-3.0
cat >/tmp/firefox-home/.config/gtk-3.0/settings.ini <<'EOF'
[Settings]
gtk-theme-name=Adwaita-dark
gtk-font-name=MS W98 UI 14
gtk-icon-theme-name=Adwaita
EOF
cp /usr/share/aurora/mimeapps.list /tmp/firefox-home/.local/share/applications/mimeapps.list 2>/dev/null || true
cp /usr/share/aurora/mimeapps.list /tmp/firefox-home/.config/mimeapps.list 2>/dev/null || true
cp /usr/share/aurora/firefox-user.js /tmp/firefox-home/profile/user.js 2>/dev/null || true
cp /usr/share/applications/aurora-explorer.desktop /tmp/firefox-home/Desktop/Aurora-Explorer.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-code.desktop /tmp/firefox-home/Desktop/Code-Editor.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-unity-hub.desktop /tmp/firefox-home/Desktop/Unity-Hub-Installer.desktop 2>/dev/null || true
cp /usr/share/applications/firefox-esr.desktop /tmp/firefox-home/Desktop/Firefox.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-settings.desktop /tmp/firefox-home/Desktop/Settings.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-task-view.desktop /tmp/firefox-home/Desktop/Task-View.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-terminal.desktop /tmp/firefox-home/Desktop/Terminal.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-package-center.desktop /tmp/firefox-home/Desktop/Package-Center.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-explorer.desktop /tmp/firefox-home/Applications/Aurora-Explorer.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-code.desktop /tmp/firefox-home/Applications/Code-Editor.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-unity-hub.desktop /tmp/firefox-home/Applications/Unity-Hub-Installer.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-settings.desktop /tmp/firefox-home/Applications/Settings.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-task-view.desktop /tmp/firefox-home/Applications/Task-View.desktop 2>/dev/null || true
cp /usr/share/applications/aurora-terminal.desktop /tmp/firefox-home/Applications/Terminal.desktop 2>/dev/null || true
chmod +x /tmp/firefox-home/Desktop/*.desktop /tmp/firefox-home/Applications/*.desktop 2>/dev/null || true
update-desktop-database /usr/share/applications >/dev/console 2>&1 || true
mkdir -p /lib/apk/db /var/cache/apk /etc/apk
touch /lib/apk/db/installed /lib/apk/db/world
chmod 1777 /tmp /tmp/.X11-unix /dev/shm
mdev -s 2>/dev/null || true
modprobe bochs >/dev/console 2>&1 || true
modprobe cirrus-qemu >/dev/console 2>&1 || true
modprobe virtio-gpu >/dev/console 2>&1 || true
modprobe fbdev 2>/dev/null || true
modprobe evdev 2>/dev/null || true
modprobe mousedev 2>/dev/null || true
modprobe psmouse 2>/dev/null || true
modprobe hid 2>/dev/null || true
modprobe hid-generic 2>/dev/null || true
modprobe usbhid 2>/dev/null || true
modprobe usbmouse 2>/dev/null || true
modprobe snd 2>/dev/null || true
modprobe snd-pcm 2>/dev/null || true
modprobe snd-timer 2>/dev/null || true
modprobe snd-ac97-codec 2>/dev/null || true
modprobe snd-ens1371 2>/dev/null || true
modprobe e1000 2>/dev/null || true
modprobe e1000e 2>/dev/null || true
modprobe virtio_net 2>/dev/null || true
modprobe af_packet 2>/dev/null || true
modprobe cfg80211 2>/dev/null || true
modprobe mac80211 2>/dev/null || true
for i in 1 2 3; do
    [ -e /sys/class/net/eth0 ] && break
    mdev -s 2>/dev/null || true
    sleep 1
done
[ -e /dev/fb0 ] || mknod /dev/fb0 c 29 0
dbus-uuidgen --ensure 2>/dev/null || true
mkdir -p /run/dbus /run/NetworkManager /var/lib/NetworkManager
dbus-daemon --system --fork --nopidfile 2>/dev/null || true
if command -v NetworkManager >/dev/null 2>&1; then
    NetworkManager --no-daemon >/var/log/NetworkManager.log 2>&1 &
    sleep 1
    nmcli device connect eth0 >/dev/console 2>&1 || true
    nmcli radio wifi on >/dev/console 2>&1 || true
fi
netdev=eth0
[ -e /sys/class/net/"$netdev" ] || netdev=$(ls /sys/class/net 2>/dev/null | grep -v '^lo$' | head -n 1)
if [ -n "$netdev" ]; then
    ip link set "$netdev" up >/dev/console 2>&1 || true
    udhcpc -i "$netdev" -s /usr/share/udhcpc/default.script -q -t 8 -n >/dev/console 2>&1 || true
fi
printf 'nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n' >/etc/resolv.conf
printf 'AuroraOS 98: starting real Firefox ESR on Xorg\\n' >/dev/console
export HOME=/tmp/firefox-home
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/0
export XCURSOR_SIZE=48
export XCURSOR_THEME=AuroraPixel
export GDK_DPI_SCALE=1.25
export GDK_SCALE=1
export QT_SCALE_FACTOR=1.25
export MOZ_ENABLE_WAYLAND=0
export MOZ_DISABLE_CONTENT_SANDBOX=1
/usr/bin/Xorg :0 -config /etc/X11/xorg.conf -br -noreset -nolisten tcp vt1 >/var/log/Xorg.0.log 2>&1 &
xpid=$!
sleep 2
if ! kill -0 "$xpid" 2>/dev/null; then
    printf 'AuroraOS 98: Xorg failed\\n' >/dev/console
    cat /var/log/Xorg.0.log >/dev/console 2>/dev/null || true
    exec sh
fi
printf 'AuroraOS 98: Xorg is running\\n' >/dev/console
if command -v dbus-launch >/dev/null 2>&1; then
    dbus-launch --sh-syntax >/tmp/dbus-session.env 2>/var/log/dbus-launch.log &
    dbuslaunchpid=$!
    sleep 1
    if kill -0 "$dbuslaunchpid" 2>/dev/null; then
        kill "$dbuslaunchpid" 2>/dev/null || true
    fi
    [ -s /tmp/dbus-session.env ] && . /tmp/dbus-session.env
fi
xsetroot -display :0 -solid '#111111' >/dev/console 2>&1 || true
printf 'Xft.dpi: 144\nXcursor.size: 48\nXcursor.theme: AuroraPixel\n' >/tmp/firefox-home/.Xresources
xrdb -display :0 -merge /tmp/firefox-home/.Xresources >/dev/console 2>&1 || true
xsetroot -display :0 -cursor_name left_ptr >/dev/console 2>&1 || true
xmodmap -display :0 -e "clear mod4" -e "keycode 133 = Control_L NoSymbol Control_L" -e "keycode 134 = Control_R NoSymbol Control_R" -e "add Control = Control_L Control_R" >/var/log/xmodmap.log 2>&1 || true
jwm -display :0 -f /etc/jwm/aurora.jwmrc >/var/log/jwm.log 2>&1 &
sleep 1
feh --bg-fill /usr/share/aurora/wallpaper.jpg >/var/log/wallpaper.log 2>&1 || true
DISPLAY=:0 /usr/bin/aurora-desktop-icons >/var/log/aurora-desktop-icons.log 2>&1 &
sleep 1
alsactl init >/var/log/alsa-init.log 2>&1 || true
amixer set Master unmute 80% >/dev/console 2>&1 || true
amixer set PCM unmute 80% >/dev/console 2>&1 || true
printf 'AuroraOS 98: usable JWM desktop is ready\\n' >/dev/console
while true; do
    sleep 60
done
""",
        0o755,
    )


def normalize_for_cpio() -> None:
    for path in ROOTFS.rglob("*"):
        if path.is_symlink():
            continue
        try:
            mode = path.stat().st_mode
        except FileNotFoundError:
            continue
        if path.is_dir():
            path.chmod(mode | 0o755)
        else:
            path.chmod(mode | 0o644)


def build_cpio() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    normalize_for_cpio()
    find = subprocess.Popen(["find", "."], cwd=ROOTFS, stdout=subprocess.PIPE)
    cpio = subprocess.Popen(["cpio", "-o", "-H", "newc", "-R", "0:0"], cwd=ROOTFS, stdin=find.stdout, stdout=subprocess.PIPE)
    compressor = subprocess.Popen(["lz4", "-l", "-1", "-q"], stdin=cpio.stdout, stdout=open(OUT, "wb"))
    assert find.stdout and cpio.stdout
    find.stdout.close()
    cpio.stdout.close()
    if find.wait() or cpio.wait() or compressor.wait():
        raise RuntimeError("failed to build Firefox initramfs")
    print(f"Wrote {OUT}")


def build() -> None:
    if not MODULES_SRC.exists():
        raise RuntimeError("run make linux-qemu first so kernel modules are available")
    by_name, provides = parse_indexes()
    packages = resolve_packages(by_name, provides)
    total = sum(int(pkg.get("S", "0")) for pkg in packages)
    print(f"Resolved {len(packages)} APKs, download size about {total // (1024 * 1024)} MB")
    paths = download_packages(packages)
    reset_rootfs()
    extract_packages(paths)
    configure_rootfs()
    build_cpio()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--pack-existing", action="store_true")
    args = parser.parse_args()
    if args.build:
        build()
        return 0
    if args.pack_existing:
        configure_rootfs()
        build_cpio()
        return 0
    parser.error("use --build or --pack-existing")


if __name__ == "__main__":
    raise SystemExit(main())
