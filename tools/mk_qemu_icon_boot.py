from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "aurora-icon-gui.img"
PNG = ROOT / "build" / "aurora-icon-gui-reference.png"
ICONS = ROOT / "assets" / "icons" / "system"
FONT_REGULAR = ROOT / "MSW98UI-Regular copy.ttf"
FONT_BOLD = ROOT / "MSW98UI-Bold copy.ttf"
FONT = ImageFont.truetype(str(FONT_REGULAR), 14) if FONT_REGULAR.exists() else ImageFont.load_default()
FONT_B = ImageFont.truetype(str(FONT_BOLD), 15) if FONT_BOLD.exists() else ImageFont.load_default()

W, H = 640, 480
FRAME_SIZE = W * H
FRAME_SECTORS = FRAME_SIZE // 512
BANK_SIZE = 65536

EGA = [
    (0, 0, 0),
    (0, 0, 170),
    (0, 170, 0),
    (0, 170, 170),
    (170, 0, 0),
    (170, 0, 170),
    (170, 85, 0),
    (170, 170, 170),
    (85, 85, 85),
    (85, 85, 255),
    (85, 255, 85),
    (85, 255, 255),
    (255, 85, 85),
    (255, 85, 255),
    (255, 255, 85),
    (255, 255, 255),
]


def nearest_ega(rgb):
    r, g, b = rgb
    return min(
        range(len(EGA)),
        key=lambda i: (r - EGA[i][0]) ** 2 + (g - EGA[i][1]) ** 2 + (b - EGA[i][2]) ** 2,
    )


def draw_bevel(d, box, fill=(170, 170, 170), title=None):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=fill, outline=(0, 0, 0))
    d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=(255, 255, 255))
    d.line((x0 + 1, y0 + 1, x0 + 1, y1 - 1), fill=(255, 255, 255))
    d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=(85, 85, 85))
    d.line((x1 - 1, y0 + 1, x1 - 1, y1 - 1), fill=(85, 85, 85))
    if title:
        d.rectangle((x0 + 2, y0 + 2, x1 - 2, y0 + 22), fill=(0, 0, 170))
        d.text((x0 + 8, y0 + 5), title, fill=(255, 255, 255), font=FONT_B)


def paste_icon(base, name, x, y, size=32):
    icon = Image.open(ICONS / f"{name}-32.png").convert("RGBA")
    icon = icon.resize((size, size), Image.Resampling.NEAREST)
    base.alpha_composite(icon, (x, y))


def draw_label(d, x, y, label, selected=False):
    if selected:
        d.rectangle((x - 2, y - 1, x + len(label) * 7 + 4, y + 14), fill=(0, 0, 170))
        d.text((x, y), label, fill=(255, 255, 255), font=FONT)
    else:
        d.text((x, y), label, fill=(0, 0, 0), font=FONT)


def draw_desktop_icon(img, d, icon_name, label, x, y, selected=False):
    paste_icon(img, icon_name, x + 8, y, 32)
    parts = label.split("\\n")
    for i, part in enumerate(parts):
        draw_label(d, x, y + 36 + i * 15, part, selected and i == 0)


def draw_cursor(d, x, y):
    white = (255, 255, 255)
    black = (0, 0, 0)
    pts = [
        (x, y),
        (x, y + 26),
        (x + 6, y + 20),
        (x + 10, y + 30),
        (x + 15, y + 28),
        (x + 11, y + 18),
        (x + 21, y + 18),
    ]
    d.polygon(pts, fill=white, outline=black)
    d.line((x + 2, y + 5, x + 2, y + 21), fill=black)
    d.line((x + 3, y + 5, x + 17, y + 17), fill=white)


def bevel_button(d, box, label, pressed=False):
    x0, y0, x1, y1 = box
    d.rectangle(box, fill=(170, 170, 170), outline=(0, 0, 0))
    if pressed:
        d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=(85, 85, 85))
        d.line((x0 + 1, y0 + 1, x0 + 1, y1 - 1), fill=(85, 85, 85))
        d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=(255, 255, 255))
        d.line((x1 - 1, y0 + 1, x1 - 1, y1 - 1), fill=(255, 255, 255))
    else:
        d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=(255, 255, 255))
        d.line((x0 + 1, y0 + 1, x0 + 1, y1 - 1), fill=(255, 255, 255))
        d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=(85, 85, 85))
        d.line((x1 - 1, y0 + 1, x1 - 1, y1 - 1), fill=(85, 85, 85))
    tw = d.textlength(label, font=FONT)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + 5), label, fill=(0, 0, 0), font=FONT)


