from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 4
SIZE = 32

COLORS = {
    "black": (0, 0, 0, 255),
    "white": (255, 255, 255, 255),
    "gray": (192, 192, 192, 255),
    "dark": (64, 64, 64, 255),
    "blue": (11, 22, 143, 255),
    "cyan": (0, 120, 212, 255),
    "teal": (47, 143, 138, 255),
    "yellow": (235, 190, 58, 255),
    "green": (46, 145, 84, 255),
    "red": (210, 70, 65, 255),
    "purple": (126, 76, 160, 255),
}


def new_icon():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def save(name, img):
    img = img.resize((SIZE * SCALE, SIZE * SCALE), Image.Resampling.NEAREST)
    img.save(OUT / f"{name}.png")


def rect(draw, xy, fill, outline="black"):
    draw.rectangle(xy, fill=COLORS[fill], outline=COLORS[outline])


def explorer():
    img = new_icon()
    d = ImageDraw.Draw(img)
    rect(d, (3, 8, 28, 25), "yellow")
    rect(d, (3, 6, 13, 10), "yellow")
    d.line((4, 11, 27, 11), fill=COLORS["white"])
    d.line((28, 9, 28, 25), fill=COLORS["dark"])
    d.line((3, 25, 28, 25), fill=COLORS["dark"])
    save("aurora-explorer", img)


def package_center():
    img = new_icon()
    d = ImageDraw.Draw(img)
    rect(d, (6, 7, 25, 25), "gray")
    rect(d, (9, 4, 22, 10), "yellow")
    d.rectangle((10, 13, 14, 17), fill=COLORS["blue"])
    d.rectangle((17, 13, 21, 17), fill=COLORS["green"])
    d.rectangle((10, 20, 14, 23), fill=COLORS["red"])
    d.rectangle((17, 20, 21, 23), fill=COLORS["purple"])
    save("aurora-package-center", img)


def terminal():
    img = new_icon()
    d = ImageDraw.Draw(img)
    rect(d, (4, 6, 27, 24), "black")
    d.line((7, 10, 11, 14), fill=COLORS["green"])
    d.line((7, 18, 11, 14), fill=COLORS["green"])
    d.rectangle((14, 18, 22, 19), fill=COLORS["green"])
    save("aurora-terminal", img)


def pi_tools():
    img = new_icon()
    d = ImageDraw.Draw(img)
    rect(d, (8, 8, 23, 23), "green")
    for p in range(10, 23, 4):
        d.line((p, 4, p, 7), fill=COLORS["black"])
        d.line((p, 24, p, 28), fill=COLORS["black"])
        d.line((4, p, 7, p), fill=COLORS["black"])
        d.line((24, p, 28, p), fill=COLORS["black"])
    rect(d, (12, 12, 19, 19), "teal")
    save("aurora-pi-tools", img)


def settings():
    img = new_icon()
    d = ImageDraw.Draw(img)
    rect(d, (5, 7, 26, 24), "gray")
    d.rectangle((8, 10, 23, 12), fill=COLORS["blue"])
    d.rectangle((8, 15, 20, 17), fill=COLORS["green"])
    d.rectangle((8, 20, 17, 22), fill=COLORS["red"])
    save("aurora-settings", img)


def control_panel():
    img = new_icon()
    d = ImageDraw.Draw(img)
    rect(d, (5, 5, 26, 26), "gray")
    for x in (9, 17):
        for y in (9, 17):
            rect(d, (x, y, x + 5, y + 5), "cyan")
    save("aurora-control-panel", img)


for fn in [explorer, package_center, terminal, pi_tools, settings, control_panel]:
    fn()

print(f"Generated icons in {OUT}")
