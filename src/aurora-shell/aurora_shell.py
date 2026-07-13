#!/usr/bin/env python3
import ctypes
import sys
import subprocess
import socket
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from threading import Thread

ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = ROOT / "assets" / "icons" / "system"
FONT_REGULAR = ROOT / "MSW98UI-Regular copy.ttf"
FONT_BOLD = ROOT / "MSW98UI-Bold copy.ttf"

DESKTOP = "#008080"
FACE = "#c0c0c0"
SHADOW = "#808080"
DARK = "#000000"
LIGHT = "#ffffff"
TITLE = "#000080"


# Network and system utilities
def get_network_status():
    """Check if connected to network"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return "Connected"
    except OSError:
        return "Disconnected"


def get_hostname():
    """Get system hostname"""
    try:
        return socket.gethostname()
    except:
        return "localhost"


def launch_browser():
    """Launch default web browser"""
    try:
        subprocess.Popen(["chromium-browser", "https://google.com"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        try:
            subprocess.Popen(["firefox"], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            try:
                subprocess.Popen(["microsoft-edge", "https://google.com"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                pass


def launch_terminal():
    """Launch system terminal"""
    try:
        subprocess.Popen(["xterm"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def launch_wifi_connection():
    """Open Aurora Wi-Fi connector backed by NetworkManager."""
    commands = [
        ["xterm", "-title", "Wi-Fi Connection", "-e", "aurora-wifi-connect", "status"],
        ["aurora-wifi-connect", "status"],
    ]
    for command in commands:
        try:
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue





def register_font(path):
    if sys.platform != "darwin" or not path.exists():
        return False
    try:
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        ct = ctypes.CDLL("/System/Library/Frameworks/CoreText.framework/CoreText")
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_bool,
        ]
        cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        ct.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
        ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
        cf.CFRelease.argtypes = [ctypes.c_void_p]

        raw = str(path).encode("utf-8")
        url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
        if not url:
            return False
        ok = bool(ct.CTFontManagerRegisterFontsForURL(url, 1, None))
        cf.CFRelease(url)
        return ok
    except Exception:
        return False


class AuroraShell:
    def __init__(self):
        register_font(FONT_REGULAR)
        register_font(FONT_BOLD)

        self.root = tk.Tk()
        self.root.title("AuroraOS Shell Prototype")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)
        self.root.configure(bg=DESKTOP)
        
        self.current_path = Path.home()  # Track current file browser path

        family = "MS W98 UI" if "MS W98 UI" in set(tkfont.families(self.root)) else "TkDefaultFont"
        self.ui_font = tkfont.Font(family=family, size=11)
        self.ui_bold = tkfont.Font(family=family, size=11, weight="bold")
        self.rail_font = tkfont.Font(family=family, size=18, weight="bold")
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family=family, size=11)
            except tk.TclError:
                pass
        self.root.option_add("*Font", self.ui_font)
        self.root.option_add("*Button.Font", self.ui_font)
        self.root.option_add("*Label.Font", self.ui_font)

        self.icons = {}
        self.windows = {}
        self.start_menu = None
        self.programs_menu = None
        self.drag = None

        self.desktop = tk.Frame(self.root, bg=DESKTOP)
        self.desktop.pack(fill="both", expand=True)

        self.taskbar = tk.Frame(self.root, bg=FACE, bd=2, relief="raised", height=34)
        self.taskbar.pack(fill="x", side="bottom")
        self.taskbar.pack_propagate(False)

        self.build_desktop()
        self.build_taskbar()
        self.open_system_properties()
        self.open_my_computer()

        self.root.bind("<Escape>", lambda _e: self.hide_start())

    def icon(self, name, size=32):
        key = f"{name}-{size}"
        if key not in self.icons:
            path = ICON_DIR / f"{name}-{size}.png"
            self.icons[key] = tk.PhotoImage(file=str(path))
        return self.icons[key]

    def build_desktop(self):
        items = [
            ("computer", "My Computer", self.open_my_computer),
            ("network", "Network\nNeighborhood", self.open_network),
            ("recycle", "Recycle Bin", self.open_recycle),
        ]
        for i, (icon, label, command) in enumerate(items):
            self.desktop_icon(icon, label, 18, 14 + i * 96, command)

    def desktop_icon(self, icon_name, text, x, y, command):
        frame = tk.Frame(self.desktop, bg=DESKTOP, width=88, height=82)
        frame.place(x=x, y=y)
        label_icon = tk.Label(frame, image=self.icon(icon_name, 32), bg=DESKTOP)
        label_icon.pack()
        label_text = tk.Label(frame, text=text, fg="white", bg=DESKTOP, justify="center")
        label_text.pack()
        for widget in (frame, label_icon, label_text):
            widget.bind("<Double-Button-1>", lambda _e, cmd=command: cmd())

    def build_taskbar(self):
        self.start_button = tk.Button(
            self.taskbar,
            text=" Start",
            image=self.icon("taskbar", 16),
            compound="left",
            bd=2,
            relief="raised",
            command=self.toggle_start,
        )
        self.start_button.pack(side="left", padx=2, pady=2)

        self.task_my_computer = tk.Button(
            self.taskbar,
            text=" My Computer",
            image=self.icon("computer", 16),
            compound="left",
            bd=2,
            relief="sunken",
            command=self.open_my_computer,
            width=160,
            anchor="w",
        )
        self.task_my_computer.pack(side="left", padx=4, pady=2)

        tray = tk.Frame(self.taskbar, bg=FACE, bd=2, relief="sunken")
        tray.pack(side="right", padx=3, pady=3)
        tk.Label(tray, image=self.icon("audio", 16), bg=FACE).pack(side="left", padx=3)
        tk.Label(tray, text="2:54 AM", bg=FACE).pack(side="left", padx=8)

    def hide_start(self):
        if self.programs_menu:
            self.programs_menu.destroy()
            self.programs_menu = None
        if self.start_menu:
            self.start_menu.destroy()
            self.start_menu = None
        self.start_button.configure(relief="raised")

    def toggle_start(self):
        if self.start_menu:
            self.hide_start()
        else:
            self.show_start()

    def show_start(self):
        self.start_button.configure(relief="sunken")
        self.start_menu = tk.Frame(self.root, bg=FACE, bd=2, relief="raised")
        self.start_menu.place(x=0, y=self.root.winfo_height() - 34 - 300, width=238, height=300)

        rail = tk.Frame(self.start_menu, bg=TITLE, width=30)
        rail.pack(side="left", fill="y")
        tk.Label(rail, text="AuroraOS98", fg="white", bg=TITLE, font=self.rail_font).place(x=-35, y=205)

        body = tk.Frame(self.start_menu, bg=FACE)
        body.pack(side="left", fill="both", expand=True)
        self.menu_row(body, "package-center", "Programs", self.show_programs, arrow=True, selected=True)
        self.menu_row(body, "documents", "Documents", lambda: None, arrow=True)
        self.menu_row(body, "settings", "Settings", self.open_settings, arrow=True)
        self.menu_row(body, "search", "Find", lambda: None, arrow=True)
        self.menu_row(body, "help", "Help", lambda: None)
        self.menu_row(body, "run", "Run...", self.open_run)
        tk.Frame(body, bg=SHADOW, height=1).pack(fill="x", padx=4, pady=4)
        self.menu_row(body, "shutdown", "Suspend", lambda: None)
        self.menu_row(body, "shutdown", "Shut Down...", self.root.destroy)
        self.show_programs()

    def menu_row(self, parent, icon_name, text, command, arrow=False, selected=False):
        bg = TITLE if selected else FACE
        fg = "white" if selected else "black"
        row = tk.Frame(parent, bg=bg, height=34)
        row.pack(fill="x")
        row.pack_propagate(False)
        tk.Label(row, image=self.icon(icon_name, 16), bg=bg).pack(side="left", padx=9)
        tk.Label(row, text=text, bg=bg, fg=fg, anchor="w").pack(side="left", fill="x", expand=True)
        if arrow:
            tk.Label(row, text=">", bg=bg, fg=fg).pack(side="right", padx=6)
        row.bind("<Button-1>", lambda _e: command())
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda _e: command())

    def show_programs(self):
        if self.programs_menu:
            self.programs_menu.destroy()
        self.programs_menu = tk.Frame(self.root, bg=FACE, bd=2, relief="raised")
        self.programs_menu.place(x=236, y=self.root.winfo_height() - 34 - 300, width=210, height=200)
        rows = [
            ("globe", "Web Browser", launch_browser, False),
            ("terminal", "Terminal", launch_terminal, False),
            ("explorer", "File Manager", self.open_my_computer, False),
            ("package-center", "Package Center", None, True),
            ("settings", "Settings", self.open_settings, False),
        ]
        for icon_name, text, command, arrow in rows:
            self.menu_row(self.programs_menu, icon_name, text, command or (lambda: None), arrow=arrow)

    def window(self, key, title, x, y, w, h, icon_name="computer"):
        if key in self.windows and self.windows[key].winfo_exists():
            self.windows[key].lift()
            return self.windows[key]

        win = tk.Frame(self.desktop, bg=FACE, bd=2, relief="raised")
        win.place(x=x, y=y, width=w, height=h)
        self.windows[key] = win

        titlebar = tk.Frame(win, bg="#808080", height=24)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)
        tk.Label(titlebar, image=self.icon(icon_name, 16), bg="#808080").pack(side="left", padx=4)
        tk.Label(titlebar, text=title, fg="white", bg="#808080", font=self.ui_bold).pack(side="left")
        for text, cmd in [("X", win.destroy), ("□", None), ("_", None)]:
            tk.Button(titlebar, text=text, bd=2, relief="raised", width=2, command=cmd).pack(
                side="right", padx=1, pady=1
            )

        titlebar.bind("<ButtonPress-1>", lambda e, f=win: self.start_drag(e, f))
        titlebar.bind("<B1-Motion>", self.do_drag)
        return win

    def start_drag(self, event, frame):
        self.drag = (frame, event.x_root, event.y_root, frame.winfo_x(), frame.winfo_y())
        frame.lift()

    def do_drag(self, event):
        if not self.drag:
            return
        frame, sx, sy, fx, fy = self.drag
        frame.place(x=fx + event.x_root - sx, y=fy + event.y_root - sy)

    def open_my_computer(self):
        win = self.window("computer", f"My Computer - {self.current_path.name}", 110, 84, 550, 400, "computer")
        for child in win.winfo_children()[1:]:
            child.destroy()
        
        menubar = tk.Frame(win, bg=FACE, height=30)
        menubar.pack(fill="x")
        tk.Label(menubar, text="File   Edit   View   Help", fg=SHADOW, bg=FACE, anchor="w").pack(
            fill="x", padx=10, pady=6
        )
        
        # Location bar
        loc_frame = tk.Frame(win, bg=FACE)
        loc_frame.pack(fill="x", padx=6, pady=4)
        tk.Label(loc_frame, text="Location:", bg=FACE).pack(side="left")
        tk.Entry(loc_frame, bd=2, relief="sunken").pack(side="left", fill="x", expand=True, padx=4)
        
        # File browser pane
        pane = tk.Frame(win, bg="white", bd=2, relief="sunken")
        pane.pack(fill="both", expand=True, padx=6, pady=4)
        
        # Get current directory contents
        try:
            items = sorted(self.current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            # Limit display to 12 items
            items = items[:12]
        except PermissionError:
            items = []
        
        for i, item in enumerate(items):
            icon_name = "folder" if item.is_dir() else "file"
            label = item.name[:15] + "..." if len(item.name) > 15 else item.name
            
            f = tk.Frame(pane, bg="white")
            f.place(x=28 + (i % 4) * 120, y=22 + (i // 4) * 90, width=110, height=80)
            tk.Label(f, image=self.icon(icon_name, 32), bg="white").pack()
            
            text_label = tk.Label(f, text=label, bg="white", justify="center", wraplength=95, font=("Arial", 8))
            text_label.pack()
            
            # Handle double-click to open folder
            if item.is_dir():
                def navigate_to(path, btn=f):
                    self.current_path = path
                    self.open_my_computer()
                text_label.bind("<Double-Button-1>", lambda _e, p=item: navigate_to(p))
                f.bind("<Double-Button-1>", lambda _e, p=item: navigate_to(p))

    def open_system_properties(self):
        win = self.window("system", "System Properties", 360, 8, 620, 520, "settings")
        for child in win.winfo_children()[1:]:
            child.destroy()
        tabs = tk.Frame(win, bg=FACE)
        tabs.pack(fill="x", padx=12, pady=(14, 0))
        for tab in ["General", "Device Manager", "Hardware Profiles", "Performance"]:
            tk.Button(tabs, text=tab, bd=2, relief="raised").pack(side="left")
        body = tk.Frame(win, bg=FACE, bd=2, relief="sunken")
        body.pack(fill="both", expand=True, padx=12, pady=0)
        tk.Label(body, text="System:", bg=FACE, font=self.ui_bold).place(x=330, y=34)
        tk.Label(body, text="AuroraOS 98\nRaspberry Pi Edition\n0.1.2026", bg=FACE, justify="left").place(
            x=360, y=62
        )
        logo = tk.Frame(body, bg=DESKTOP, bd=2, relief="sunken")
        logo.place(x=92, y=70, width=116, height=96)
        for color, rx, ry in [("#ff5555", 25, 24), ("#ffff55", 56, 24), ("#5555ff", 25, 54), ("#55ff55", 56, 54)]:
            tk.Frame(logo, bg=color).place(x=rx, y=ry, width=26, height=24)
        tk.Label(body, text="Registered to:", bg=FACE, font=self.ui_bold).place(x=330, y=170)
        tk.Label(body, text="AuroraOS Developer\n00023-OEM-AURORA-PI", bg=FACE, justify="left").place(
            x=360, y=200
        )
        tk.Label(
            body,
            text="Manufactured and supported by:",
            bg=FACE,
            font=self.ui_bold,
        ).place(x=60, y=288)
        tk.Label(
            body,
            text="AuroraOS Project\nLinux + Wayland\nRaspberry Pi 4 / Pi 5\n700MB RAM target",
            bg=FACE,
            justify="left",
        ).place(x=360, y=288)
        tk.Button(win, text="OK", width=10, bd=2, relief="raised").pack(side="right", padx=12, pady=10)
        tk.Button(win, text="Cancel", width=10, bd=2, relief="raised").pack(side="right", pady=10)

    def open_terminal(self):
        win = self.window("terminal", "Aurora Terminal", 190, 160, 600, 340, "terminal")
        for child in win.winfo_children()[1:]:
            child.destroy()
        
        text = tk.Text(
            win, 
            bg="black", 
            fg="#55ff55", 
            insertbackground="#55ff55", 
            bd=2, 
            relief="sunken",
            font=("Courier", 10),
            wrap="word"
        )
        text.pack(fill="both", expand=True, padx=6, pady=6)
        
        # Welcome message
        welcome = """AuroraOS 98 - Terminal Emulator
