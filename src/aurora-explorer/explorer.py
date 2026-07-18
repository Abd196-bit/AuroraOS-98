#!/usr/bin/python3
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


HOME = Path("/tmp/firefox-home")
ICON_DIR = Path("/usr/share/aurora/icons")
ARCHIVE_SUFFIXES = (".zip", ".7z", ".rar", ".tar", ".tgz", ".gz", ".xz", ".bz2", ".dmg")


class Explorer:
    def __init__(self, start: Path) -> None:
        self.root = tk.Tk()
        self.root.title("AuroraOS File Explorer")
        try:
            self.window_icon = tk.PhotoImage(file=str(ICON_DIR / "explorer-48.png"))
            self.root.iconphoto(True, self.window_icon)
        except tk.TclError:
            self.window_icon = None
        self.root.geometry("1180x720+80+60")
        self.root.minsize(820, 500)
        self.root.configure(bg="#202020")
        self.root.option_add("*Font", ("MS W98 UI", 15))
        self.history: list[Path] = []
        self.history_index = -1
        self.current = start
        self.paths: dict[str, Path] = {}
        self.images: dict[str, tk.PhotoImage] = {}
        self._load_images()
        self._configure_style()
        self._build()
        self.navigate(start)

    def _load_images(self) -> None:
        for name in ("folder", "download", "archive", "installer", "executable", "generic-file", "desktop"):
            path = ICON_DIR / f"{name}-48.png"
            if path.exists():
                try:
                    self.images[name] = tk.PhotoImage(file=str(path))
                except tk.TclError:
                    pass

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Treeview", background="#171717", fieldbackground="#171717",
                        foreground="#f3f3f3", rowheight=58, borderwidth=1)
        style.map("Treeview", background=[("selected", "#0078d7")],
                  foreground=[("selected", "white")])
        style.configure("Treeview.Heading", background="#303030", foreground="white",
                        relief="raised", padding=(8, 8))
        style.configure("Vertical.TScrollbar", background="#c0c0c0", troughcolor="#303030")

    def _button(self, parent: tk.Widget, text: str, command, width: int = 10) -> tk.Button:
        return tk.Button(parent, text=text, command=lambda: self._clicked(command), width=width,
                         bg="#c0c0c0", fg="#111111", activebackground="#e0e0e0",
                         bd=2, relief="raised", highlightthickness=0)

    def _clicked(self, command) -> None:
        subprocess.Popen(["/usr/bin/aplay", "-q", "/usr/share/aurora/sounds/click.wav"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        command()

    def _build(self) -> None:
        title = tk.Frame(self.root, bg="#0078d7", height=46)
        title.pack(fill="x")
        tk.Label(title, text="AuroraOS File Explorer", bg="#0078d7", fg="white",
                 font=("MS W98 UI", 18, "bold")).pack(side="left", padx=12, pady=8)

        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Open", command=self.open_selected)
        file_menu.add_command(label="Open Terminal Here", command=self.open_terminal)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.root.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_command(label="Refresh", command=self.refresh)
        view_menu.add_command(label="Home", command=lambda: self.navigate(HOME))
        menu.add_cascade(label="View", menu=view_menu)
        self.root.configure(menu=menu)

        toolbar = tk.Frame(self.root, bg="#2b2b2b", bd=1, relief="raised")
        toolbar.pack(fill="x")
        for text, command, width in (
            ("Back", self.back, 8), ("Forward", self.forward, 9), ("Up", self.up, 7),
            ("Home", lambda: self.navigate(HOME), 8),
            ("Downloads", lambda: self.navigate(HOME / "Downloads"), 12),
            ("Refresh", self.refresh, 9),
        ):
            self._button(toolbar, text, command, width).pack(side="left", padx=4, pady=6)

        address_row = tk.Frame(self.root, bg="#202020")
        address_row.pack(fill="x", padx=8, pady=7)
        tk.Label(address_row, text="Address", bg="#202020", fg="#f3f3f3").pack(side="left", padx=(0, 8))
        self.address = tk.Entry(address_row, bg="#111111", fg="white", insertbackground="white",
                                bd=2, relief="sunken")
        self.address.pack(side="left", fill="x", expand=True)
        self.address.bind("<Return>", lambda _event: self.open_address())
        self._button(address_row, "Go", self.open_address, 6).pack(side="left", padx=(8, 0))

        content = tk.PanedWindow(self.root, orient="horizontal", bg="#808080", sashwidth=5,
                                 bd=2, relief="sunken")
        content.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        places = tk.Frame(content, bg="#252525", width=220)
        content.add(places, minsize=200)
        tk.Label(places, text="Places", anchor="w", bg="#303030", fg="white",
                 font=("MS W98 UI", 16, "bold"), padx=10, pady=8).pack(fill="x")
        for label, path in (
            ("Home", HOME), ("Desktop", HOME / "Desktop"),
            ("Documents", HOME / "Documents"), ("Downloads", HOME / "Downloads"),
            ("Applications", HOME / "Applications"), ("Temporary Files", Path("/tmp")),
        ):
            tk.Button(places, text=label, anchor="w", command=lambda p=path: self._clicked(lambda: self.navigate(p)),
                      bg="#252525", fg="#f3f3f3", activebackground="#0078d7",
                      activeforeground="white", bd=0, padx=16, pady=9).pack(fill="x")

        table_frame = tk.Frame(content, bg="#171717")
        content.add(table_frame, minsize=560)
        self.tree = ttk.Treeview(table_frame, columns=("type", "size", "modified"),
                                 show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Name", command=lambda: self._sort("name"))
        self.tree.heading("type", text="Type", command=lambda: self._sort("type"))
        self.tree.heading("size", text="Size", command=lambda: self._sort("size"))
        self.tree.heading("modified", text="Modified", command=lambda: self._sort("modified"))
        self.tree.column("#0", width=470, minwidth=240)
        self.tree.column("type", width=160, minwidth=100)
        self.tree.column("size", width=120, minwidth=90, anchor="e")
        self.tree.column("modified", width=180, minwidth=140)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _event: self.open_selected())
        self.tree.bind("<Return>", lambda _event: self.open_selected())
        self.root.bind("<BackSpace>", lambda _event: self.back())
        self.root.bind("<F5>", lambda _event: self.refresh())

        self.status = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status, anchor="w", bg="#303030", fg="white",
                 bd=1, relief="sunken", padx=8, pady=5).pack(fill="x", padx=8, pady=(0, 8))

    @staticmethod
    def _size(size: int) -> str:
        if size >= 1024 ** 3:
            return f"{size / 1024 ** 3:.1f} GB"
        if size >= 1024 ** 2:
            return f"{size / 1024 ** 2:.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"

    @staticmethod
    def _kind(path: Path) -> tuple[str, str]:
        if path.is_dir():
            return "folder", "File folder"
        lower = path.name.lower()
        if lower.endswith(ARCHIVE_SUFFIXES):
            return "archive", "Compressed archive"
        if lower.endswith(".deb"):
            return "installer", "Debian package"
        if lower.endswith(".apk"):
            return "installer", "APK package"
        if lower.endswith(".dmg"):
            return "archive", "Apple disk image"
        if lower.endswith((".exe", ".msi", ".appimage", ".sh")) or os.access(path, os.X_OK):
            return "executable", "Application"
        if lower.endswith(".desktop"):
            return "desktop", "Desktop launcher"
        return "generic-file", path.suffix[1:].upper() + " file" if path.suffix else "File"

    def navigate(self, path: Path, record: bool = True) -> None:
        try:
            target = path.expanduser().resolve()
            if not target.is_dir():
                raise NotADirectoryError(target)
            entries = sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError as error:
            messagebox.showerror("Aurora Explorer", f"Could not open folder:\n{error}", parent=self.root)
            return
        self.current = target
        if record:
            del self.history[self.history_index + 1 :]
            self.history.append(target)
            self.history_index = len(self.history) - 1
        self.address.delete(0, "end")
        self.address.insert(0, str(target))
        self.paths.clear()
        self.tree.delete(*self.tree.get_children())
        for path in entries:
            if path.name.startswith("."):
                continue
            icon, kind = self._kind(path)
            try:
                stat = path.stat()
                size = "" if path.is_dir() else self._size(stat.st_size)
                modified = dt.datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y %H:%M")
            except OSError:
                size, modified = "", ""
            item = self.tree.insert("", "end", text=path.name, image=self.images.get(icon, ""),
                                    values=(kind, size, modified))
            self.paths[item] = path
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])
        self.tree.focus_set()
        self.status.set(f"{len(self.paths)} items  |  {target}")
        self.root.title(f"{target.name or '/'} - AuroraOS File Explorer")

    def selected_path(self) -> Path | None:
        selection = self.tree.selection()
        return self.paths.get(selection[0]) if selection else None

    def open_selected(self) -> None:
        path = self.selected_path()
        if path is None:
            return
        self._clicked(lambda: self._open(path))

    def _open(self, path: Path) -> None:
        if path.is_dir():
            self.navigate(path)
            return
        try:
            subprocess.Popen(["/usr/bin/aurora-open-downloaded-file", str(path)], env=os.environ.copy())
            self.status.set(f"Opened {path.name}")
        except OSError as error:
            messagebox.showerror("Aurora Explorer", str(error), parent=self.root)

    def open_address(self) -> None:
        self.navigate(Path(self.address.get()))

    def refresh(self) -> None:
        self.navigate(self.current, record=False)

    def up(self) -> None:
        self.navigate(self.current.parent)

    def back(self) -> None:
        if self.history_index > 0:
            self.history_index -= 1
            self.navigate(self.history[self.history_index], record=False)

    def forward(self) -> None:
        if self.history_index + 1 < len(self.history):
            self.history_index += 1
            self.navigate(self.history[self.history_index], record=False)

    def open_terminal(self) -> None:
        subprocess.Popen(["/usr/bin/aurora-terminal", str(self.current)], env=os.environ.copy())

    def _sort(self, column: str) -> None:
        children = list(self.tree.get_children())
        index = {"type": 0, "size": 1, "modified": 2}.get(column)
        children.sort(key=lambda item: (self.tree.item(item, "text") if index is None
                                        else self.tree.item(item, "values")[index]).lower())
        for position, item in enumerate(children):
            self.tree.move(item, "", position)

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    start = Path(sys.argv[1]) if len(sys.argv) > 1 else HOME / "Downloads"
    if start.is_file():
        start = start.parent
    Explorer(start).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
