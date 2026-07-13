import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "linux-base" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
import mk_qemu_icon_boot as aurora_gui  # noqa: E402


def write_bgra32(path: Path, img: Image.Image):
    data = bytearray()
    for r, g, b in img.convert("RGB").getdata():
        data.extend((b, g, r, 0))
    path.write_bytes(data)


def main():
    frames = {
        "desktop-closed.bgra32": aurora_gui.build_frame(show_start=False, show_cursor=False),
        "status.bgra32": aurora_gui.build_frame(show_start=False, status=True, show_cursor=False),
    }
    for selected in range(8):
        frames[f"desktop-open-{selected}.bgra32"] = aurora_gui.build_frame(
            show_start=True,
            show_cursor=False,
            start_selected=selected,
            submenu_selected=0,
        )
    for selected in range(6):
        frames[f"desktop-submenu-{selected}.bgra32"] = aurora_gui.build_frame(
            show_start=True,
            show_cursor=False,
            start_selected=0,
            submenu_selected=selected,
        )
    for tab in range(4):
        frames[f"system-tab-{tab}.bgra32"] = aurora_gui.build_frame(
            show_start=False,
            show_cursor=False,
            tab=tab,
        )
    for dialog in [
        "package",
        "documents",
        "settings",
        "find",
        "help",
        "run",
        "suspend",
        "shutdown",
        "terminal",
        "explorer",
        "control",
        "drive",
        "network",
        "recycle",
        "about",
        "browser",
        "features",
    ]:
        frames[f"dialog-{dialog}.bgra32"] = aurora_gui.build_frame(
            show_start=False,
            show_cursor=False,
            dialog=dialog,
        )
    for filename, base in frames.items():
        img = Image.new("RGB", (1280, 800), (0, 128, 128))
        scaled = base.convert("RGB").resize((1066, 800), Image.Resampling.NEAREST)
        img.paste(scaled, (107, 0))
        write_bgra32(OUT / filename, img)
        print(f"Wrote {OUT / filename}")


if __name__ == "__main__":
    main()
