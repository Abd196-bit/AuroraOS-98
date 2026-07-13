from pathlib import Path
import shutil
import subprocess
import gzip
import platform
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build" / "linux-base"
ISO = BASE / "iso"
APKS = BASE / "apks" / "x86_64"
ROOTFS = BASE / "initramfs-root"
OUT = BASE / "aurora-initramfs.cpio.gz"
LINUX_VIRT_ROOT = BASE / "linux-virt-apk"
ALPINE_REPO = "https://dl-cdn.alpinelinux.org/alpine/edge/main/x86_64"
ALPINE_PACKAGES = ["musl", "busybox", "busybox-binsh", "linux-virt"]
ZIG_VERSION = "0.16.0"
ZIG_PLATFORM = "macos" if platform.system() == "Darwin" else "linux"
ZIG_ARCH = "aarch64" if platform.machine() in {"arm64", "aarch64"} else "x86_64"
ZIG_DIR = ROOT / "build" / "tools" / f"zig-{ZIG_ARCH}-{ZIG_PLATFORM}-{ZIG_VERSION}"
ZIG = ZIG_DIR / "zig"
ZIG_ARCHIVE = ROOT / "build" / "tools" / f"zig-{ZIG_ARCH}-{ZIG_PLATFORM}-{ZIG_VERSION}.tar.xz"
ZIG_URL = f"https://ziglang.org/download/{ZIG_VERSION}/{ZIG_ARCHIVE.name}"
FB_SHELL_SRC = ROOT / "src" / "aurora-fb-shell" / "aurora_fb_shell.c"
FB_SHELL_BIN = ROOT / "build" / "tools" / "aurora-fb-shell"


def run(cmd, cwd=None):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, cwd=cwd, check=True)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def parse_apk_index() -> dict[str, dict[str, str]]:
    import io
    import tarfile

    index = fetch(f"{ALPINE_REPO}/APKINDEX.tar.gz")
    packages: dict[str, dict[str, str]] = {}
    with tarfile.open(fileobj=io.BytesIO(index), mode="r:gz") as archive:
        member = archive.extractfile("APKINDEX")
        if member is None:
            raise SystemExit("Alpine APKINDEX did not contain APKINDEX")
        text = member.read().decode()
    for block in text.strip().split("\n\n"):
        item: dict[str, str] = {}
        for line in block.splitlines():
            if len(line) > 2 and line[1] == ":":
                item[line[0]] = line[2:]
        name = item.get("P")
        if name:
            packages[name] = item
    return packages


def ensure_alpine_packages():
    APKS.mkdir(parents=True, exist_ok=True)
    packages = parse_apk_index()
    for name in ALPINE_PACKAGES:
        item = packages.get(name)
        if not item:
            raise SystemExit(f"Alpine package not found in APKINDEX: {name}")
        filename = f"{item['P']}-{item['V']}.apk"
        path = APKS / filename
        if not path.exists():
            url = f"{ALPINE_REPO}/{filename}"
            print(f"downloading {filename}")
            path.write_bytes(fetch(url))

    linux_virt = sorted(APKS.glob("linux-virt-*.apk"))
    if not linux_virt:
        raise SystemExit("missing downloaded linux-virt apk")
    if LINUX_VIRT_ROOT.exists():
        shutil.rmtree(LINUX_VIRT_ROOT)
    LINUX_VIRT_ROOT.mkdir(parents=True, exist_ok=True)
    run(["bsdtar", "-xf", str(linux_virt[0]), "-C", str(LINUX_VIRT_ROOT)])

    vmlinuz = LINUX_VIRT_ROOT / "boot" / "vmlinuz-virt"
    if not vmlinuz.exists():
        matches = sorted(LINUX_VIRT_ROOT.glob("boot/vmlinuz-*"))
        if matches:
            vmlinuz = matches[0]
    if not vmlinuz.exists():
        raise SystemExit("linux-virt apk did not contain a boot/vmlinuz kernel")
    (ISO / "boot").mkdir(parents=True, exist_ok=True)
    shutil.copy2(vmlinuz, ISO / "boot" / "vmlinuz-virt")