def window_buttons(d, x, y):
    bevel_button(d, (x, y, x + 17, y + 17), "?")
    bevel_button(d, (x + 20, y, x + 37, y + 17), "X")


def title_buttons(d, x, y):
    bevel_button(d, (x, y, x + 16, y + 16), "_")
    bevel_button(d, (x + 18, y, x + 34, y + 16), "□")
    bevel_button(d, (x + 36, y, x + 52, y + 16), "X")


def draw_dialog(img, d, title, lines, icon="settings", buttons=("OK",), wide=False):
    x0, y0, x1, y1 = (144, 118, 520, 360) if wide else (174, 136, 500, 330)
    draw_bevel(d, (x0, y0, x1, y1), title=title)
    if icon:
        paste_icon(img, icon, x0 + 24, y0 + 48, 32)
        text_x = x0 + 72
    else:
        text_x = x0 + 24
    y = y0 + 48
    for line in lines:
        d.text((text_x, y), line, fill=(0, 0, 0), font=FONT)
        y += 22
    bx = x1 - 24 - len(buttons) * 76
    by = y1 - 36
    for button in buttons:
        bevel_button(d, (bx, by, bx + 66, by + 22), button)
        bx += 76


def draw_app_window(img, d, title, app):
    x0, y0, x1, y1 = 52, 34, 606, 430
    draw_bevel(d, (x0, y0, x1, y1))
    d.rectangle((x0 + 3, y0 + 3, x1 - 3, y0 + 23), fill=(0, 0, 170))
    icon_name = {
        "browser": "package",
        "terminal": "terminal",
        "package": "package-center",
        "explorer": "explorer",
        "settings": "settings",
        "control": "control-panel",
        "features": "package-center",
    }.get(app, "settings")
    paste_icon(img, icon_name, x0 + 8, y0 + 6, 14)
    d.text((x0 + 28, y0 + 7), title, fill=(255, 255, 255), font=FONT_B)
    title_buttons(d, x1 - 53, y0 + 5)
    d.text((x0 + 10, y0 + 34), "File   Edit   View   Tools   Help", fill=(0, 0, 0), font=FONT)
    draw_bevel(d, (x0 + 6, y0 + 58, x1 - 6, y0 + 90))
    bevel_button(d, (x0 + 14, y0 + 64, x0 + 74, y0 + 84), "Back")
    bevel_button(d, (x0 + 80, y0 + 64, x0 + 148, y0 + 84), "Forward")
    bevel_button(d, (x0 + 154, y0 + 64, x0 + 214, y0 + 84), "Home")
    d.rectangle((x0 + 226, y0 + 64, x1 - 18, y0 + 84), fill=(255, 255, 255), outline=(85, 85, 85))

    body = (x0 + 6, y0 + 94, x1 - 6, y1 - 28)
    d.rectangle(body, fill=(255, 255, 255), outline=(85, 85, 85))
    bx0, by0, bx1, by1 = body

    if app == "browser":
        d.text((x0 + 234, y0 + 68), "aurora://start/firefox", fill=(0, 0, 0), font=FONT)
        paste_icon(img, "package", bx0 + 24, by0 + 24, 48)
        d.text((bx0 + 92, by0 + 26), "Firefox", fill=(0, 0, 0), font=FONT_B)
        d.text((bx0 + 92, by0 + 52), "Installed as the default AuroraOS 98 browser", fill=(0, 0, 0), font=FONT)
        d.text((bx0 + 92, by0 + 82), "Full graphical rootfs command:", fill=(0, 0, 0), font=FONT)
        d.rectangle((bx0 + 92, by0 + 106, bx1 - 32, by0 + 136), fill=(192, 192, 192), outline=(85, 85, 85))
        d.text((bx0 + 104, by0 + 114), "/usr/bin/aurora-open-firefox", fill=(0, 0, 0), font=FONT)
        d.text((bx0 + 92, by0 + 164), "This framebuffer VM shows the shell path.", fill=(0, 0, 0), font=FONT)
        d.text((bx0 + 92, by0 + 188), "Real Firefox needs the full Wayland Linux rootfs.", fill=(0, 0, 0), font=FONT)
    elif app == "terminal":
        d.text((x0 + 234, y0 + 68), "aurora-terminal", fill=(0, 0, 0), font=FONT)
        d.rectangle((bx0 + 10, by0 + 10, bx1 - 10, by1 - 10), fill=(0, 0, 0), outline=(0, 0, 0))
        lines = [
            "AuroraOS 98 Terminal",
            "",
            "$ uname -a",
            "Linux aurora 6.18.35-virt x86_64",
            "$ echo $AURORA_PROFILE",
            "serenity-framebuffer",
            "$ firefox",
            "Firefox installed in full graphical rootfs",
            "$ _",
        ]
        yy = by0 + 22
        for line in lines:
            d.text((bx0 + 22, yy), line, fill=(85, 255, 85), font=FONT)
            yy += 22
    elif app == "package":
        d.text((x0 + 234, y0 + 68), "Installed Apps", fill=(0, 0, 0), font=FONT)
        headers = ["Application", "Source", "Status"]
        xs = [bx0 + 24, bx0 + 250, bx0 + 390]
        for x, text in zip(xs, headers):
            d.text((x, by0 + 18), text, fill=(0, 0, 0), font=FONT_B)
        rows = [
            ("Firefox", "Native", "Installed"),
            ("100 Features", "Aurora", "Installed"),
            ("Chromium", "Native", "Available"),
            ("LibreOffice", "Native", "Profile"),
            ("GIMP", "Native", "Profile"),
        ]
        yy = by0 + 50
        for i, row in enumerate(rows):
            if i == 0:
                d.rectangle((bx0 + 14, yy - 4, bx1 - 18, yy + 18), fill=(0, 0, 170))
                fill = (255, 255, 255)
            else:
                fill = (0, 0, 0)
            for x, text in zip(xs, row):
                d.text((x, yy), text, fill=fill, font=FONT)
            yy += 28
    elif app == "explorer":
        d.text((x0 + 234, y0 + 68), "C:\\Applications", fill=(0, 0, 0), font=FONT)
        items = [
            ("computer", "My Computer", 30, 26),
            ("folder", "Documents", 150, 26),
            ("settings", "Control Panel", 270, 26),
            ("package", "Firefox", 390, 26),
            ("package-center", "Package Center", 30, 130),
            ("terminal", "Aurora Terminal", 170, 130),
            ("package-center", "Features", 320, 130),
        ]
        for icon, label, xx, yy in items:
            draw_desktop_icon(img, d, icon, label, bx0 + xx, by0 + yy, selected=(label == "Firefox"))
    elif app == "features":
        d.text((x0 + 234, y0 + 68), "aurora://features", fill=(0, 0, 0), font=FONT)
        d.text((bx0 + 22, by0 + 18), "AuroraOS 98 Feature Catalog", fill=(0, 0, 0), font=FONT_B)
        d.text((bx0 + 22, by0 + 44), "100 scoped OS features are installed in:", fill=(0, 0, 0), font=FONT)
        d.rectangle((bx0 + 22, by0 + 66, bx1 - 22, by0 + 94), fill=(192, 192, 192), outline=(85, 85, 85))
        d.text((bx0 + 34, by0 + 74), "/etc/aurora/feature-catalog.toml", fill=(0, 0, 0), font=FONT)
        groups = [
            ("Shell + UI", "20 features"),
            ("Apps + Package Center", "15 features"),
            ("Firefox/QEMU runtime", "10 features"),
            ("Linux base + rootfs", "15 features"),
            ("Raspberry Pi tools", "7 features"),
            ("Serenity behavior port", "8 features"),
            ("Assets + QA", "12 features"),
            ("Docs + build checks", "13 features"),
        ]
        yy = by0 + 114
        for name, count in groups:
            d.rectangle((bx0 + 22, yy - 4, bx1 - 28, yy + 24), fill=(192, 192, 192), outline=(85, 85, 85))
            d.text((bx0 + 36, yy + 2), name, fill=(0, 0, 0), font=FONT_B)
            d.text((bx1 - 140, yy + 2), count, fill=(0, 0, 0), font=FONT)
            yy += 34
    else:
        d.text((x0 + 234, y0 + 68), "aurora://control-panel", fill=(0, 0, 0), font=FONT)
        panels = [
            ("Display", "Pixel scale, title bars, desktop color"),
            ("Mouse", "Pointer speed, buttons, USB tablet"),
            ("Keyboard", "Repeat rate, shortcuts"),
            ("Network", "NetworkManager adapters"),
            ("Wi-Fi", "Scan and connect wireless networks"),
            ("Sound", "PipeWire devices"),
            ("Packages", "Native, Flatpak, AppImage"),
            ("Features", "100-item AuroraOS capability catalog"),
            ("Updates", "System update policy"),
        ]
        yy = by0 + 20
        for name, desc in panels:
            d.rectangle((bx0 + 22, yy - 4, bx1 - 28, yy + 28), fill=(192, 192, 192), outline=(85, 85, 85))
            d.text((bx0 + 36, yy + 2), name, fill=(0, 0, 0), font=FONT_B)
            d.text((bx0 + 150, yy + 2), desc, fill=(0, 0, 0), font=FONT)
            yy += 42

    d.text((x0 + 10, y1 - 20), "Ready", fill=(0, 0, 0), font=FONT)


