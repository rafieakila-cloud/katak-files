"""
KatakFILES - file manager ringan untuk Windows
Tema 32-bit klasik (Windows 95/98). Python + Tkinter + tkinterdnd2.
Ikon: Segoe MDL2 Assets + glyph jadul. Tanpa Electron.
"""

import os
import sys
import re
import glob
import shutil
import zipfile
import ctypes
import webbrowser
import subprocess
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except Exception:
    TkinterDnD = None
    HAS_DND = False

APP_NAME = "KatakFILES"
VERSION = "1.0.0 (Jadul)"

# ---------- palet Windows 95/98 ----------
FACE      = "#c0c0c0"   # button face
HILIGHT   = "#ffffff"   # bevel terang
SHADOW    = "#808080"   # bevel gelap
DARK      = "#000000"   # bevel paling gelap
NAVY      = "#000080"   # title bar / selection
NAVY2     = "#1084d0"   # gradient title (opsional)
WHITE     = "#ffffff"
BLACK     = "#000000"
TREE_BG   = "#ffffff"
TEAL      = "#008080"

MDL2 = "Segoe MDL2 Assets"
# Glyph jadul (panah klasik) + MDL2 untuk sisanya
G = {
    "back": "◄", "forward": "►", "up": "▲", "refresh": "\uE72C",
    "folder": "\uE8B7", "page": "\uE7C3", "document": "\uE8A5",
    "search": "\uE721", "newfolder": "\uE8F4", "newfile": "\uE8A5",
    "copy": "\uE8C8", "cut": "\uE8C6", "paste": "\uE77F",
    "rename": "\uE8AC", "delete": "\uE74D", "selectall": "\uE8B3",
    "play": "\uE768",
    "desktop": "\uE7F4", "downloads": "\uE896", "documents": "\uE8A5",
    "pictures": "\uE91B", "music": "\uE8D6", "videos": "\uE714",
    "pc": "\uE977", "usb": "\uE88E", "globe": "\uE774", "terminal": "\uE756",
}
FONT = ("Tahoma", 8)
FONT_TITLE = ("Tahoma", 9, "bold")
FONT_ICON = (MDL2, 11)

def icon_for(name: str, is_dir: bool) -> str:
    if is_dir:
        return G["folder"]
    ext = os.path.splitext(name)[1].lower()
    image = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico"}
    audio = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
    video = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
    archive = {".zip", ".rar", ".7z", ".tar", ".gz"}
    code = {".py", ".js", ".html", ".css", ".c", ".cpp", ".rs", ".go", ".java", ".json", ".sh"}
    if ext in image: return G["pictures"]
    if ext in audio: return G["music"]
    if ext in video: return G["videos"]
    if ext in archive: return "\uE896"
    if ext in code: return G["terminal"]
    if ext in {".exe", ".msi"}: return "\uE7B8"
    return G["page"]

def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024

def unique_path(dest: str) -> str:
    base, ext = os.path.splitext(dest)
    candidate = dest
    i = 1
    while os.path.exists(candidate):
        suffix = " - Copy" if i == 1 else f" - Copy ({i})"
        candidate = f"{base}{suffix}{ext}"
        i += 1
    return candidate

def unique_folder(dest: str) -> str:
    candidate = dest
    i = 1
    while os.path.exists(candidate):
        candidate = f"{dest} ({i})"
        i += 1
    return candidate

def get_drives():
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    out = []
    for i in range(26):
        if bitmask & (1 << i):
            letter = f"{chr(65 + i)}:\\"
            try:
                t = ctypes.windll.kernel32.GetDriveTypeW(letter)
            except Exception:
                t = 3
            out.append((letter, t))
    return out

def send_to_recycle_bin(paths):
    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD), ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR),
        ]
    op = SHFILEOPSTRUCTW()
    op.hwnd = 0
    op.wFunc = 0x0003  # FO_DELETE
    op.pFrom = "\0".join(paths) + "\0\0"
    op.pTo = None
    op.fFlags = 0x0001 | 0x0010 | 0x0400 | 0x0004  # ALLOWUNDO|NOCONFIRMATION|NOERRORUI|SILENT
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return result, bool(op.fAnyOperationsAborted)

