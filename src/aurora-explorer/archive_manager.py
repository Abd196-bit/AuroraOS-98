#!/usr/bin/python3
from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class ArchiveManager:
    def __init__(self, archive: Path) -> None:
        self.archive = archive.resolve()
        self.destination: Path | None = None
        self.root = tk.Tk()
        self.root.title(f"Aurora Archive Manager - {self.archive.name}")
        self.root.geometry("1040x680+150+90")
        self.root.configure(bg="#202020")
        self.root.option_add("*Font", ("MS W98 UI", 15))
        self._build()
        self._load()

    def _build(self) -> None:
        title = tk.Frame(self.root, bg="#0078d7", height=46)
        title.pack(fill="x")
        tk.Label(title, text="Aurora Archive Manager", bg="#0078d7", fg="white",
                 font=("MS W98 UI", 18, "bold")).pack(side="left", padx=12, pady=8)
        toolbar = tk.Frame(self.root, bg="#2b2b2b", bd=1, relief="raised")
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        tk.Button(toolbar, text="Extract All", command=self.extract_all, width=16,
                  bd=2, relief="raised").pack(side="left", padx=6, pady=6)
        tk.Button(toolbar, text="Open Extracted Folder", command=self.open_destination,
                  width=24, bd=2, relief="raised").pack(side="left", padx=6, pady=6)
        tk.Button(toolbar, text="Close", command=self.root.destroy, width=10,
                  bd=2, relief="raised").pack(side="right", padx=6, pady=6)
        path = tk.Entry(self.root, bg="#111111", fg="#f3f3f3", relief="sunken", bd=2)
        path.insert(0, str(self.archive))
        path.configure(state="readonly", readonlybackground="#111111")
        path.pack(fill="x", padx=10, pady=6)
        frame = tk.Frame(self.root, bg="#202020")
        frame.pack(fill="both", expand=True, padx=10, pady=4)
        self.tree = ttk.Treeview(frame, columns=("size", "type"), show="tree headings")
        for column, text, width in (("#0", "Name", 650), ("size", "Size", 140), ("type", "Type", 140)):
            self.tree.heading(column, text=text)
            self.tree.column(column, width=width)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.status = tk.StringVar(value="Reading archive...")
        tk.Label(self.root, textvariable=self.status, bg="#2b2b2b", fg="#f3f3f3",
                 anchor="w", bd=1, relief="sunken").pack(fill="x", padx=8, pady=(4, 8))

    @staticmethod
    def _size(value: int) -> str:
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.1f} MB"
        if value >= 1024:
            return f"{value / 1024:.1f} KB"
        return f"{value} B"

    def _entries(self) -> list[tuple[str, int, str]]:
        if self.archive.name.lower().endswith(".zip"):
            with zipfile.ZipFile(self.archive) as archive:
                return [(item.filename, item.file_size, "Folder" if item.is_dir() else "File")
                        for item in archive.infolist()]
        if tarfile.is_tarfile(self.archive):
            with tarfile.open(self.archive) as archive:
                return [(item.name, item.size, "Folder" if item.isdir() else "File")
                        for item in archive.getmembers()]
        result = subprocess.run(["7z", "l", "-ba", str(self.archive)], check=True,
                                text=True, capture_output=True)
        entries = []
        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=5)
            if len(parts) == 6 and parts[3].isdigit():
                entries.append((parts[5], int(parts[3]), "File"))
        return entries

    def _load(self) -> None:
        try:
            entries = self._entries()
            for name, size, kind in entries:
                self.tree.insert("", "end", text=name, values=(self._size(size), kind))
            self.status.set(f"{len(entries)} items")
        except Exception as error:
            self.status.set("Could not read archive")
            messagebox.showerror("Archive Error", str(error), parent=self.root)

    @staticmethod
    def _inside(destination: Path, member: str) -> bool:
        destination = destination.resolve()
        target = (destination / member).resolve()
        return target == destination or destination in target.parents

    def extract_all(self) -> None:
        default = self.archive.parent / self.archive.name.removesuffix(".zip")
        selected = filedialog.askdirectory(parent=self.root, title="Extract archive to",
                                           initialdir=str(self.archive.parent), mustexist=True)
        destination = Path(selected).resolve() if selected else default.resolve()
        if not selected:
            destination.mkdir(parents=True, exist_ok=True)
        try:
            self.status.set("Extracting...")
            self.root.update_idletasks()
            if self.archive.name.lower().endswith(".zip"):
                with zipfile.ZipFile(self.archive) as archive:
                    if not all(self._inside(destination, item.filename) for item in archive.infolist()):
                        raise RuntimeError("The archive contains an unsafe path.")
                    archive.extractall(destination)
            elif tarfile.is_tarfile(self.archive):
                with tarfile.open(self.archive) as archive:
                    if not all(self._inside(destination, item.name) for item in archive.getmembers()):
                        raise RuntimeError("The archive contains an unsafe path.")
                    archive.extractall(destination, filter="data")
            else:
                subprocess.run(["7z", "x", "-y", f"-o{destination}", str(self.archive)], check=True)
            for path in destination.rglob("*"):
                if path.is_file() and path.suffix in {"", ".sh", ".AppImage"}:
                    path.chmod(path.stat().st_mode | 0o111)
            self.destination = destination
            self.status.set(f"Extracted to {destination}")
            messagebox.showinfo("Extraction Complete", f"Files extracted to:\n{destination}", parent=self.root)
        except Exception as error:
            self.status.set("Extraction failed")
            messagebox.showerror("Extraction Failed", str(error), parent=self.root)

    def open_destination(self) -> None:
        if self.destination is None or not self.destination.exists():
            messagebox.showinfo("Archive Manager", "Extract the archive first.", parent=self.root)
            return
        subprocess.Popen(["/usr/bin/aurora-explorer", str(self.destination)], env=os.environ.copy())

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        print("usage: aurora-archive-manager ARCHIVE", file=sys.stderr)
        return 2
    ArchiveManager(Path(sys.argv[1])).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
