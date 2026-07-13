from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/folder1/Desktop/Screenshot 2026-06-19 at 10.41.35\u202fPM.png")
OUT = ROOT / "assets" / "icons" / "provided"
OUT.mkdir(parents=True, exist_ok=True)

# Crops from the user-provided reference screenshot. These are treated as
# provided project assets, not Microsoft system assets.
CROPS = {
    "provided-title-square": (43, 43, 38, 38),
    "provided-tool-home": (76, 300, 32, 32),
    "provided-tool-remove-bg": (74, 357, 36, 36),
    "provided-tool-editor": (74, 421, 36, 36),
    "provided-tool-converter": (74, 482, 42, 38),
    "provided-tool-texture": (74, 542, 36, 36),
    "provided-tool-ide": (74, 604, 36, 36),
    "provided-card-bg": (377, 596, 62, 50),
    "provided-card-editor": (1010, 588, 54, 54),
    "provided-card-converter": (377, 822, 54, 42),
    "provided-card-texture": (1010, 822, 54, 54),
    "provided-card-ide": (375, 1054, 72, 72),
}


def nearest_square(img: Image.Image, size: int = 64) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.thumbnail((size, size), Image.Resampling.NEAREST)
    x = (size - img.width) // 2
    y = (size - img.height) // 2
    canvas.alpha_composite(img, (x, y))
    return canvas


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source screenshot: {SOURCE}")

    src = Image.open(SOURCE).convert("RGBA")
    written = []
    for name, (x, y, w, h) in CROPS.items():
        crop = src.crop((x, y, x + w, y + h))
        raw_path = OUT / f"{name}-raw.png"
        icon_path = OUT / f"{name}.png"
        crop.save(raw_path)
        nearest_square(crop).save(icon_path)
        written.append(icon_path)

    print(f"Extracted {len(written)} provided icons into {OUT}")


if __name__ == "__main__":
    main()