def detect_wsl():
    try:
        out = subprocess.run(["wsl.exe", "-l", "-v"], capture_output=True,
                             timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return []
    text = out.stdout.decode("utf-16-le", errors="ignore")
    text = text.replace("\x00", "").replace("\ufeff", "")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    header = next((i for i, l in enumerate(lines) if l.upper().startswith("NAME")), None)
    if header is None:
        return []
    distros = []
    for line in lines[header + 1:]:
        parts = line.split()
        name = parts[0].lstrip("*").strip()
        if name and not name.upper().startswith("NAME"):
            distros.append(name)
    return distros

def detect_rufus():
    candidates = []
    path = shutil.which("rufus.exe") or shutil.which("rufus")
    if path:
        candidates.append(path)
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\rufus.exe") as key:
                    candidates.append(winreg.QueryValue(key, None))
            except OSError:
                pass
    except Exception:
        pass
    home = os.path.expanduser("~")
    for folder in (os.path.join(home, "Downloads"), os.path.join(home, "Desktop"),
                   os.path.join(home, "Documents")):
        if os.path.isdir(folder):
            candidates.extend(glob.glob(os.path.join(folder, "rufus*.exe")))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


class KatakApp:
    def __init__(self, root, start_dir=None):
        self.root = root
        self.root.overrideredirect(True)   # window tanpa frame: kita bikin sendiri ala 98
        self.root.geometry("1100x700+120+80")
        self.root.minsize(820, 520)
        self.root.configure(bg=FACE)

        if start_dir and os.path.isdir(start_dir):
            self.current_dir = os.path.normpath(start_dir)
        else:
            self.current_dir = os.path.expanduser("~")
        self.history = [self.current_dir]
        self.hist_index = 0
        self.all_entries = []
        self.sort_col = "name"
        self.sort_asc = True
        self.clipboard = []
        self.clipboard_mode = None
        self.drag_source = None
        self.drag_origin_y = None
        self.maximized = False
        self.normal_geometry = "1100x700+120+80"

        self._build_style()
        self._build_titlebar()
        self._build_menubar()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()
        self._bind_keys()
        self.navigate(self.current_dir, add_history=False)

    # ---------- gaya jadul ----------
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("winnative")   # bevel asli Windows
        except tk.TclError:
            style.theme_use("clam")
        style.configure("Treeview", background=TREE_BG, fieldbackground=TREE_BG,
                        foreground=BLACK, rowheight=22, borderwidth=1,
                        relief="sunken", font=FONT)
        style.configure("Treeview.Heading", background=FACE, foreground=BLACK,
                        font=("Tahoma", 8, "bold"), relief="raised", borderwidth=2)
        style.map("Treeview", background=[("selected", NAVY)],
                  foreground=[("selected", WHITE)])

    def _raised(self, parent, **kw):
        b = tk.Button(parent, relief="raised", bd=2, bg=FACE, fg=BLACK,
                      activebackground=FACE, activeforeground=BLACK,
                      font=FONT_ICON, **kw)
        return b

    def _sunken(self, parent, **kw):
        f = tk.Frame(parent, relief="sunken", bd=2, bg=WHITE, **kw)
        return f

    # ---------- title bar jadul ----------
    def _build_titlebar(self):
        self.titlebar = tk.Frame(self.root, bg=NAVY, height=28)
        self.titlebar.pack(side="top", fill="x")
        self.titlebar.pack_propagate(False)

        lbl = tk.Label(self.titlebar, text=f"  {APP_NAME} {VERSION}",
                       bg=NAVY, fg=WHITE, font=FONT_TITLE, anchor="w")
        lbl.pack(side="left", fill="both", expand=True)
        for w in (self.titlebar, lbl):
            w.bind("<ButtonPress-1>", self._title_press)
            w.bind("<B1-Motion>", self._title_move)
            w.bind("<Double-Button-1>", lambda e: self._toggle_max())

        for glyph, cmd in (("_", self.root.iconify), ("□", self._toggle_max), ("✕", self.root.destroy)):
            b = tk.Button(self.titlebar, text=glyph, command=cmd, width=3,
                          bg=FACE, fg=BLACK, relief="raised", bd=1,
                          font=("Tahoma", 9, "bold"), cursor="hand2",
                          padx=2, pady=0)
            b.pack(side="right", padx=2, pady=3)

    def _title_press(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()
        self.maximized = False

    def _title_move(self, event):
        if self.maximized:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _toggle_max(self):
        if self.maximized:
            self.root.geometry(self.normal_geometry)
        else:
            self.normal_geometry = self.root.geometry()
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            self.root.geometry(f"{sw}x{sh - 48}+0+0")
        self.maximized = not self.maximized

    # ---------- menu bar ----------
    def _build_menubar(self):
        menubar = tk.Menu(self.root, bg=FACE, fg=BLACK, tearoff=0,
                          activebackground=NAVY, activeforeground=WHITE)

        filem = tk.Menu(menubar, bg=FACE, fg=BLACK, tearoff=0,
                        activebackground=NAVY, activeforeground=WHITE)
        filem.add_command(label="Buka", command=self.open_selected)
        filem.add_command(label="New Folder", command=self.new_folder)
        filem.add_command(label="New File", command=self.new_file)
        filem.add_separator()
        filem.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=filem)

        editm = tk.Menu(menubar, bg=FACE, fg=BLACK, tearoff=0,
                        activebackground=NAVY, activeforeground=WHITE)
        editm.add_command(label="Salin\tCtrl+C", command=lambda: self.copy_selection(False))
        editm.add_command(label="Cut\tCtrl+X", command=lambda: self.copy_selection(True))
        editm.add_command(label="Tempel\tCtrl+V", command=self.paste)
        editm.add_command(label="Pilih Semua\tCtrl+A",
                          command=lambda: self.tree.selection_set(self.tree.get_children()))
        editm.add_separator()
        editm.add_command(label="Rename\tF2", command=self.rename_selection)
        editm.add_command(label="Hapus\tDel", command=self.delete_selection)
        menubar.add_cascade(label="Edit", menu=editm)

        viewm = tk.Menu(menubar, bg=FACE, fg=BLACK, tearoff=0,
                        activebackground=NAVY, activeforeground=WHITE)
        viewm.add_command(label="Nama", command=lambda: self.set_sort("name"))
        viewm.add_command(label="Ukuran", command=lambda: self.set_sort("size"))
        viewm.add_command(label="Diubah", command=lambda: self.set_sort("modified"))
        viewm.add_separator()
        viewm.add_command(label="Refresh\tF5", command=self.refresh)
        menubar.add_cascade(label="View", menu=viewm)

        toolm = tk.Menu(menubar, bg=FACE, fg=BLACK, tearoff=0,
                        activebackground=NAVY, activeforeground=WHITE)
        toolm.add_command(label="Extract Here", command=self.extract_here)
        toolm.add_command(label="Extract to…", command=self.extract_to)
        toolm.add_command(label="Compress to .zip", command=self.compress_to_zip)
        menubar.add_cascade(label="Tools", menu=toolm)

        helpm = tk.Menu(menubar, bg=FACE, fg=BLACK, tearoff=0,
                        activebackground=NAVY, activeforeground=WHITE)
        helpm.add_command(label="About KatakFILES…", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpm)

        self.root.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo(
            "About KatakFILES",
            f"KatakFILES {VERSION}\n\n"
            "File manager 32-bit klasik.\n"
            "Python + Tkinter, tanpa Electron.\n"
            "Ikon: Segoe MDL2 Assets.\n\n"
            "Dibuat dengan bantuan AI, dirakit oleh manusia.",
        )

    # ---------- toolbar ----------
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=FACE, padx=6, pady=4)
        bar.pack(side="top", fill="x")
        for glyph, cmd in ((G["back"], self.go_back), (G["forward"], self.go_forward),
                           (G["up"], self.go_up), (G["refresh"], self.refresh)):
            self._raised(bar, text=glyph, command=cmd, width=3).pack(side="left", padx=1)

        self.path_var = tk.StringVar()
        path_entry = tk.Entry(bar, textvariable=self.path_var, bg=WHITE, fg=BLACK,
                              insertbackground=BLACK, relief="sunken", bd=2,
                              font=("Tahoma", 9))
        path_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=2)
        path_entry.bind("<Return>", lambda e: self.navigate(self.path_var.get()))

        self.search_var = tk.StringVar()
        tk.Label(bar, text="Cari:", bg=FACE, fg=BLACK, font=FONT).pack(side="left")
        search = tk.Entry(bar, textvariable=self.search_var, width=16, bg=WHITE,
                          fg=BLACK, insertbackground=BLACK, relief="sunken", bd=2,
                          font=("Tahoma", 9))
        search.pack(side="left", padx=4, ipady=2)
        self.search_var.trace_add("write", lambda *_: self.render_entries())

    # ---------- body: sidebar + tree ----------
    def _build_body(self):
        body = tk.Frame(self.root, bg=FACE, padx=4, pady=4)
        body.pack(side="top", fill="both", expand=True)

        side = tk.Frame(body, bg=FACE, width=230)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        self.sidebar = tk.Listbox(side, bg=WHITE, fg=BLACK, bd=2, relief="sunken",
                                  highlightthickness=0, selectbackground=NAVY,
                                  selectforeground=WHITE, font=FONT, activestyle="none")
        self.sidebar.pack(fill="both", expand=True)
        self.sidebar.bind("<Button-1>", self._sidebar_click)
        self.sidebar_items = []
        self._populate_sidebar()

        container = tk.Frame(body, bg=FACE)
        container.pack(side="left", fill="both", expand=True, padx=(4, 0))

        cols = ("icon", "name", "size", "modified")
        self.tree = ttk.Treeview(container, columns=cols, show="headings",
                                 selectmode="extended")
        self.tree.heading("icon", text="")
        self.tree.heading("name", text="Nama", command=lambda: self.set_sort("name"))
        self.tree.heading("size", text="Ukuran", command=lambda: self.set_sort("size"))
        self.tree.heading("modified", text="Diubah", command=lambda: self.set_sort("modified"))
        self.tree.column("icon", width=28, anchor="center", stretch=False)
        self.tree.column("name", width=430, anchor="w")
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("modified", width=140, anchor="w")

        vs = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="left", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Return>", lambda e: self.open_selected())
        self.tree.bind("<ButtonPress-1>", self._drag_start)
        self.tree.bind("<ButtonRelease-1>", self._drag_end)

        if HAS_DND:
            try:
                self.tree.drop_target_register(DND_FILES)
                self.tree.dnd_bind("<<Drop>>", self._external_drop)
            except Exception:
                pass

    def _populate_sidebar(self):
        home = os.path.expanduser("~")
        def add(text, target):
            self.sidebar.insert("end", text)
            self.sidebar_items.append(target)

        add("Akses cepat", None)
        quick = [
            ("  Desktop", os.path.join(home, "Desktop")),
            ("  Downloads", os.path.join(home, "Downloads")),
            ("  Documents", os.path.join(home, "Documents")),
            ("  Pictures", os.path.join(home, "Pictures")),
            ("  Music", os.path.join(home, "Music")),
            ("  Videos", os.path.join(home, "Videos")),
        ]
        for label, path in quick:
            if os.path.isdir(path):
                add(label, path)

        add("Drive", None)
        for letter, dtype in get_drives():
            try:
                usage = shutil.disk_usage(letter)
                free_txt = f"{human_size(usage.free)} bebas"
            except OSError:
                free_txt = "?"
            icon = {"2": "USB", "4": "NET"}.get(str(dtype), "HDD")
            add(f"  {letter}  ({free_txt})", letter)

        add("Linux (WSL)", None)
        distros = detect_wsl()
        if distros:
            for distro in distros:
                add(f"  {distro}", ("wsl", distro))
        else:
            add("  (belum ada WSL)", None)

        add("Tools", None)
        rufus = detect_rufus()
        add("  Rufus" + ("" if rufus else "  (belum ada)"), ("rufus", rufus))

    def _sidebar_click(self, event):
        idx = self.sidebar.nearest(event.y)
        try:
            target = self.sidebar_items[idx]
        except IndexError:
            return
        if target is None:
            return
        if isinstance(target, tuple):
            kind, value = target
            if kind == "wsl":
                self.launch_wsl(value)
            elif kind == "rufus":
                if value:
                    os.startfile(value)
                else:
                    webbrowser.open("https://rufus.ie/")
            return
        self.navigate(target)

    def launch_wsl(self, distro):
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "cmd.exe", "/k", "wsl.exe", "-d", distro])
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Gagal membuka WSL {distro}:\n{e}")

    # ---------- status bar ----------
    def _build_statusbar(self):
        self.status_var = tk.StringVar(value=f"{APP_NAME} siap")
        bar = tk.Frame(self.root, bg=FACE, padx=3, pady=3)
        bar.pack(side="bottom", fill="x")
        self.status_panel = tk.Frame(bar, relief="sunken", bd=2, bg=FACE)
        self.status_panel.pack(side="left", fill="x", expand=True)
        tk.Label(self.status_panel, textvariable=self.status_var, bg=FACE,
                 fg=BLACK, anchor="w", font=FONT, padx=6).pack(fill="x")
        self.status_panel2 = tk.Frame(bar, relief="sunken", bd=2, bg=FACE)
        self.status_panel2.pack(side="left", padx=(3, 0))
        self.count_var = tk.StringVar(value="0 item")
        tk.Label(self.status_panel2, textvariable=self.count_var, bg=FACE,
                 fg=BLACK, anchor="w", font=FONT, padx=10).pack()

    def _update_status(self):
        try:
            usage = shutil.disk_usage(self.current_dir)
            free_text = f"{human_size(usage.free)} bebas dari {human_size(usage.total)}"
        except Exception:
            free_text = "?"
        self.status_var.set(free_text)
        self.count_var.set(f"{len(self.all_entries)} item")

    # ---------- navigation ----------
    def navigate(self, path, add_history=True):
        path = os.path.expandvars(path.strip().strip('"'))
        if not path:
            return
        if not os.path.isdir(path):
            messagebox.showerror(APP_NAME, f"Folder tidak ditemukan:\n{path}")
            return
        path = os.path.normpath(path)
        self.current_dir = path
        if add_history:
            self.history = self.history[:self.hist_index + 1]
            self.history.append(path)
            self.hist_index = len(self.history) - 1
        self.path_var.set(path)
        self.refresh()

    def go_back(self):
        if self.hist_index > 0:
            self.hist_index -= 1
            self.navigate(self.history[self.hist_index], add_history=False)

    def go_forward(self):
        if self.hist_index < len(self.history) - 1:
            self.hist_index += 1
            self.navigate(self.history[self.hist_index], add_history=False)

    def go_up(self):
        parent = os.path.dirname(self.current_dir.rstrip("\\"))
        if parent and parent != self.current_dir:
            self.navigate(parent)

    def refresh(self):
        self.all_entries = []
        try:
            with os.scandir(self.current_dir) as it:
                for entry in it:
                    try:
                        stat = entry.stat()
                        size = stat.st_size if entry.is_file() else None
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        self.all_entries.append({
                            "path": entry.path, "name": entry.name,
                            "is_dir": entry.is_dir(), "size": size, "mtime": mtime,
                        })
                    except OSError:
                        continue
        except (PermissionError, OSError) as e:
            messagebox.showerror(APP_NAME, f"Tidak bisa membaca folder:\n{e}")
        self.render_entries()

    def set_sort(self, col):
        if self.sort_col == col:
            self.sort_asc = not self.sort_asc
        else:
            self.sort_col, self.sort_asc = col, True
        self.render_entries()

    def render_entries(self):
        query = self.search_var.get().strip().lower()
        entries = [e for e in self.all_entries if query in e["name"].lower()]
        reverse = not self.sort_asc
        if self.sort_col == "name":
            key = lambda e: e["name"].lower()
        elif self.sort_col == "size":
            key = lambda e: (e["size"] if e["size"] is not None else -1)
        else:
            key = lambda e: e["mtime"]
        entries.sort(key=key, reverse=reverse)
        entries.sort(key=lambda e: not e["is_dir"])  # folder di atas

        self.tree.delete(*self.tree.get_children())
        for e in entries:
            size = "" if e["is_dir"] else human_size(e["size"])
            modified = e["mtime"].strftime("%Y-%m-%d %H:%M")
            self.tree.insert("", "end", iid=e["path"],
                             values=(icon_for(e["name"], e["is_dir"]), e["name"], size, modified))
        self._update_status()

    def selected_paths(self):
        return list(self.tree.selection())

    def total_selected_size(self):
        total = 0
        for e in self.all_entries:
            if e["path"] in self.selected_paths() and e["size"]:
                total += e["size"]
        return total

    # ---------- actions ----------
    def open_selected(self):
        paths = self.selected_paths()
        if not paths:
            return
        path = paths[0]
        if os.path.isdir(path):
            self.navigate(path)
            return
        try:
            os.startfile(path)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Gagal membuka:\n{e}")

    def copy_selection(self, cut=False):
        paths = self.selected_paths()
        if paths:
            self.clipboard = paths
            self.clipboard_mode = "cut" if cut else "copy"
            self.status_var.set(f"{len(paths)} item {'dipindah' if cut else 'disalin'}")

    def paste(self):
        if not self.clipboard:
            return
        self._transfer_items(self.clipboard, self.current_dir, self.clipboard_mode)
        if self.clipboard_mode == "cut":
            self.clipboard = []
            self.clipboard_mode = None
        self.refresh()

    def _transfer_items(self, sources, dest_dir, mode):
        for src in sources:
            dest = os.path.join(dest_dir, os.path.basename(src))
            same_dir = os.path.abspath(os.path.dirname(src)) == os.path.abspath(dest_dir)
            if os.path.isdir(src):
                dest = unique_folder(dest) if (os.path.exists(dest) or same_dir) else dest
                try:
                    if mode == "cut":
                        shutil.move(src, dest)
                    else:
                        shutil.copytree(src, dest)
                except (shutil.Error, OSError) as e:
                    messagebox.showerror(APP_NAME, f"Gagal:\n{e}")
            else:
                dest = unique_path(dest) if (os.path.exists(dest) or same_dir) else dest
                try:
                    if mode == "cut":
                        shutil.move(src, dest)
                    else:
                        shutil.copy2(src, dest)
                except (shutil.Error, OSError) as e:
                    messagebox.showerror(APP_NAME, f"Gagal:\n{e}")

    def delete_selection(self):
        paths = self.selected_paths()
        if not paths:
            return
        total_bytes = self.total_selected_size()
        msg = f"Hapus {len(paths)} item ke Recycle Bin?"
        if total_bytes:
            msg += f"\n\nTotal: {human_size(total_bytes)}"
        if messagebox.askyesno(APP_NAME, msg):
            if total_bytes >= 500 * 1024 * 1024:
                self._delete_with_animation(paths)
            else:
                send_to_recycle_bin(paths)
                self.refresh()

    # ---------- animasi kodok (file besar) ----------
    def _delete_with_animation(self, paths):
        win = tk.Toplevel(self.root)
        win.title("Membersihkan…")
        win.configure(bg=FACE)
        win.geometry("380x230")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        canvas = tk.Canvas(win, width=380, height=165, bg=WHITE,
                           highlightthickness=2, highlightbackground=SHADOW)
        canvas.pack(pady=(10, 0), padx=10)
        tk.Label(win, text="Kodok sedang membersihkan tempat sampah…",
                 bg=FACE, fg=BLACK, font=FONT).pack(pady=8)

        canvas.create_rectangle(255, 70, 330, 125, fill="#a0a0a0", outline=BLACK, width=2)
        canvas.create_rectangle(245, 56, 340, 70, fill="#c0c0c0", outline=BLACK, width=2)
        canvas.create_rectangle(272, 84, 282, 118, fill="#606060", outline="")
        canvas.create_rectangle(300, 84, 310, 118, fill="#606060", outline="")

        frog = canvas.create_oval(30, 80, 110, 122, fill="#3fa050", outline=BLACK, width=2)
        belly = canvas.create_oval(48, 94, 92, 118, fill="#8fe0a8", outline="")
        eye_l = canvas.create_oval(42, 55, 62, 76, fill="#3fa050", outline=BLACK, width=2)
        eye_r = canvas.create_oval(78, 55, 98, 76, fill="#3fa050", outline=BLACK, width=2)
        pupil_l = canvas.create_oval(50, 62, 56, 68, fill=BLACK, outline="")
        pupil_r = canvas.create_oval(86, 62, 92, 68, fill=BLACK, outline="")
        mouth = canvas.create_arc(52, 86, 88, 106, start=200, extent=140, style="arc",
                                  outline=BLACK, width=2)
        parts = [frog, belly, eye_l, eye_r, pupil_l, pupil_r, mouth]

        total_frames = 160
        state = {"frame": 0, "done": False, "last_x": 30, "last_y": 0}

        def hop():
            f = state["frame"]
            t = f / total_frames
            x = 30 + (225 - 30) * t
            y = 0 if (f % 18) < 9 else -22
            dx = x - state["last_x"]; dy = y - state["last_y"]
            for part in parts:
                canvas.move(part, dx, dy)
            state["last_x"], state["last_y"] = x, y
            state["frame"] = f + 1
            if state["done"]:
                return
            if state["frame"] <= total_frames:
                win.after(16, hop)

        def worker():
            send_to_recycle_bin(paths)
            state["done"] = True

        import threading
        threading.Thread(target=worker, daemon=True).start()
        win.after(16, hop)

        def check_done():
            if state["done"]:
                win.grab_release()
                win.destroy()
                self.refresh()
            else:
                win.after(100, check_done)
        win.after(100, check_done)

    def rename_selection(self):
        paths = self.selected_paths()
        if len(paths) != 1:
            return
        old_path = paths[0]
        old_name = os.path.basename(old_path)
        new_name = simpledialog.askstring(APP_NAME, "Nama baru:", initialvalue=old_name,
                                          parent=self.root)
        if new_name and new_name != old_name:
            new_path = os.path.join(self.current_dir, new_name)
            if os.path.exists(new_path):
                messagebox.showerror(APP_NAME, "Nama sudah dipakai.")
                return
            try:
                os.rename(old_path, new_path)
                self.refresh()
            except OSError as e:
                messagebox.showerror(APP_NAME, f"Gagal rename:\n{e}")

    def new_folder(self):
        name = simpledialog.askstring(APP_NAME, "Nama folder baru:",
                                      initialvalue="New folder", parent=self.root)
        if name:
            path = unique_folder(os.path.join(self.current_dir, name))
            try:
                os.mkdir(path)
                self.refresh()
            except OSError as e:
                messagebox.showerror(APP_NAME, f"Gagal membuat folder:\n{e}")

    def new_file(self):
        name = simpledialog.askstring(APP_NAME, "Nama file baru:",
                                      initialvalue="New file.txt", parent=self.root)
        if name:
            path = unique_path(os.path.join(self.current_dir, name))
            try:
                open(path, "w", encoding="utf-8").close()
                self.refresh()
            except OSError as e:
                messagebox.showerror(APP_NAME, f"Gagal membuat file:\n{e}")

    # ---------- zip ----------
    def _zip_safe_extract(self, zip_path, dest):
        dest_real = os.path.realpath(dest)
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                target = os.path.realpath(os.path.join(dest_real, member))
                if not target.startswith(dest_real + os.sep) and target != dest_real:
                    raise ValueError(f"Zip slip terdeteksi: {member}")
            zf.extractall(dest_real)

    def extract_here(self):
        for path in self.selected_paths():
            if not zipfile.is_zipfile(path):
                continue
            dest = unique_folder(os.path.join(self.current_dir,
                                              os.path.splitext(os.path.basename(path))[0]))
            try:
                self._zip_safe_extract(path, dest)
            except (zipfile.BadZipFile, ValueError, OSError) as e:
                messagebox.showerror(APP_NAME, f"Gagal ekstrak:\n{e}")
        self.refresh()

    def extract_to(self):
        paths = [p for p in self.selected_paths() if zipfile.is_zipfile(p)]
        if not paths:
            return
        dest = filedialog.askdirectory(parent=self.root, title="Ekstrak ke folder…")
        if not dest:
            return
        for path in paths:
            try:
                self._zip_safe_extract(path, os.path.join(dest,
                                       os.path.splitext(os.path.basename(path))[0]))
            except (zipfile.BadZipFile, ValueError, OSError) as e:
                messagebox.showerror(APP_NAME, f"Gagal ekstrak:\n{e}")
        self.refresh()

    def compress_to_zip(self):
        paths = self.selected_paths()
        if not paths:
            return
        base = os.path.splitext(os.path.basename(paths[0]))[0] if len(paths) == 1 else "arsip"
        dest = unique_path(os.path.join(self.current_dir, base + ".zip"))
        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in paths:
                    if os.path.isdir(path):
                        for root_dir, _, files in os.walk(path):
                            for name in files:
                                full = os.path.join(root_dir, name)
                                arc = os.path.join(os.path.basename(path), os.path.relpath(full, path))
                                zf.write(full, arc)
                    else:
                        zf.write(path, os.path.basename(path))
            self.refresh()
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Gagal membuat ZIP:\n{e}")

    # ---------- drag & drop ----------
    def _parse_dropped_paths(self, data):
        parts = re.findall(r"\{[^}]+\}|\S+", data)
        out = []
        for p in parts:
            p = p.strip()
            if p.startswith("{") and p.endswith("}"):
                p = p[1:-1]
            if p:
                out.append(p)
        return out

    def _external_drop(self, event):
        sources = [p for p in self._parse_dropped_paths(event.data) if os.path.exists(p)]
        if not sources:
            return
        which = messagebox.askyesnocancel(
            APP_NAME,
            f"Tempel {len(sources)} item dari luar?\n\n"
            "Yes = Salin\nNo = Pindahkan\nCancel = Batal")
        if which is None:
            return
        self._transfer_items(sources, self.current_dir, "copy" if which else "cut")
        self.refresh()

    def _drag_start(self, event):
        self.drag_source = self.tree.identify_row(event.y)
        self.drag_origin_y = event.y

    def _drag_end(self, event):
        src = self.drag_source
        self.drag_source = None
        if not src:
            return
        target = self.tree.identify_row(event.y)
        if not target or target == src or abs(event.y - (self.drag_origin_y or 0)) < 4:
            return
        if os.path.isdir(target):
            move = messagebox.askyesno(APP_NAME,
                f"Pindahkan ke:\n{target}\n\nYes = Pindahkan\nNo = Salin")
            self._transfer_items([src], target, "cut" if move else "copy")
            self.refresh()

    # ---------- context menu & keys ----------
    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id and row_id not in self.tree.selection():
            self.tree.selection_set(row_id)
        menu = tk.Menu(self.root, tearoff=0, bg=FACE, fg=BLACK,
                       activebackground=NAVY, activeforeground=WHITE)
        sel = self.selected_paths()
        has_zip = any(zipfile.is_zipfile(p) for p in sel)
        menu.add_command(label="Buka", command=self.open_selected)
        menu.add_separator()
        menu.add_command(label="Salin  (Ctrl+C)", command=lambda: self.copy_selection(False))
        menu.add_command(label="Cut  (Ctrl+X)", command=lambda: self.copy_selection(True))
        menu.add_command(label="Tempel  (Ctrl+V)", command=self.paste)
        menu.add_separator()
        menu.add_command(label="Rename  (F2)", command=self.rename_selection)
        menu.add_command(label="Hapus  (Del)", command=self.delete_selection)
        menu.add_separator()
        if has_zip:
            menu.add_command(label="Extract Here", command=self.extract_here)
            menu.add_command(label="Extract to…", command=self.extract_to)
            menu.add_separator()
        menu.add_command(label="Compress to .zip", command=self.compress_to_zip)
        menu.add_separator()
        menu.add_command(label="New Folder  (Ctrl+Shift+N)", command=self.new_folder)
        menu.add_command(label="New File", command=self.new_file)
        menu.add_separator()
        menu.add_command(label="Refresh  (F5)", command=self.refresh)
        menu.tk_popup(event.x_root, event.y_root)

    def _bind_keys(self):
        for seq, cmd in {
            "<Control-c>": lambda: self.copy_selection(False),
            "<Control-x>": lambda: self.copy_selection(True),
            "<Control-v>": self.paste,
            "<Control-a>": lambda: self.tree.selection_set(self.tree.get_children()),
            "<F2>": self.rename_selection,
            "<F5>": self.refresh,
            "<Delete>": self.delete_selection,
            "<BackSpace>": self.go_up,
            "<Control-Shift-N>": self.new_folder,
        }.items():
            self.root.bind_all(seq, lambda e: cmd())


def main():
    import sys
    start_dir = None
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        start_dir = sys.argv[1]
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    KatakApp(root, start_dir=start_dir)
    root.mainloop()

if __name__ == "__main__":
    main()
