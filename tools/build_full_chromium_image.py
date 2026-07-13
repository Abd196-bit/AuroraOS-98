#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFCONFIG = ROOT / "distro" / "buildroot" / "x86_64_chromium_defconfig"
OUT = ROOT / "build" / "full-chromium"
IMAGE = OUT / "images" / "rootfs.ext4"


def buildroot_dir() -> Path:
    override = os.environ.get("BUILDROOT_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return ROOT / "third_party" / "buildroot"


def qemu_available() -> bool:
    return shutil.which("qemu-system-x86_64") is not None


def print_status() -> int:
    br = buildroot_dir()
    print("AuroraOS 98 full Firefox/Chromium rootfs profile")
    print(f"  defconfig: {DEFCONFIG}")
    print(f"  output:    {OUT}")
    print(f"  image:     {IMAGE}")
    print(f"  buildroot: {br}")
    print(f"  host:      {platform.system().lower()} {platform.machine()}")
    print(f"  qemu:      {'found' if qemu_available() else 'missing'}")
    print()
    if not DEFCONFIG.exists():
        print("missing x86-64 browser defconfig", file=sys.stderr)
        return 1
    if not (br / "Makefile").exists():
        print("Buildroot is not checked out here.")
        print("Set BUILDROOT_DIR to a Buildroot checkout, or place it at third_party/buildroot.")
        print("This Mac can still run the framebuffer prototype, but real Firefox/Chromium needs this full rootfs build.")
        return 0
    if platform.system() != "Linux":
        print("Buildroot is present, but full Chromium image builds should run on a Linux build host.")
        print("Use a Linux PC/VM for: make full-chromium-image")
        return 0
    print("Buildroot is present. Run: make full-chromium-image")
    return 0


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def build() -> int:
    br = buildroot_dir()
    if platform.system() != "Linux":
        print("ERROR: full browser images must be built on a Linux build host.", file=sys.stderr)
        print("This host can run QEMU previews, but the Buildroot Firefox/Chromium toolchain/build is Linux-hosted.", file=sys.stderr)
        print("Use a Linux PC/VM, then rerun: make full-chromium-image", file=sys.stderr)
        return 4
    if not (br / "Makefile").exists():
        print("ERROR: Buildroot is required for the full browser image.", file=sys.stderr)
        print("Set BUILDROOT_DIR=/path/to/buildroot or clone Buildroot into third_party/buildroot.", file=sys.stderr)
        print("Then rerun: make full-chromium-image", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    run(["make", f"O={OUT}", f"BR2_DEFCONFIG={DEFCONFIG}", "defconfig"], cwd=br)
    run(["make", f"O={OUT}"], cwd=br)
    if not IMAGE.exists():
        print(f"ERROR: expected image was not produced: {IMAGE}", file=sys.stderr)
        return 3
    print(f"Built full AuroraOS 98 Firefox/Chromium rootfs: {IMAGE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.check:
        return print_status()
    return build()


if __name__ == "__main__":
    raise SystemExit(main())