Linux 5.10+ | systemd | Wayland
Type 'help' for available commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        text.insert("end", welcome)
        
        def execute_command(event=None):
            content = text.get("end-2c linestart", "end-1c")
            if content.strip():
                # Execute simple commands
                try:
                    if content.strip() == "help":
                        text.insert("end", """
Available commands:
  help     - Show this help message
  clear    - Clear terminal
  whoami   - Show current user
  date     - Show current date/time
  uname    - Show system info
  ls       - List files in current directory
  pwd      - Print working directory
""")
                    elif content.strip() == "clear":
                        text.delete("1.0", "end")
                    elif content.strip() == "date":
                        import datetime
                        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        text.insert("end", f"\n{date_str}\n")
                    elif content.strip() == "whoami":
                        import os
                        text.insert("end", f"\n{os.getenv('USER', 'aurora')}\n")
                    elif content.strip() == "uname":
                        result = subprocess.run(["uname", "-a"], capture_output=True, text=True)
                        text.insert("end", f"\n{result.stdout}\n")
                    elif content.strip().startswith("ls"):
                        try:
                            result = subprocess.run(content.strip().split(), capture_output=True, text=True, timeout=2)
                            text.insert("end", f"\n{result.stdout}\n")
                        except:
                            text.insert("end", "\nCommand error\n")
                    else:
                        text.insert("end", "\nCommand not found\n")
                except Exception as e:
                    text.insert("end", f"\nError: {str(e)}\n")
            
            text.insert("end", "$ ")
            text.see("end")
            return "break"
        
        text.insert("end", "$ ")
        text.bind("<Return>", execute_command)

    def open_network(self):
        win = self.window("network", "Network Neighborhood", 180, 150, 420, 300, "network")
        for child in win.winfo_children()[1:]:
            child.destroy()
        
        # Network info pane
        info_pane = tk.Frame(win, bg=FACE)
        info_pane.pack(fill="both", expand=True, padx=12, pady=12)
        
        # System name
        tk.Label(info_pane, text="Computer Name:", bg=FACE, font=self.ui_bold).pack(anchor="w", pady=(0, 4))
        hostname = get_hostname()
        tk.Label(info_pane, text=hostname, bg=FACE).pack(anchor="w", pady=(0, 12))
        
        # Network status
        tk.Label(info_pane, text="Network Status:", bg=FACE, font=self.ui_bold).pack(anchor="w", pady=(0, 4))
        status = get_network_status()
        status_color = "#00aa00" if status == "Connected" else "#aa0000"
        tk.Label(info_pane, text=status, bg=FACE, fg=status_color).pack(anchor="w", pady=(0, 12))
        
        # Buttons
        button_frame = tk.Frame(win, bg=FACE)
        button_frame.pack(fill="x", padx=12, pady=12)
        tk.Button(button_frame, text="Browse Internet", width=15, command=launch_browser).pack(side="left", padx=4)
        tk.Button(button_frame, text="Network Settings", width=15).pack(side="left", padx=4)
        tk.Button(button_frame, text="Wi-Fi Connection", width=15, command=launch_wifi_connection).pack(side="left", padx=4)

    def open_recycle(self):
        self.window("recycle", "Recycle Bin", 220, 170, 320, 220, "recycle")

    def open_settings(self):
        self.open_system_properties()

    def open_run(self):
        win = self.window("run", "Run", 250, 240, 360, 140, "run")
        for child in win.winfo_children()[1:]:
            child.destroy()
        tk.Label(win, text="Open:", bg=FACE).pack(side="left", padx=16, pady=30)
        tk.Entry(win, bd=2, relief="sunken").pack(side="left", fill="x", expand=True, padx=8)
        tk.Button(win, text="OK", width=8).pack(side="right", padx=12)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    AuroraShell().run()
