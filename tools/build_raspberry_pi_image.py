#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "raspberry-pi"
DOWNLOADS = BUILD / "downloads"
PACKAGES = BUILD / "packages"
PACKAGE_ROOT = BUILD / "package-root"
QEMU_INITRAMFS = ROOT / "build" / "firefox-qemu-arm64" / "aurora-firefox-initramfs.cpio.lz4"
ARCADE_INITRAMFS = ROOT / "build" / "arcade-legend-x-arm64" / "arcade-legend-x-initramfs.cpio.lz4"

ALPINE_VERSION = "3.24.1"
ALPINE_BRANCH = "v3.24"
PI_TEST_VERSION = "0.4"
EXPECTED_KERNEL_PACKAGE_VERSION = "6.18.35-r0"
ALPINE_RELEASE_BASE = f"https://dl-cdn.alpinelinux.org/alpine/{ALPINE_BRANCH}/releases/aarch64"
ALPINE_MAIN = f"https://dl-cdn.alpinelinux.org/alpine/{ALPINE_BRANCH}/main/aarch64"
BASE_NAME = f"alpine-rpi-{ALPINE_VERSION}-aarch64.img.gz"
OUTPUT_NAME = "AuroraOS-98-Pi4-Pi5-test-0.1.img"
OUTPUT_800X480_NAME = "AuroraOS-98-Pi4-Pi5-test-0.4-800x480-fullscreen.img"
QEMU_SMOKE_INITRAMFS = "aurora-initramfs-rpi-qemu-smoke.lz4"
QEMU_ROOT_IMAGE = "aurora-pi-qemu-root.ext4"
ARCADE_QEMU_ROOT_IMAGE = "arcade-legend-x-pi-qemu-root.ext4"
ARCADE_OUTPUT_NAME = "Arcade-Legend-X-AuroraOS-Pi4-0.3-Legacy-HDMI-800x480.img"
QEMU_ROOT_SIZE = 1024 * 1024 * 1024
IMAGE_SIZE = 2048 * 1024 * 1024
PARTITION_START = 2048
SECTOR_SIZE = 512
REQUIRED_PACKAGES = (
    "linux-rpi",
    "linux-firmware-brcm",
    "linux-firmware-cypress",
    "linux-firmware-synaptics",
)
QEMU_SMOKE_SKIP_PREFIXES = (
    "usr/lib/wine",
    "usr/lib/vscodium",
    "usr/lib/electron",
    "usr/lib/firefox-esr",
    "usr/lib/libLLVM.so",
    "usr/lib/libgallium-",
)


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("+", " ".join(command))
    return subprocess.run(command, check=True, **kwargs)


def require_tools() -> None:
    missing = [name for name in ("bsdtar", "cpio", "lz4", "mcopy", "mdel", "mdir", "mformat", "xz") if not shutil.which(name)]
    if missing:
        raise RuntimeError(f"missing required tools: {', '.join(missing)}")