def build_frame(show_start=True, status=False, show_cursor=True, start_selected=0, submenu_selected=0, dialog=None, tab=0):
    img = Image.new("RGBA", (W, H), (0, 170, 170, 255))
    d = ImageDraw.Draw(img)
    active_tab = tab

    draw_desktop_icon(img, d, "computer", "My Computer", 24, 8, False)
    draw_desktop_icon(img, d, "network", "Network\\nNeighborhood", 24, 88, False)
    draw_desktop_icon(img, d, "recycle", "Recycle Bin", 24, 182, False)

    # Background System Properties window.
    sx0, sy0, sx1, sy1 = 228, 4, 632, 438
    draw_bevel(d, (sx0, sy0, sx1, sy1))
    d.rectangle((sx0 + 3, sy0 + 3, sx1 - 3, sy0 + 23), fill=(128, 128, 128))
    d.text((sx0 + 9, sy0 + 6), "System Properties", fill=(255, 255, 255), font=FONT_B)
    window_buttons(d, sx1 - 41, sy0 + 5)
    tabs = ["General", "Device Manager", "Hardware Profiles", "Performance"]
    tx = sx0 + 12
    for i, tab in enumerate(tabs):
        tw = int(d.textlength(tab, font=FONT)) + 22
        fill = (192, 192, 192) if i == active_tab else (170, 170, 170)
        d.rectangle((tx, sy0 + 32, tx + tw, sy0 + 56), fill=fill, outline=(0, 0, 0))
        d.line((tx + 1, sy0 + 33, tx + tw - 1, sy0 + 33), fill=(255, 255, 255))
        d.text((tx + 10, sy0 + 38), tab, fill=(0, 0, 0), font=FONT)
        tx += tw + 2
    d.rectangle((sx0 + 12, sy0 + 57, sx1 - 10, sy1 - 46), fill=(170, 170, 170), outline=(0, 0, 0))
    if active_tab == 0:
        draw_bevel(d, (sx0 + 82, sy0 + 108, sx0 + 170, sy0 + 198), fill=(170, 170, 170))
        d.rectangle((sx0 + 104, sy0 + 126, sx0 + 150, sy0 + 168), fill=(0, 170, 170), outline=(0, 0, 0))
        d.rectangle((sx0 + 112, sy0 + 133, sx0 + 126, sy0 + 146), fill=(255, 85, 85))
        d.rectangle((sx0 + 130, sy0 + 133, sx0 + 144, sy0 + 146), fill=(255, 255, 85))
        d.rectangle((sx0 + 112, sy0 + 150, sx0 + 126, sy0 + 163), fill=(85, 85, 255))
        d.rectangle((sx0 + 130, sy0 + 150, sx0 + 144, sy0 + 163), fill=(85, 255, 85))
        tab_lines = [
            (sx0 + 214, sy0 + 82, "System:"),
            (sx0 + 236, sy0 + 104, "AuroraOS 98"),
            (sx0 + 236, sy0 + 124, "Serenity framebuffer profile"),
            (sx0 + 236, sy0 + 144, "Linux base 0.1.2026"),
            (sx0 + 214, sy0 + 192, "Registered to:"),
            (sx0 + 236, sy0 + 214, "AuroraOS Developer"),
            (sx0 + 236, sy0 + 236, "00023-OEM-AURORA-PI"),
            (sx0 + 40, sy0 + 286, "Manufactured and supported by:"),
            (sx0 + 236, sy0 + 286, "AuroraOS Project"),
            (sx0 + 236, sy0 + 310, "Linux + Serenity UI behavior"),
            (sx0 + 236, sy0 + 334, "Firefox browser installed"),
            (sx0 + 236, sy0 + 358, "Pi 4 / Pi 5 / x86-64"),
        ]
    elif active_tab == 1:
        tab_lines = [
            (sx0 + 42, sy0 + 92, "Device Manager:"),
            (sx0 + 64, sy0 + 122, "+ System devices"),
            (sx0 + 64, sy0 + 146, "+ Raspberry Pi GPIO"),
            (sx0 + 64, sy0 + 170, "+ VirtIO display adapter"),
            (sx0 + 64, sy0 + 194, "+ USB tablet pointer"),
            (sx0 + 64, sy0 + 218, "+ Network adapter"),
        ]
    elif active_tab == 2:
        tab_lines = [
            (sx0 + 42, sy0 + 92, "Hardware profiles:"),
            (sx0 + 64, sy0 + 122, "Current profile: QEMU laptop preview"),
            (sx0 + 64, sy0 + 150, "Targets: Raspberry Pi 4, Pi 5, x86-64 PC"),
            (sx0 + 64, sy0 + 178, "Graphics: Serenity-style framebuffer shell"),
        ]
    else:
        tab_lines = [
            (sx0 + 42, sy0 + 92, "Performance:"),
            (sx0 + 64, sy0 + 122, "Idle shell target: under 700 MB RAM"),
            (sx0 + 64, sy0 + 150, "Input: keyboard and mouse active"),
            (sx0 + 64, sy0 + 178, "Boot mode: Linux initramfs + Firefox installed"),
        ]
    for x, y, text in tab_lines:
        d.text((x, y), text, fill=(0, 0, 0), font=FONT)
    bevel_button(d, (sx0 + 250, sy1 - 34, sx0 + 326, sy1 - 12), "OK")
    bevel_button(d, (sx0 + 336, sy1 - 34, sx0 + 404, sy1 - 12), "Cancel")

    # Foreground My Computer window.
    wx0, wy0, wx1, wy1 = 70, 52, 322, 268
    draw_bevel(d, (wx0, wy0, wx1, wy1))
    d.rectangle((wx0 + 3, wy0 + 3, wx1 - 3, wy0 + 23), fill=(128, 128, 128))
    paste_icon(img, "computer", wx0 + 8, wy0 + 6, 14)
    d.text((wx0 + 27, wy0 + 7), "My Computer", fill=(255, 255, 255), font=FONT_B)
    title_buttons(d, wx1 - 53, wy0 + 5)
    d.text((wx0 + 10, wy0 + 33), "File   Edit   View   Help", fill=(85, 85, 85), font=FONT)
    d.rectangle((wx0 + 6, wy0 + 70, wx1 - 6, wy1 - 12), fill=(255, 255, 255), outline=(85, 85, 85))
    drive_items = [
        ("floppy", "3½ Floppy [A:]", 102, 96),
        ("disk", "[C:]", 174, 101),
        ("cdrom", "Discordmes...\\n[D:]", 254, 94),
        ("folder", "Control", 103, 164),
        ("folder", "Printers", 181, 164),
    ]
    for icon_name, label, x, y in drive_items:
        paste_icon(img, icon_name, x, y, 30)
        lines = label.split("\\n")
        for j, line in enumerate(lines):
            d.text((x - 20, y + 35 + j * 14), line, fill=(0, 0, 0), font=FONT)

    if show_start:
        # Start menu and Programs submenu.
        mx0, my0, mx1, my1 = 0, 186, 164, 450
        d.rectangle((mx0, my0, mx1, my1), fill=(170, 170, 170), outline=(0, 0, 0))
        d.line((mx0 + 1, my0 + 1, mx1 - 1, my0 + 1), fill=(255, 255, 255))
        d.line((mx0 + 1, my0 + 1, mx0 + 1, my1 - 1), fill=(255, 255, 255))
        d.rectangle((mx0 + 2, my0 + 2, mx0 + 28, my1 - 2), fill=(0, 0, 170))
        rail_font = ImageFont.truetype(str(FONT_BOLD), 19) if FONT_BOLD.exists() else FONT_B
        rail = Image.new("RGBA", (118, 24), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rail)
        rd.text((0, 1), "AuroraOS98", fill=(255, 255, 255), font=rail_font)
        img.alpha_composite(rail.rotate(90, expand=True), (mx0 + 2, my1 - 122))
        start_items = [
            ("package-center", "Programs", True),
            ("documents", "Documents", True),
            ("settings", "Settings", True),
            ("search", "Find", True),
            ("help", "Help", False),
            ("run", "Run...", False),
            ("shutdown", "Shut Down...", False),
        ]
        yy = my0 + 16
        for i, (icon_name, label, arrow) in enumerate(start_items):
            if i == start_selected:
                d.rectangle((30, yy - 4, mx1 - 6, yy + 24), fill=(0, 0, 170))
                color = (255, 255, 255)
            else:
                color = (0, 0, 0)
            if i == 6:
                d.line((30, yy - 8, mx1 - 8, yy - 8), fill=(255, 255, 255))
                d.line((30, yy - 7, mx1 - 8, yy - 7), fill=(85, 85, 85))
            paste_icon(img, icon_name, 42, yy, 20)
            d.text((70, yy + 4), label, fill=color, font=FONT)
            if arrow:
                d.text((150, yy + 4), ">", fill=color, font=FONT_B)
            yy += 36

        if start_selected == 0:
            smx0, smy0, smx1, smy1 = 164, 186, 304, 318
            d.rectangle((smx0, smy0, smx1, smy1), fill=(170, 170, 170), outline=(0, 0, 0))
            submenu = [
                ("package-center", "AuroraOS 98", True),
                ("package-center", "Accessories", True),
                ("package-center", "StartUp", True),
                ("package", "Firefox", False),
                ("terminal", "MS-DOS Prompt", False),
                ("explorer", "Windows Explorer", False),
            ]
            yy = smy0 + 10
            for i, (icon_name, label, arrow) in enumerate(submenu):
                if i == submenu_selected:
                    d.rectangle((smx0 + 4, yy - 3, smx1 - 5, yy + 21), fill=(0, 0, 170))
                    color = (255, 255, 255)
                else:
                    color = (0, 0, 0)
                paste_icon(img, icon_name, smx0 + 9, yy, 18)
                d.text((smx0 + 36, yy + 4), label, fill=color, font=FONT)
                if arrow:
                    d.text((smx1 - 14, yy + 4), ">", fill=color, font=FONT_B)
                yy += 22

        if show_cursor:
            draw_cursor(d, 131, 204)

    # Taskbar.
    draw_bevel(d, (0, 450, 639, 479))
    bevel_button(d, (2, 454, 52, 476), "Start", pressed=show_start)
    paste_icon(img, "taskbar", 5, 457, 14)
    draw_bevel(d, (58, 454, 218, 476))
    paste_icon(img, "computer", 64, 458, 14)
    d.text((84, 459), "My Computer", fill=(0, 0, 0), font=FONT)
    draw_bevel(d, (556, 454, 636, 476))
    paste_icon(img, "audio", 560, 458, 14)
    d.text((592, 459), "2:54 AM", fill=(0, 0, 0), font=FONT)


    if status:
        draw_bevel(d, (164, 142, 500, 330), title="AuroraOS 98 Status")
        d.text((194, 188), "Linux kernel is running.", fill=(0, 0, 0), font=FONT)
        d.text((194, 214), "Userland profile: Serenity-inspired", fill=(0, 0, 0), font=FONT)
        d.text((194, 240), "Browser installed: Firefox", fill=(0, 0, 0), font=FONT)
        d.text((194, 266), "Display: QEMU framebuffer (/dev/fb0)", fill=(0, 0, 0), font=FONT)
        bevel_button(d, (392, 294, 474, 318), "OK")

    dialogs = {
        "package": ("Aurora Package Center", ["Installed: Firefox web browser.", "Native packages, Flatpak, AppImage,", "optional installers, Chromium available."], "package-center", ("Install", "Close")),
        "documents": ("Documents", ["Serenity-style file workflow.", "Backed by Aurora Explorer on Linux."], "documents", ("Open", "Close")),
        "settings": ("System Settings", ["Serenity-style settings layout,", "Linux backends: DRM, input, network,", "PipeWire, Pi hardware, packages."], "settings", ("Open", "Close")),
        "find": ("Find", ["Search target:", "Files, apps, settings, packages"], "search", ("Find Now", "Cancel")),
        "help": ("Aurora Help", ["AuroraOS 98 keeps Linux underneath.", "Framebuffer UI follows Serenity-style", "classic desktop behavior."], "help", ("OK",)),
        "run": ("Run", ["Open:", "firefox"], "run", ("OK", "Cancel")),
        "suspend": ("Suspend AuroraOS", ["Suspend is not available in QEMU.", "Use Shut Down or press q."], "shutdown", ("OK",)),
        "shutdown": ("Shut Down AuroraOS", ["Press q to power off this QEMU VM.", "Esc or Cancel returns to desktop."], "shutdown", ("Shut Down", "Cancel")),
        "terminal": ("Aurora Terminal", ["$ uname -a", "Linux aurora 6.18.35-virt", "$ profile=serenity-framebuffer"], "terminal", ("Close",)),
        "explorer": ("Aurora Explorer", ["Home  Documents  Downloads", "Applications  Control Panel", "Firefox  Package Center  Pi Tools"], "explorer", ("Open", "Close")),
        "control": ("Control Panel", ["Display  Mouse  Keyboard", "Network  Sound  Pi Hardware", "Packages  Updates"], "control-panel", ("Open", "Close")),
        "drive": ("Drive Properties", ["Volume: Aurora System", "Filesystem: initramfs overlay", "Status: mounted read-only preview"], "disk", ("OK",)),
        "network": ("Network Neighborhood", ["NetworkManager backend available.", "Wi-Fi Connection can scan, connect,", "disconnect, and show status via nmcli."], "network", ("Wi-Fi", "OK")),
        "recycle": ("Recycle Bin", ["Recycle Bin is empty."], "recycle", ("OK",)),
        "about": ("About AuroraOS 98", ["Linux underneath.", "Serenity-style framebuffer base.", "Firefox and Linux apps included."], "computer", ("OK",)),
        "browser": ("Firefox", ["AuroraOS 98 web browser.", "Firefox is installed as default.", "Full browser launches in the full rootfs;", "this framebuffer build proves the shell path."], "package", ("Open", "Close")),
        "features": ("Feature Catalog", ["100 AuroraOS 98 features installed.", "Press F to open this catalog.", "Stored at /etc/aurora/feature-catalog.toml"], "package-center", ("Open", "Close")),
    }
    if dialog in dialogs:
        title, lines, icon, buttons = dialogs[dialog]
        if dialog in {"browser", "terminal", "package", "explorer", "settings", "control", "features"}:
            draw_app_window(img, d, title, dialog)
        else:
            draw_dialog(img, d, title, lines, icon, buttons, wide=False)

    return img


