#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import shutil
import tarfile
import urllib.request
from pathlib import Path

import build_firefox_qemu as image


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build" / "firefox-qemu-arm64"
KERNEL_ROOT = BASE / "linux-virt"
KERNEL_APK = BASE / "kernel-apks"
MAIN_REPO = "https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def ensure_kernel() -> Path:
    data = fetch(f"{MAIN_REPO}/APKINDEX.tar.gz")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.extractfile("APKINDEX")
        if member is None:
            raise RuntimeError("Alpine index did not contain APKINDEX")
        text = member.read().decode()
    package = None
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(":", 1) for line in block.splitlines() if len(line) > 2 and line[1] == ":")
        if fields.get("P") == "linux-virt":
            package = fields
            break
    if package is None:
        raise RuntimeError("Alpine aarch64 linux-virt package was not found")

    filename = f"linux-virt-{package['V']}.apk"
    KERNEL_APK.mkdir(parents=True, exist_ok=True)
    apk = KERNEL_APK / filename
    if not apk.exists():
        print(f"downloading {filename}")
        apk.write_bytes(fetch(f"{MAIN_REPO}/{filename}"))

    if KERNEL_ROOT.exists():
        shutil.rmtree(KERNEL_ROOT)
    KERNEL_ROOT.mkdir(parents=True)
    image.run(["bsdtar", "-xf", str(apk), "-C", str(KERNEL_ROOT)])
    kernel = KERNEL_ROOT / "boot" / "vmlinuz-virt"
    if not kernel.exists():
        matches = sorted((KERNEL_ROOT / "boot").glob("vmlinuz-*"))
        if not matches:
            raise RuntimeError("linux-virt did not contain an ARM64 kernel")
        kernel = matches[0]
    return kernel


def configure_builder() -> None:
    image.BASE = BASE
    image.APK_DIR = BASE / "apks"
    image.ROOTFS = BASE / "rootfs"
    image.OUT = BASE / "aurora-firefox-initramfs.cpio.lz4"
    image.MODULES_SRC = KERNEL_ROOT / "lib" / "modules"
    image.TARGET_ARCH = "aarch64"
    image.VSCODIUM_FLAC_COMPAT_URL = (
        "https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/libflac-1.4.3-r1.apk"
    )
    image.REPOS = {
        repo: f"https://dl-cdn.alpinelinux.org/alpine/edge/{repo}/aarch64"
        for repo in ("main", "community", "testing")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the hardware-accelerated ARM64 AuroraOS QEMU image")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--pack-existing", action="store_true")
    args = parser.parse_args()
    if not args.build and not args.pack_existing:
        parser.error("use --build or --pack-existing")
    kernel = ensure_kernel()
    configure_builder()
    if args.build:
        image.build()
    else:
        image.install_debian_runtime()
        image.configure_rootfs()
        image.build_cpio()
    target = BASE / "vmlinuz-virt"
    shutil.copy2(kernel, target)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