def kernel_version() -> str:
    modules = LINUX_VIRT_ROOT / "lib" / "modules"
    versions = sorted(path.name for path in modules.iterdir() if path.is_dir()) if modules.exists() else []
    if not versions:
        raise SystemExit("linux-virt modules were not extracted")
    return versions[0]


def module_src() -> Path:
    return LINUX_VIRT_ROOT / "lib" / "modules" / kernel_version()


def build_cpio(rootfs: Path, out: Path):
    find = subprocess.Popen(["find", "."], cwd=rootfs, stdout=subprocess.PIPE)
    cpio = subprocess.Popen(["cpio", "-o", "-H", "newc"], cwd=rootfs, stdin=find.stdout, stdout=subprocess.PIPE)
    assert find.stdout is not None
    find.stdout.close()
    with out.open("wb") as fh:
        gzip = subprocess.Popen(["gzip", "-9"], stdin=cpio.stdout, stdout=fh)
        assert cpio.stdout is not None
        cpio.stdout.close()
        gzip.wait()
    cpio.wait()
    find.wait()
    if find.returncode != 0 or cpio.returncode != 0 or gzip.returncode != 0:
        raise SystemExit("failed to build initramfs cpio.gz")


def extract_apk(pattern):
    matches = sorted(APKS.glob(pattern))
    if not matches:
        raise SystemExit(f"missing apk {pattern}")
    run(["bsdtar", "-xf", str(matches[0]), "-C", str(ROOTFS)])


def copytree(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)


def copy_module(rel: str):
    src = module_src() / rel
    if not src.exists():
        print(f"warning: missing module {src}")
        return
    dst = ROOTFS / "lib" / "modules" / kernel_version() / rel.removesuffix(".gz")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix == ".gz":
        with gzip.open(src, "rb") as fh, dst.open("wb") as out:
            shutil.copyfileobj(fh, out)
    else:
        shutil.copy2(src, dst)


def copy_kernel_modules():
    src = module_src()
    dst = ROOTFS / "lib" / "modules" / kernel_version()
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)


def ensure_zig():
    if ZIG.exists():
        return
    if ZIG_PLATFORM not in {"macos", "linux"}:
        raise SystemExit(f"unsupported host for automatic Zig setup: {platform.system()} {platform.machine()}")
    ZIG_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if not ZIG_ARCHIVE.exists():
        print(f"downloading Zig {ZIG_VERSION} toolchain: {ZIG_URL}")
        with urllib.request.urlopen(ZIG_URL, timeout=120) as response, ZIG_ARCHIVE.open("wb") as out:
            shutil.copyfileobj(response, out)
    print(f"extracting {ZIG_ARCHIVE}")
    run(["tar", "-xf", str(ZIG_ARCHIVE), "-C", str(ZIG_ARCHIVE.parent)])
    if not ZIG.exists():
        raise SystemExit(f"Zig extraction finished but compiler is missing at {ZIG}")


def build_fb_shell():
    ensure_zig()
    FB_SHELL_BIN.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(ZIG),
        "cc",
        "-target",
        "x86_64-linux-musl",
        "-O2",
        "-static",
        str(FB_SHELL_SRC),
        "-o",
        str(FB_SHELL_BIN),
    ])


