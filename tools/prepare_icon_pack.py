from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "win95-winxp_icons-master" / "icons"
OUT = ROOT / "assets" / "icons" / "system"
OUT.mkdir(parents=True, exist_ok=True)

ICON_MAP = {
    "computer": "w2k_my_computer.ico",
    "desktop": "w2k_desktop.ico",
    "explorer": "w2k_folder_open.ico",
    "folder": "w2k_folder_closed.ico",
    "documents": "w2k_my_documents.ico",
    "package-center": "w2k_programs.ico",
    "control-panel": "w2k_control_panel.ico",
    "settings": "w2k_settings.ico",
    "help": "w2k_help.ico",
    "network": "w2k_network.ico",
    "disk": "w2k_hard_drive.ico",
    "floppy": "w2k_floppy_drive_3½.ico",
    "cdrom": "w2k_cd-rom_drive.ico",
    "recycle": "w2k_recycle_bin_empty.ico",
    "terminal": "w98_console_prompt.ico",
    "text-editor": "w2k_notepad_1.ico",
    "graphics": "w2k_paint.ico",
    "audio": "w2k_sndvol_1.ico",
    "video": "w2k_movie_clip.ico",
    "search": "w2k_search.ico",
    "shutdown": "w2k_shutdown.ico",
    "taskbar": "w2k_taskbar.ico",
    "run": "w2k_run.ico",
    "package": "w2k_default_application.ico",
    "pi-tools": "w2k_system.ico",
    "download": "wxp_downloadfolder.ico",
    "archive": "w2k_zip_file.ico",
    "executable": "w98_executable.ico",
    "installer": "w98_installer.ico",
    "generic-file": "w2k_default_document.ico",
}


def load_ico(path: Path) -> Image.Image:
    img = Image.open(path)
    sizes = sorted(getattr(img, "ico", img).sizes(), reverse=True)
    if sizes:
        img = img.ico.getimage(sizes[0])
    return img.convert("RGBA")


def save_sizes(name: str, img: Image.Image) -> None:
    for size in (16, 32, 48, 72, 128):
        resized = img.resize((size, size), Image.Resampling.NEAREST)
        resized.save(OUT / f"{name}-{size}.png")
    img.resize((128, 128), Image.Resampling.NEAREST).save(OUT / f"{name}.png")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing icon pack: {SOURCE}")

    missing = []
    for name, file_name in ICON_MAP.items():
        src = SOURCE / file_name
        if not src.exists():
            missing.append(str(src))
            continue
        save_sizes(name, load_ico(src))

    if missing:
        raise SystemExit("missing icons:\n" + "\n".join(missing))

    index = OUT / "icon-map.tsv"
    index.write_text(
        "\n".join(f"{name}\t{file_name}\tsystem/{name}.png" for name, file_name in ICON_MAP.items()) + "\n",
        encoding="utf-8",
    )
    print(f"Prepared {len(ICON_MAP)} provided system icons in {OUT}")


if __name__ == "__main__":
    main()