def download(url: str, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as target:
        shutil.copyfileobj(response, target, 1024 * 1024)
    temporary.replace(destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_base_image() -> Path:
    archive = DOWNLOADS / BASE_NAME
    checksum = DOWNLOADS / f"{BASE_NAME}.sha256"
    image = DOWNLOADS / BASE_NAME.removesuffix(".gz")
    download(f"{ALPINE_RELEASE_BASE}/{BASE_NAME}", archive)
    download(f"{ALPINE_RELEASE_BASE}/{BASE_NAME}.sha256", checksum)
    expected = checksum.read_text().split()[0]
    actual = sha256(archive)
    if actual != expected:
        raise RuntimeError(f"Alpine image checksum mismatch: expected {expected}, got {actual}")
    print(f"Verified Alpine base image: {actual}")
    if not image.exists():
        with gzip.open(archive, "rb") as source, image.open("wb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
    return image


def package_index() -> dict[str, dict[str, str]]:
    index = DOWNLOADS / "APKINDEX-main.tar.gz"
    download(f"{ALPINE_MAIN}/APKINDEX.tar.gz", index)
    with tarfile.open(index, "r:gz") as archive:
        member = archive.extractfile("APKINDEX")
        if member is None:
            raise RuntimeError("Alpine APK index does not contain APKINDEX")
        text = member.read().decode()
    packages: dict[str, dict[str, str]] = {}
    for block in text.strip().split("\n\n"):
        fields = dict(line.split(":", 1) for line in block.splitlines() if len(line) > 2 and line[1] == ":")
        if fields.get("P"):
            packages[fields["P"]] = fields
    return packages


def prepare_pi_files(product_name: str = "AuroraOS 98") -> Path:
    index = package_index()
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    PACKAGE_ROOT.mkdir(parents=True)
    for name in REQUIRED_PACKAGES:
        package = index.get(name)
        if package is None:
            raise RuntimeError(f"Alpine package not found: {name}")
        if name == "linux-rpi" and package["V"] != EXPECTED_KERNEL_PACKAGE_VERSION:
            raise RuntimeError(
                "Alpine linux-rpi no longer matches the verified base image: "
                f"expected {EXPECTED_KERNEL_PACKAGE_VERSION}, found {package['V']}"
            )
        filename = f"{name}-{package['V']}.apk"
        path = PACKAGES / filename
        download(f"{ALPINE_MAIN}/{filename}", path)
        run(["bsdtar", "-xf", str(path), "-C", str(PACKAGE_ROOT)])

    modules = PACKAGE_ROOT / "lib" / "modules"
    if not modules.exists():
        raise RuntimeError("linux-rpi package did not contain kernel modules")
    normalize_modules(modules)
    marker = PACKAGE_ROOT / "etc" / "aurora" / "pi-test-build"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        f"{product_name} Raspberry Pi hardware test {PI_TEST_VERSION}\n"
        f"Alpine Linux {ALPINE_VERSION} aarch64 foundation\n"
        "Requires Raspberry Pi 4 or 5 with at least 4 GB RAM\n"
    )
    return PACKAGE_ROOT


def normalize_modules(modules: Path) -> None:
    for compressed in sorted(modules.rglob("*.ko.gz")):
        plain = compressed.with_suffix("")
        with gzip.open(compressed, "rb") as source, plain.open("wb") as target:
            shutil.copyfileobj(source, target)
        plain.chmod(compressed.stat().st_mode)
        compressed.unlink()
    for metadata in modules.rglob("modules.*"):
        if not metadata.is_file():
            continue
        try:
            text = metadata.read_text()
        except UnicodeDecodeError:
            continue
        metadata.write_text(text.replace(".ko.gz", ".ko"))


def modify_init(
    data: bytes,
    display_800x480: bool,
    qemu_smoke: bool,
    product_name: str,
    pi4_legacy_display: bool = False,
) -> bytes:
    text = data.decode()
    path_setup = "export PATH=/sbin:/bin:/usr/sbin:/usr/bin\n"
    if path_setup not in text:
        raise RuntimeError("could not locate PATH setup in Aurora init")
    early_setup = "mount -o remount,rw / 2>/dev/null || true\n"
    compact = qemu_smoke or display_800x480 or pi4_legacy_display
    if compact:
        early_setup += "export AURORA_COMPACT=1\n"
        text = text.replace("export GDK_DPI_SCALE=1.25", "export GDK_DPI_SCALE=1")
        text = text.replace("export QT_SCALE_FACTOR=1.25", "export QT_SCALE_FACTOR=1")
        text = text.replace("Xft.dpi: 144", "Xft.dpi: 96")
    text = text.replace(path_setup, path_setup + early_setup, 1)
    anchor = "modprobe bochs >/dev/console 2>&1 || true\n"
    if qemu_smoke:
        pi_setup = """# AuroraOS Raspberry Pi QEMU framebuffer profile
mdev -s 2>/dev/null || true
sed -i 's/Driver "modesetting"/Driver "fbdev"/' /etc/X11/xorg.conf
sed -i 's/^[[:space:]]*Modes .*/        Modes "800x480"/' /etc/X11/xorg.conf
"""
    elif pi4_legacy_display:
        pi_setup = """# Pi 4 legacy framebuffer profile for older HDMI controller boards
for module in bcm2835_dma bcm2835_codec bcm2835_isp bcmgenet brcmfmac cfg80211 snd_bcm2835 raspberrypi_hwmon; do
    modprobe "$module" >/dev/console 2>&1 || true
done
mdev -s 2>/dev/null || true
for i in 1 2 3 4 5; do
    [ -e /dev/fb0 ] && break
    sleep 1
    mdev -s 2>/dev/null || true
done
sed -i 's/Driver "modesetting"/Driver "fbdev"/' /etc/X11/xorg.conf
sed -i 's/^[[:space:]]*Modes .*/        Modes "800x480"/' /etc/X11/xorg.conf
"""
    else:
        pi_setup = """# AuroraOS Raspberry Pi hardware test
for module in drm drm_kms_helper vc4 v3d bcm2835_dma bcm2835_codec bcm2835_isp bcmgenet macb brcmfmac cfg80211 snd_bcm2835 raspberrypi_hwmon; do
    modprobe "$module" >/dev/console 2>&1 || true
done
mdev -s 2>/dev/null || true
for i in 1 2 3 4 5; do
    [ -e /dev/dri/card0 ] && break
    sleep 1
    mdev -s 2>/dev/null || true
done
"""
    if anchor not in text:
        raise RuntimeError("could not locate module setup in Aurora init")
    if compact:
        pi_setup += """# Fit the complete Aurora shell into an 800x480 panel.
sed -i 's/height="82"/height="46"/; s/MS W98 UI-18/MS W98 UI-12/g; s|<Height>46</Height>|<Height>30</Height>|; s/maxwidth="620"/maxwidth="100"/' /etc/jwm/aurora.jwmrc
sed -i '/TrayButton label="Settings"/d; /TrayButton label="Store"/d' /etc/jwm/aurora.jwmrc
sed -i 's/FontSize: 16/FontSize: 12/; s/SnapWidth: 120/SnapWidth: 90/; s/SnapHeight: 112/SnapHeight: 90/' /usr/bin/aurora-desktop-icons
sed -i \\
  -e 's|180 60 /usr|90 45 /usr|' \\
  -e 's|180 190 /usr|280 45 /usr|' \\
  -e 's|180 320 /usr|470 45 /usr|' \\
  -e 's|180 450 /usr|660 45 /usr|' \\
  -e 's|180 580 /usr|90 190 /usr|' \\
  -e 's|420 580 /usr|280 190 /usr|' \\
  -e 's|430 60 /usr|470 190 /usr|' \\
  -e 's|430 190 /usr|660 190 /usr|' \\
  /usr/bin/aurora-desktop-icons
"""
    if qemu_smoke:
        pass
    elif display_800x480 or pi4_legacy_display:
        pi_setup += """# Do not let the inherited QEMU Xorg profile select 1440x900.
sed -i 's/^[[:space:]]*Modes .*/        Modes "800x480"/' /etc/X11/xorg.conf
"""
    else:
        pi_setup += """# Let KMS and the monitor EDID choose the Pi display mode.
sed -i '/^[[:space:]]*Modes /d' /etc/X11/xorg.conf
"""
    text = text.replace(anchor, pi_setup + anchor, 1)
    text = text.replace(
        "printf 'nameserver 10.0.2.3\\nnameserver 1.1.1.1\\n' >/etc/resolv.conf",
        "printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' >/etc/resolv.conf",
    )
    text = text.replace(
        "AuroraOS 98: starting real Firefox ESR on Xorg",
        f"{product_name} Raspberry Pi test: starting Xorg",
    )
    text = text.replace(
        "Arcade Legend X: starting Xorg",
        f"{product_name} Raspberry Pi test: starting Xorg",
    )
    return text.encode()


def read_exact(stream, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = stream.read(size - len(chunks))
        if not chunk:
            raise EOFError(f"unexpected end of cpio stream, wanted {size} bytes")
        chunks.extend(chunk)
    return bytes(chunks)


def transfer(stream, target, size: int, copy: bool) -> bytes | None:
    captured = bytearray() if target is None and copy else None
    remaining = size
    while remaining:
        chunk = stream.read(min(1024 * 1024, remaining))
        if not chunk:
            raise EOFError("unexpected end of cpio data")
        if target is not None and copy:
            target.write(chunk)
        elif captured is not None:
            captured.extend(chunk)
        remaining -= len(chunk)
    return bytes(captured) if captured is not None else None


def newc_header(name: bytes, mode: int, size: int, inode: int, mtime: int = 0) -> bytes:
    fields = (inode, mode, 0, 0, 1, mtime, size, 0, 0, 0, 0, len(name) + 1, 0)
    return b"070701" + b"".join(f"{value:08x}".encode() for value in fields)


def write_newc_entry(target, name: str, mode: int, data: bytes, inode: int, mtime: int = 0) -> None:
    encoded = name.encode()
    target.write(newc_header(encoded, mode, len(data), inode, mtime))
    target.write(encoded + b"\0")
    target.write(b"\0" * ((4 - ((110 + len(encoded) + 1) % 4)) % 4))
    target.write(data)
    target.write(b"\0" * ((4 - (len(data) % 4)) % 4))


def overlay_paths(root: Path) -> list[Path]:
    selected: set[Path] = set()
    for relative in (Path("lib/modules"), Path("lib/firmware"), Path("etc/aurora")):
        source = root / relative
        if not source.exists():
            continue
        selected.add(source)
        selected.update(source.rglob("*"))
        parent = source.parent
        while parent != root:
            selected.add(parent)
            parent = parent.parent
    return sorted(selected, key=lambda path: (len(path.relative_to(root).parts), str(path.relative_to(root))))


def build_pi_initramfs(
    pi_root: Path,
    output: Path,
    display_800x480: bool,
    qemu_smoke: bool = False,
    source_initramfs: Path = QEMU_INITRAMFS,
    product_name: str = "AuroraOS 98",
    pi4_legacy_display: bool = False,
) -> None:
    if not source_initramfs.exists():
        raise RuntimeError(f"ARM64 source initramfs is missing: {source_initramfs}")
    output.parent.mkdir(parents=True, exist_ok=True)
    decompressor = subprocess.Popen(["lz4", "-dc", str(source_initramfs)], stdout=subprocess.PIPE)
    output_file = output.open("wb")
    compressor = subprocess.Popen(["lz4", "-l", "-1", "-q"], stdin=subprocess.PIPE, stdout=output_file)
    assert decompressor.stdout is not None and compressor.stdin is not None
    source = decompressor.stdout
    target = compressor.stdin
    init_data: bytes | None = None
    count = 0
    try:
        while True:
            header = read_exact(source, 110)
            if header[:6] not in (b"070701", b"070702"):
                raise RuntimeError(f"unsupported cpio header: {header[:6]!r}")
            values = [int(header[6 + i * 8:14 + i * 8], 16) for i in range(13)]
            size = values[6]
            name_size = values[11]
            name_blob = read_exact(source, name_size)
            name = name_blob[:-1].decode(errors="surrogateescape")
            name_padding = read_exact(source, (4 - ((110 + name_size) % 4)) % 4)
            if name == "TRAILER!!!":
                break
            normalized_name = name.removeprefix("./")
            smoke_skip = (
                qemu_smoke
                and source_initramfs == QEMU_INITRAMFS
                and normalized_name.startswith(QEMU_SMOKE_SKIP_PREFIXES)
            )
            skip = (
                name == "./init"
                or name == "init"
                or name.startswith("./lib/modules/")
                or name == "./lib/modules"
                or smoke_skip
            )
            capture_init = name in ("./init", "init")
            if not skip:
                target.write(header)
                target.write(name_blob)
                target.write(name_padding)
            data = transfer(source, None if capture_init else target, size, not skip or capture_init)
            data_padding = read_exact(source, (4 - (size % 4)) % 4)
            if not skip:
                target.write(data_padding)
            if capture_init:
                init_data = data
            count += 1
            if count % 5000 == 0:
                print(f"Processed {count} initramfs entries")

        if init_data is None:
            raise RuntimeError("Aurora initramfs did not contain /init")
        inode = 0x70000000
        write_newc_entry(
            target,
            "./init",
            stat.S_IFREG | 0o755,
            modify_init(
                init_data,
                display_800x480,
                qemu_smoke,
                product_name,
                pi4_legacy_display,
            ),
            inode,
        )
        inode += 1
        for path in overlay_paths(pi_root):
            relative = path.relative_to(pi_root)
            name = "./" + relative.as_posix()
            info = path.lstat()
            if path.is_symlink():
                data = os.readlink(path).encode()
                mode = stat.S_IFLNK | 0o777
            elif path.is_dir():
                data = b""
                mode = stat.S_IFDIR | (info.st_mode & 0o7777)
            elif path.is_file():
                data = path.read_bytes()
                mode = stat.S_IFREG | (info.st_mode & 0o7777)
            else:
                continue
            write_newc_entry(target, name, mode, data, inode, int(info.st_mtime))
            inode += 1
        write_newc_entry(target, "TRAILER!!!", 0, b"", inode)
    finally:
        target.close()
        source.close()
    if decompressor.wait() != 0 or compressor.wait() != 0:
        raise RuntimeError("failed to repack Raspberry Pi initramfs")
    output_file.close()
    print(f"Wrote {output} ({output.stat().st_size // (1024 * 1024)} MB)")


def write_mbr(image: Path) -> None:
    sector_count = IMAGE_SIZE // SECTOR_SIZE - PARTITION_START
    with image.open("wb") as target:
        target.truncate(IMAGE_SIZE)
    entry = bytearray(16)
    entry[0] = 0x80
    entry[1:4] = bytes((0, 2, 0))
    entry[4] = 0x0C
    entry[5:8] = bytes((0xFE, 0xFF, 0xFF))
    entry[8:12] = struct.pack("<I", PARTITION_START)
    entry[12:16] = struct.pack("<I", sector_count)
    mbr = bytearray(SECTOR_SIZE)
    mbr[446:462] = entry
    mbr[510:512] = b"\x55\xaa"
    with image.open("r+b") as target:
        target.write(mbr)


def mtools_environment(base: Path, image: Path, directory: Path) -> dict[str, str]:
    config = directory / "mtoolsrc"
    offset = PARTITION_START * SECTOR_SIZE
    config.write_text(
        f'drive a: file="{base}" offset={offset}\n'
        f'drive b: file="{image}" offset={offset}\n'
    )
    environment = os.environ.copy()
    environment["MTOOLSRC"] = str(config)
    return environment


def assemble_image(
    base: Path,
    initramfs: Path,
    output: Path,
    display_800x480: bool,
    product_name: str = "AuroraOS 98",
    pi4_legacy_display: bool = False,
) -> None:
    write_mbr(output)
    offset = PARTITION_START * SECTOR_SIZE
    run(["mformat", "-i", f"{output}@@{offset}", "-F", "-v", "AURORA_PI", "::"])
    with tempfile.TemporaryDirectory(prefix="aurora-pi-") as temporary:
        temp = Path(temporary)
        environment = mtools_environment(base, output, temp)
        run(["mcopy", "-s", "a:/*", "b:/"], env=environment)
        run(["mdel", "b:/boot/initramfs-rpi"], env=environment)
        run(["mcopy", "-o", str(initramfs), "b:/boot/initramfs-rpi"], env=environment)

        usercfg = f"# {product_name} Raspberry Pi hardware test\n"
        usercfg += "disable_overscan=1\nmax_framebuffers=2\n"
        if not pi4_legacy_display:
            usercfg += (
                "[pi4]\n"
                "dtoverlay=vc4-kms-v3d-pi4\n"
                "[pi5]\n"
                "dtoverlay=vc4-kms-v3d-pi5\n"
                "[all]\n"
            )
        cmdline = "console=tty1 quiet loglevel=4 vt.global_cursor_default=0"
        if pi4_legacy_display:
            usercfg += (
                "# Pi 4 firmware framebuffer for older 5-inch HDMI boards.\n"
                "hdmi_force_hotplug=1\n"
                "hdmi_group=2\n"
                "hdmi_mode=87\n"
                "hdmi_cvt=800 480 60 6 0 0 0\n"
                "hdmi_drive=2\n"
                "framebuffer_width=800\n"
                "framebuffer_height=480\n"
                "framebuffer_depth=32\n"
                "framebuffer_ignore_alpha=1\n"
                "disable_splash=1\n"
            )
        elif display_800x480:
            usercfg += (
                "# Waveshare-compatible 5-inch 800x480 HDMI timing.\n"
                "# Let the firmware pass this custom CVT mode to KMS.\n"
                "hdmi_force_hotplug=1\n"
                "hdmi_group=2\n"
                "hdmi_mode=87\n"
                "hdmi_cvt=800 480 60 6 0 0 0\n"
                "hdmi_drive=1\n"
                "disable_splash=1\n"
            )
        (temp / "usercfg.txt").write_text(usercfg)
        (temp / "cmdline.txt").write_text(cmdline + "\n")
        if pi4_legacy_display:
            display_profile = "Display profile: Pi 4 legacy HDMI framebuffer at 800x480.\r\n"
        elif display_800x480:
            display_profile = "Display profile: Waveshare-compatible 800x480 CVT at 60 Hz on HDMI.\r\n"
        else:
            display_profile = "Display profile: automatic HDMI detection.\r\n"
        (temp / "README-PI.txt").write_text(
            f"{product_name} Raspberry Pi hardware test {PI_TEST_VERSION}\r\n"
            "================================================\r\n"
            "Target: Raspberry Pi 4 or Pi 5 with 4 GB RAM or more.\r\n"
            "This is an experimental RAM-based desktop image. Changes do not persist.\r\n"
            "Ethernet is recommended for the first test.\r\n"
            + display_profile
            + "If the GUI fails, connect a display and keyboard and record the console error.\r\n"
        )
        for filename in ("usercfg.txt", "cmdline.txt", "README-PI.txt"):
            run(["mcopy", "-o", str(temp / filename), f"b:/{filename}"], env=environment)
        listing = run(["mdir", "-b", "b:/boot"], env=environment, capture_output=True, text=True).stdout
        if "initramfs" not in listing.lower() or "vmlinuz" not in listing.lower():
            raise RuntimeError("assembled image is missing boot files")
    print(f"Assembled sparse image: {output}")


def compress_image(image: Path) -> Path:
    compressed = image.with_suffix(image.suffix + ".xz")
    temporary = compressed.with_suffix(compressed.suffix + ".part")
    with temporary.open("wb") as target:
        run(["xz", "-T0", "-1", "-c", str(image)], stdout=target)
    temporary.replace(compressed)
    checksum = compressed.with_suffix(compressed.suffix + ".sha256")
    checksum.write_text(f"{sha256(compressed)}  {compressed.name}\n")
    print(f"Wrote {compressed}")
    print(f"Wrote {checksum}")
    return compressed


def clean_precompression_intermediates(base: Path, initramfs: Path) -> None:
    initramfs.unlink(missing_ok=True)
    base.unlink(missing_ok=True)
    shutil.rmtree(PACKAGE_ROOT, ignore_errors=True)


def e2fs_tool(name: str) -> str:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    homebrew = Path("/opt/homebrew/opt/e2fsprogs/sbin") / name
    if homebrew.exists():
        return str(homebrew)
    raise RuntimeError(f"missing {name}; on macOS run: brew install e2fsprogs")


def prepare_qemu_smoke_boot_files(base: Path) -> Path:
    destination = BUILD / "qemu-raspi4"
    destination.mkdir(parents=True, exist_ok=True)
    source = f"{base}@@{PARTITION_START * SECTOR_SIZE}"
    for guest, host in (
        ("::boot/vmlinuz-rpi", "vmlinuz-rpi"),
        ("::bcm2711-rpi-4-b.dtb", "bcm2711-rpi-4-b.dtb"),
        ("::boot/initramfs-rpi", "initramfs-rpi"),
    ):
        (destination / host).unlink(missing_ok=True)
        run(["mcopy", "-o", "-i", source, guest, str(destination / host)])
    return destination


def prepare_qemu_device_tree(destination: Path) -> None:
    original = destination / "bcm2711-rpi-4-b.dtb"
    effective = destination / "bcm2711-rpi-4-b-effective.dtb"
    source = destination / "bcm2711-rpi-4-b-qemu.dts"
    output = destination / "bcm2711-rpi-4-b-qemu.dtb"
    run([
        "qemu-system-aarch64",
        "-M", f"raspi4b,dumpdtb={effective}",
        "-m", "2G",
        "-kernel", str(destination / "vmlinuz-rpi"),
        "-dtb", str(original),
        "-display", "none",
    ])
    result = run(["dtc", "-q", "-I", "dtb", "-O", "dts", str(effective)], capture_output=True, text=True)
    text = result.stdout
    usb_pattern = r'(usb: usb@7e980000 \{.*?)(\n\s*power-domains = <[^;]+>;)(.*?\n\s*status = )"disabled";'
    text, usb_changes = re.subn(usb_pattern, r'\1\3"okay";', text, count=1, flags=re.DOTALL)
    emmc_pattern = (
        r'(emmc2: mmc@7e340000 \{.*?)'
        r'(\n\s*vqmmc-supply = <[^;]+>;\n\s*vmmc-supply = <[^;]+>;)'
    )
    text, emmc_changes = re.subn(emmc_pattern, r'\1', text, count=1, flags=re.DOTALL)
    if usb_changes != 1 or emmc_changes != 1:
        raise RuntimeError("could not adapt the Raspberry Pi device tree for QEMU")
    source.write_text(text)
    run(["dtc", "-q", "-I", "dts", "-O", "dtb", "-o", str(output), str(source)])


def build_qemu_root(initramfs: Path, destination: Path, image_name: str = QEMU_ROOT_IMAGE) -> Path:
    root = BUILD / "qemu-root"
    image = BUILD / image_name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    decompressor = subprocess.Popen(["lz4", "-dc", str(initramfs)], stdout=subprocess.PIPE)
    assert decompressor.stdout is not None
    run(["bsdtar", "-xf", "-", "-C", str(root)], stdin=decompressor.stdout)
    decompressor.stdout.close()
    if decompressor.wait() != 0:
        raise RuntimeError("failed to extract Raspberry Pi QEMU root filesystem")
    (root / "sbin").mkdir(parents=True, exist_ok=True)
    init_link = root / "sbin" / "init"
    init_link.unlink(missing_ok=True)
    init_link.symlink_to("/init")
    image.unlink(missing_ok=True)
    root_size = IMAGE_SIZE if image_name == ARCADE_QEMU_ROOT_IMAGE else QEMU_ROOT_SIZE
    with image.open("wb") as target:
        target.truncate(root_size)
    run([e2fs_tool("mke2fs"), "-q", "-t", "ext4", "-F", "-L", "AURORA_ROOT", "-d", str(root), str(image)])
    run([e2fs_tool("e2fsck"), "-fn", str(image)])
    prepare_qemu_device_tree(destination)
    shutil.rmtree(root, ignore_errors=True)
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the experimental AuroraOS Raspberry Pi 4/5 SD image")
    parser.add_argument("--keep-intermediates", action="store_true")
    parser.add_argument(
        "--display-800x480",
        action="store_true",
        help="force a generic 5-inch 800x480 HDMI panel connected to HDMI0",
    )
    parser.add_argument(
        "--qemu-smoke",
        action="store_true",
        help="build a reduced Pi 4 initramfs that fits QEMU's emulated RAM",
    )
    parser.add_argument(
        "--pi4-legacy-display",
        action="store_true",
        help="use the Pi 4 firmware framebuffer for older 800x480 HDMI boards",
    )
    parser.add_argument(
        "--arcade-legend-x",
        action="store_true",
        help="package the Arcade Legend X console frontend instead of the Aurora desktop",
    )
    args = parser.parse_args()
    require_tools()
    BUILD.mkdir(parents=True, exist_ok=True)
    base = ensure_base_image()
    product_name = "Arcade Legend X" if args.arcade_legend_x else "AuroraOS 98"
    source_initramfs = ARCADE_INITRAMFS if args.arcade_legend_x else QEMU_INITRAMFS
    pi_root = prepare_pi_files(product_name)
    if args.qemu_smoke:
        initramfs = BUILD / QEMU_SMOKE_INITRAMFS
        build_pi_initramfs(
            pi_root,
            initramfs,
            True,
            qemu_smoke=True,
            source_initramfs=source_initramfs,
            product_name=product_name,
        )
        run(["lz4", "-t", str(initramfs)])
        qemu_files = prepare_qemu_smoke_boot_files(base)
        qemu_root_name = ARCADE_QEMU_ROOT_IMAGE if args.arcade_legend_x else QEMU_ROOT_IMAGE
        root_image = build_qemu_root(initramfs, qemu_files, qemu_root_name)
        initramfs.unlink(missing_ok=True)
        if not args.keep_intermediates:
            base.unlink(missing_ok=True)
            shutil.rmtree(PACKAGE_ROOT, ignore_errors=True)
        print(f"Raspberry Pi QEMU virtual SD root: {root_image}")
        return 0
    initramfs = BUILD / "aurora-initramfs-rpi.lz4"
    if args.arcade_legend_x:
        image = BUILD / ARCADE_OUTPUT_NAME
    else:
        image = BUILD / (OUTPUT_800X480_NAME if args.display_800x480 else OUTPUT_NAME)
    build_pi_initramfs(
        pi_root,
        initramfs,
        args.display_800x480,
        source_initramfs=source_initramfs,
        product_name=product_name,
        pi4_legacy_display=args.pi4_legacy_display,
    )
    run(["lz4", "-t", str(initramfs)])
    assemble_image(
        base,
        initramfs,
        image,
        args.display_800x480,
        product_name,
        args.pi4_legacy_display,
    )
    if not args.keep_intermediates:
        clean_precompression_intermediates(base, initramfs)
    compressed = compress_image(image)
    if not args.keep_intermediates:
        image.unlink(missing_ok=True)
    print()
    print(f"{product_name} Raspberry Pi test image ready")
    print(f"Image: {compressed}")
    print(f"SHA256: {compressed.with_suffix(compressed.suffix + '.sha256')}")
    print("Hardware requirement: Raspberry Pi 4/5 with at least 4 GB RAM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