def main():
    ensure_alpine_packages()
    build_fb_shell()

    if ROOTFS.exists():
        shutil.rmtree(ROOTFS)
    for d in ["bin", "sbin", "lib", "usr/bin", "usr/sbin", "proc", "sys", "dev", "tmp", "aurora"]:
        (ROOTFS / d).mkdir(parents=True, exist_ok=True)
    (ROOTFS / "etc" / "aurora").mkdir(parents=True, exist_ok=True)

    extract_apk("musl-*.apk")
    extract_apk("busybox-1*.apk")
    extract_apk("busybox-binsh-*.apk")

    busybox = ROOTFS / "bin" / "busybox"
    for app in [
        "sh", "mount", "umount", "mkdir", "mknod", "cat", "echo", "sleep", "clear",
        "stty", "readlink", "ls", "cp", "dd", "sync", "reboot", "poweroff", "insmod", "modprobe", "dmesg",
    ]:
        target = ROOTFS / "bin" / app
        if not target.exists() and not target.is_symlink():
            target.symlink_to("busybox")

    copytree(ROOT / "assets" / "icons" / "system", ROOTFS / "aurora" / "icons")
    shutil.copy2(ROOT / "MSW98UI-Regular copy.ttf", ROOTFS / "aurora" / "MSW98UI-Regular.ttf")
    shutil.copy2(ROOT / "MSW98UI-Bold copy.ttf", ROOTFS / "aurora" / "MSW98UI-Bold.ttf")
    shutil.copy2(ROOT / "click.wav", ROOTFS / "aurora" / "click.wav")
    shutil.copy2(FB_SHELL_BIN, ROOTFS / "bin" / "aurora-fb-shell")
    for manifest in sorted((ROOT / "packaging").glob("*.toml")):
        shutil.copy2(manifest, ROOTFS / "etc" / "aurora" / manifest.name)
    for screen in sorted((BASE / "screens").glob("*.bgra32")):
        shutil.copy2(screen, ROOTFS / "aurora" / screen.name)

    copy_kernel_modules()

    init = ROOTFS / "init"
    init.write_text(
        """#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || {
  mount -t tmpfs tmpfs /dev
  mknod /dev/console c 5 1
  mknod /dev/null c 1 3
  mknod /dev/zero c 1 5
mknod /dev/fb0 c 29 0
}
load_graphics() {
  modprobe bochs >/dev/console 2>&1 || true
  modprobe cirrus-qemu >/dev/console 2>&1 || true
  modprobe virtio-gpu >/dev/console 2>&1 || true
  modprobe evdev >/dev/console 2>&1 || true
  modprobe mousedev >/dev/console 2>&1 || true
  modprobe psmouse >/dev/console 2>&1 || true
  modprobe hid >/dev/console 2>&1 || true
  modprobe hid-generic >/dev/console 2>&1 || true
  modprobe usbhid >/dev/console 2>&1 || true
  modprobe usbmouse >/dev/console 2>&1 || true
  sleep 2
}

draw_graphics() {
  if [ -e /dev/fb0 ]; then
    cat "/aurora/$1" > /dev/fb0 2>/dev/null && return 0
  fi
  return 1
}

load_graphics
printf '\033[?25l\033[2J' > /dev/console 2>/dev/null || true
stty raw -echo < /dev/console 2>/dev/null || true
if [ -e /dev/fb0 ]; then
  /bin/aurora-fb-shell
  poweroff -f
fi

esc="$(printf '\\033')"
blue="${esc}[44m"
gray="${esc}[47;30m"
cyan="${esc}[46;30m"
white="${esc}[37m"
black="${esc}[30m"
rev="${esc}[7m"
reset="${esc}[0m"

put() { printf "${esc}[%s;%sH%s" "$2" "$1" "$3" > /dev/console; }
bar() { x="$1"; y="$2"; w="$3"; ch="$4"; i=0; while [ "$i" -lt "$w" ]; do put $((x+i)) "$y" "$ch"; i=$((i+1)); done; }
box() {
  x="$1"; y="$2"; w="$3"; h="$4"; title="$5"
  bar "$x" "$y" "$w" "-"
  bar "$x" $((y+h-1)) "$w" "-"
  i=0; while [ "$i" -lt "$h" ]; do put "$x" $((y+i)) "|"; put $((x+w-1)) $((y+i)) "|"; i=$((i+1)); done
  put "$x" "$y" "+"
  put $((x+w-1)) "$y" "+"
  put "$x" $((y+h-1)) "+"
  put $((x+w-1)) $((y+h-1)) "+"
  [ -n "$title" ] && put $((x+2)) "$y" "${blue}${white} $title ${gray}${black}"
}

desktop() {
  printf "${reset}${cyan}${black}${esc}[2J" > /dev/console
  put 3 2 "▣"
  put 1 3 "My Computer"
  put 3 7 "▥"
  put 1 8 "Network"
  put 1 9 "Neighborhood"
  put 3 13 "♻"
  put 1 14 "Recycle Bin"

  printf "${gray}${black}" > /dev/console
  box 29 1 51 24 "System Properties"
  put 31 4 "[ General ][ Device Manager ][ Hardware Profiles ][ Performance ]"
  put 54 7 "System:"
  put 58 9 "AuroraOS 98"
  put 58 10 "Raspberry Pi Edition"
  put 58 11 "Linux base"
  put 54 14 "Registered to:"
  put 58 16 "AuroraOS Developer"
  put 58 17 "00023-OEM-AURORA-PI"
  put 36 21 "Linux + Alpine initramfs + QEMU"
  put 58 22 "Raspberry Pi target"
  put 60 24 "[ OK ]  [ Cancel ]"

  box 9 5 33 16 "My Computer"
  put 11 7 "File   Edit   View   Help"
  put 12 10 "▣  3½ Floppy [A:]"
  put 26 10 "▭  [C:]"
  put 12 13 "▤  Control"
  put 26 13 "▤  Printers"

  draw_start
  taskbar
}

draw_start() {
  printf "${gray}${black}" > /dev/console
  box 1 13 22 17 ""
  printf "${blue}${white}" > /dev/console
  put 2 14 "A"
  put 2 15 "u"
  put 2 16 "r"
  put 2 17 "o"
  put 2 18 "r"
  put 2 19 "a"
  put 2 20 "O"
  put 2 21 "S"
  put 2 22 "9"
  put 2 23 "8"
  printf "${gray}${black}" > /dev/console
  put 5 14 "${blue}${white} Programs    > ${gray}${black}"
  put 5 16 " Documents   >"
  put 5 18 " Settings    >"
  put 5 20 " Find        >"
  put 5 22 " Help"
  put 5 24 " Run..."
  put 5 27 " Suspend"
  put 5 29 " Shut Down..."
  box 23 13 20 8 ""
  put 25 14 "98lite       >"
  put 25 15 "Accessories  >"
  put 25 16 "StartUp      >"
  put 25 17 "MS-DOS Prompt"
  put 25 18 "Windows Explorer"
  put 19 15 "▲"
}

taskbar() {
  printf "${gray}${black}" > /dev/console
  put 1 30 "+--------+-------------------+--------------------------------------+----------+"
  put 2 31 "| Start  | My Computer       |                                      | 2:54 AM |"
  put 1 32 "+--------+-------------------+--------------------------------------+----------+"
  put 1 34 "${reset}Keys: 1 desktop, 2 hide menu, 3 show menu, s status, q poweroff"
}

status_screen() {
  printf "${reset}${cyan}${black}${esc}[2J" > /dev/console
  printf "${gray}${black}" > /dev/console
  box 8 5 64 14 "AuroraOS Linux Status"
  put 11 8 "This is now booted on a Linux kernel."
  put 11 10 "Base: Alpine Linux initramfs"
  put 11 11 "Kernel: $(uname -r 2>/dev/null)"
  put 11 12 "QEMU target: x86_64 now, Raspberry Pi image path next"
  put 11 14 "Press 1 to return to desktop. Press q to poweroff."
}

desktop
while true; do
  key="$(dd bs=1 count=1 2>/dev/null < /dev/console)"
  case "$key" in
    1) desktop ;;
    2) printf "${reset}${cyan}${black}${esc}[2J" > /dev/console; taskbar ;;
    3) desktop ;;
    s) status_screen ;;
    q) poweroff -f ;;
  esac
done
""",
        encoding="utf-8",
    )
    init.chmod(0o755)

    if OUT.exists():
        OUT.unlink()
    build_cpio(ROOTFS, OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