def boot_sector():
    b = bytearray(512)
    o = 0

    def u8(v):
        nonlocal o
        if o >= 510:
            raise RuntimeError("boot sector overflow")
        b[o] = v & 0xFF
        o += 1

    def u16(v):
        u8(v)
        u8(v >> 8)

    def patch(pos, v):
        b[pos] = v & 0xFF
        b[pos + 1] = (v >> 8) & 0xFF

    def mov_mem_word(addr_patch, value):
        u8(0xC7)
        u8(0x06)
        pos = o
        u16(0)
        u16(value)
        return pos

    def set_lba_and_count(lba, sectors):
        patches = []
        patches.append(mov_mem_word(None, sectors))  # dap_count
        patches.append(mov_mem_word(None, lba & 0xFFFF))  # dap_lba low
        patches.append(mov_mem_word(None, (lba >> 16) & 0xFFFF))
        return patches

    u8(0xFA)                              # cli
    u8(0x31); u8(0xC0)                    # xor ax, ax
    u8(0x8E); u8(0xD8)                    # mov ds, ax
    u8(0x8E); u8(0xD0)                    # mov ss, ax
    u8(0xBC); u16(0x7C00)                 # mov sp, 7c00
    u8(0x88); u8(0x16); drive_patch = o; u16(0)  # mov [drive], dl
    u8(0xFB)                              # sti

    u8(0xB8); u16(0x4F02)                 # mov ax, 4f02h
    u8(0xBB); u16(0x0101)                 # mov bx, 101h, 640x480x256
    u8(0xCD); u8(0x10)                    # int 10h

    bank_patch_sets = []
    for bank in range((FRAME_SIZE + BANK_SIZE - 1) // BANK_SIZE):
        lba = 1 + bank * 128
        sectors = 128 if bank < 4 else 88
        byte_count = BANK_SIZE if bank < 4 else FRAME_SIZE - bank * BANK_SIZE
        words = byte_count // 2

        patches = set_lba_and_count(lba, sectors)
        bank_patch_sets.append((patches, bank))

        u8(0xBE); dap_ref = o; u16(0)      # mov si, dap
        u8(0x8A); u8(0x16); drive_ref = o; u16(0)  # mov dl, [drive]
        u8(0xB4); u8(0x42)                 # mov ah, 42h
        u8(0xCD); u8(0x13)                 # int 13h

        u8(0xB8); u16(0x4F05)              # mov ax, 4f05h
        u8(0xBB); u16(0x0000)              # mov bx, 0
        u8(0xBA); u16(bank)                # mov dx, bank
        u8(0xCD); u8(0x10)                 # int 10h

        u8(0x1E)                           # push ds
        u8(0xB8); u16(0x8000)              # mov ax, 8000h
        u8(0x8E); u8(0xD8)                 # mov ds, ax
        u8(0xB8); u16(0xA000)              # mov ax, a000h
        u8(0x8E); u8(0xC0)                 # mov es, ax
        u8(0x31); u8(0xF6)                 # xor si, si
        u8(0x31); u8(0xFF)                 # xor di, di
        u8(0xB9); u16(words)               # mov cx, words
        u8(0xFC)                           # cld
        u8(0xF3); u8(0xA5)                 # rep movsw
        u8(0x1F)                           # pop ds

    u8(0xF4)                               # hlt
    u8(0xEB); u8(0xFD)                     # jmp $

    drive = o
    u8(0)
    dap = o
    u8(0x10); u8(0)
    dap_count = o
    u16(0)
    u16(0x0000)                            # buffer offset
    u16(0x8000)                            # buffer segment
    dap_lba = o
    u16(1)
    u16(0)
    u16(0)
    u16(0)

    patch(drive_patch, 0x7C00 + drive)
    # Patch all DAP references and drive references by scanning instruction operands.
    for i in range(0, len(b) - 2):
        if b[i] == 0xBE and b[i + 1] == 0 and b[i + 2] == 0:
            patch(i + 1, 0x7C00 + dap)
        if b[i] == 0x16 and b[i + 1] == 0 and b[i + 2] == 0:
            patch(i + 1, 0x7C00 + drive)

    # Patch mov word [addr], value instructions in order:
    # each bank emits dap_count, dap_lba low, dap_lba high.
    patch_targets = []
    for i in range(0, len(b) - 5):
        if b[i] == 0xC7 and b[i + 1] == 0x06 and b[i + 2] == 0 and b[i + 3] == 0:
            patch_targets.append(i + 2)
    idx = 0
    for bank in range((FRAME_SIZE + BANK_SIZE - 1) // BANK_SIZE):
        lba = 1 + bank * 128
        sectors = 128 if bank < 4 else 88
        patch(patch_targets[idx], 0x7C00 + dap_count); idx += 1
        patch(patch_targets[idx], 0x7C00 + dap_lba); idx += 1
        patch(patch_targets[idx], 0x7C00 + dap_lba + 2); idx += 1

    if o > 510:
        raise RuntimeError(f"boot sector overflow: {o}")
    b[510] = 0x55
    b[511] = 0xAA
    return bytes(b)


def main():
    img = build_frame().convert("RGB")
    PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(PNG)

    pixels = bytearray(nearest_ega(px) for px in img.getdata())
    if len(pixels) != FRAME_SIZE:
        raise RuntimeError("bad frame size")

    OUT.write_bytes(boot_sector() + bytes(pixels))
    print(f"Wrote {OUT}")
    print(f"Wrote {PNG}")


if __name__ == "__main__":
    main()
