#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "full-chromium"
IMAGES = [
    OUT / "images" / "rootfs.ext4",
    OUT / "images" / "sdcard.img",
    OUT / "auroraos98-chromium.qcow2",
]
KERNELS = [
    OUT / "images" / "bzImage",
    OUT / "images" / "vmlinuz",
]


def existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def main() -> int:
    qemu = shutil.which("qemu-system-x86_64")
    if not qemu:
        print("ERROR: qemu-system-x86_64 is not installed.", file=sys.stderr)
        return 2

    image = existing(IMAGES)
    kernel = existing(KERNELS)
    if not image or not kernel:
        print("ERROR: full Chromium image is not built yet.", file=sys.stderr)
        print("Run: make full-chromium-image", file=sys.stderr)
        print(f"Expected image under: {OUT / 'images'}", file=sys.stderr)
        return 3

    cmd = [
        qemu,
        "-m",
        "4096M",
        "-smp",
        "4",
        "-kernel",
        str(kernel),
        "-append",
        "root=/dev/vda rw console=tty0 quiet",
        "-drive",
        f"file={image},format=raw,if=virtio",
        "-device",
        "virtio-vga-gl",
        "-display",
        "cocoa,gl=on",
        "-device",
        "usb-ehci,id=ehci",
        "-device",
        "usb-tablet,bus=ehci.0",
        "-netdev",
        "user,id=net0",
        "-device",
        "virtio-net-pci,netdev=net0",
        "-monitor",
        "none",
    ]
    print("+ " + " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
