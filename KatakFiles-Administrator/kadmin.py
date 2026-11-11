#!/usr/bin/env python3
"""
Katak-Files Administrator — terminal file manager by bawapi-katak
Mirip ranger: 3 panel + preview, murni stdlib (msvcrt + ANSI).
"""

import os
import sys
import shutil
import zipfile
import ctypes
from ctypes import wintypes
from datetime import datetime

APP = "Katak-Files Administrator"
DEV = "bawapi-katak"
VERSION = "1.0.0"

# ---------- warna (ANSI, hijau katak) ----------
ESC = "\033"
C_RESET   = ESC + "[0m"
C_ACC     = ESC + "[38;5;84m"     # hijau katak
C_ACC2    = ESC + "[38;5;120m"
C_DIM     = ESC + "[38;5;244m"
C_WHITE   = ESC + "[97m"
C_BOLD    = ESC + "[1m"
C_NAVY    = ESC + "[48;5;18m" + ESC + "[38;5;255m"
C_SEL     = ESC + "[48;5;22m" + ESC + "[38;5;231m"
C_RED     = ESC + "[38;5;203m"

def enable_ansi():
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    mode = wintypes.DWORD()
    kernel32.GetConsoleMode(h, ctypes.byref(mode))
    kernel32.SetConsoleMode(h, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

def clear_screen():
    sys.stdout.write(ESC + "[2J" + ESC + "[H")

def pos(y, x):
    sys.stdout.write(f"{ESC}[{y};{x}H")

def hide_cursor(v=True):
    sys.stdout.write(ESC + ("[?25l" if v else "[?25h"))

def human_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024

def clip(text, width):
    return text if len(text) <= width else text[:max(0, width - 1)] + "…"

# ---------- Recycle Bin (sama seperti KatakFILES) ----------
def send_to_recycle_bin(paths):
    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                    ("fFlags", wintypes.WORD), ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]
    op = SHFILEOPSTRUCTW()
    op.hwnd = 0
    op.wFunc = 0x0003  # FO_DELETE
    op.pFrom = "\0".join(paths) + "\0\0"
    op.pTo = None
    op.fFlags = 0x0001 | 0x0010 | 0x0400 | 0x0004
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))

def scan_junk(roots=None, limit=80):
    """Kumpulkan sampah .exe & .zip dari lokasi umum (download-first)."""
    home = os.path.expanduser("~")
    if roots is None:
        roots = [os.path.join(home, "Downloads"), os.path.join(home, "Desktop"),
                 os.environ.get("TEMP", "")]
    found = []
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            depth = dirpath[len(root):].count(os.sep)
            if depth >= 2:
                continue
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in (".exe", ".zip"):
                    p = os.path.join(dirpath, name)
                    try:
                        size = os.path.getsize(p)
                    except OSError:
                        continue
                    found.append((p, size))
    found.sort(key=lambda x: x[1], reverse=True)
    return found[:limit]

def make_zip(paths, dest):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            base = os.path.basename(p.rstrip("\\/"))
            if os.path.isdir(p):
                for dirpath, _, files in os.walk(p):
                    for name in files:
                        full = os.path.join(dirpath, name)
                        arc = os.path.join(base, os.path.relpath(full, p))
                        zf.write(full, arc)
            else:
                zf.write(p, base)

def unique_dest(dest):
    base, ext = os.path.splitext(dest)
    candidate = dest
    i = 1
    while os.path.exists(candidate):
        suffix = "_1" if i == 1 else f"_{i}"
        candidate = f"{base}{suffix}{ext}"
        i += 1
    return candidate

def open_gui_here(cwd):
    """Buka KatakFILES GUI pada folder yang sedang dilihat."""
    candidates = [
        r"C:\Program Files\KatakFILES\KatakFILES.exe",
        r"C:\Program Files (x86)\KatakFILES\KatakFILES.exe",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "KatakFILES", "katakfiles.py"),
    ]
    for c in candidates:
        c = os.path.normpath(c)
        if os.path.isfile(c):
            if c.endswith(".py"):
                import subprocess
                subprocess.Popen([sys.executable, c, cwd],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                os.startfile(c)
            return True
    return False

class App:
    def __init__(self):
        self.cwd = os.path.expanduser("~")
        self.entries = []       # (name, is_dir, size, path)
        self.index = 0
        self.message = ""
        self.mode = "files"     # files | psb | help
        self.psb_items = []     # (path, size, checked)
        self.psb_index = 0
        self.load_dir(self.cwd)

    # ---------- data ----------
    def load_dir(self, path):
        self.cwd = os.path.normpath(path)
        self.entries = []
        try:
            with os.scandir(self.cwd) as it:
                for e in it:
                    try:
                        st = e.stat()
                        size = st.st_size if e.is_file() else 0
                        mtime = datetime.fromtimestamp(st.st_mtime)
                        self.entries.append((e.name, e.is_dir(), size, mtime, e.path))
                    except OSError:
                        continue
        except (PermissionError, OSError) as err:
            self.message = f"Tidak bisa membaca: {err}"
            return
        self.entries.sort(key=lambda x: (not x[1], x[0].lower()))
        self.index = 0

    def go_up(self):
        parent = os.path.dirname(self.cwd)
        if parent != self.cwd:
            self.load_dir(parent)

    def open_selected(self):
        if not self.entries:
            return
        name, is_dir, _, _, path = self.entries[self.index]
        if is_dir:
            self.load_dir(path)
        else:
            try:
                os.startfile(path)
            except OSError as err:
                self.message = f"Gagal membuka: {err}"

    def selected_paths(self):
        if self.entries:
            return [self.entries[self.index][4]]
        return []

    # ---------- zip ----------
    def zip_selected(self):
        paths = self.selected_paths()
        if not paths:
            return
        base = "arsip"
        dest = unique_dest(os.path.join(self.cwd, base + ".zip"))
        try:
            make_zip(paths, dest)
            self.message = f"Dibuat: {os.path.basename(dest)}"
            self.load_dir(self.cwd)
        except (OSError, zipfile.BadZipFile) as err:
            self.message = f"Gagal zip: {err}"

    # ---------- PSB & ICUL ----------
    def open_psb(self):
        self.psb_items = [(p, s, False) for p, s in scan_junk()]
        self.psb_index = 0
        self.mode = "psb" if self.psb_items else "psb_empty"
        if self.mode == "psb":
            self.message = ""
        else:
            self.message = "Tidak ada sampah .exe/.zip ditemukan"

    def icul(self):
        checked = [p for p, _, c in self.psb_items if c]
        if not checked:
            self.message = "Belum ada yang ditandai — tekan SPACE"
            return
        send_to_recycle_bin(checked)
        self.message = f"ICUL: {len(checked)} item ke Recycle Bin"
        self.psb_items = [(p, s, c) for p, s, c in self.psb_items if not c]

    # ---------- gambar layar ----------
    def draw(self):
        cols, rows = self.terminal_size()
        lines = []
        lines.append(C_NAVY + " " * cols + C_RESET)
        lines[-1] = C_NAVY + f"  {APP}  |  {DEV}  |  v{VERSION}".ljust(cols) + C_RESET

        cwd_line = f"  > {self.cwd}"
        lines.append(C_DIM + clip(cwd_line, cols).ljust(cols) + C_RESET)
        lines.append(C_DIM + "  Nama".ljust(max(cols - 24, 10)) +
                     "Ukuran     Diubah".ljust(22)[:22] + C_RESET)

        body_rows = rows - 6
        if self.mode == "files":
            self._draw_files(lines, cols, body_rows)
        elif self.mode == "psb":
            self._draw_psb(lines, cols, body_rows)
        elif self.mode == "help":
            self._draw_help(lines, cols, body_rows)

        footer_hints = self._footer_hints()
        lines.append(C_NAVY + clip("  " + footer_hints, cols).ljust(cols) + C_RESET)

        sys.stdout.write(pos(1, 1) + "".join(l + "\r\n" for l in lines))
        sys.stdout.flush()

    def terminal_size(self):
        import shutil as _s
        s = _s.get_terminal_size((100, 30))
        return s.columns, s.lines

    def _draw_files(self, lines, cols, body_rows):
        start = max(0, self.index - body_rows + 1)
        visible = self.entries[start:start + body_rows]
        if not visible:
            lines.append(C_DIM + "  (folder kosong)".ljust(cols) + C_RESET)
            for _ in range(body_rows - 1):
                lines.append(" " * cols)
            return
        w_name = max(cols - 27, 10)
        for i in range(body_rows):
            row_i = start + i
            if row_i >= len(self.entries):
                lines.append(" " * cols)
                continue
            name, is_dir, size, mtime, _ = self.entries[row_i]
            label = name + ("/" if is_dir else "")
            size_t = "" if is_dir else human_size(size)
            date_t = mtime.strftime("%Y-%m-%d %H:%M")
            row = f"  {clip(label, w_name).ljust(w_name)}{size_t.rjust(10)}  {date_t}"
            prefix = "›" if row_i == self.index else " "
            style = C_SEL if row_i == self.index else (C_ACC if is_dir else C_WHITE)
            lines.append(style + (prefix + row)[:cols].ljust(cols) + C_RESET)

    def _draw_psb(self, lines, cols, body_rows):
        checked_n = sum(1 for _, _, c in self.psb_items if c)
        total = sum(s for p, s, _ in self.psb_items if True)
        hdr = f"  PSB — Pembersih Sampah Bersih   [{checked_n} dipilih]"
        lines.append(C_ACC2 + hdr.ljust(cols) + C_RESET)
        start = max(0, self.psb_index - body_rows + 1)
        visible = self.psb_items[start:start + body_rows - 1]
        if not visible:
            lines.append(C_WHITE + "  (tidak ada sampah .exe/.zip)".ljust(cols) + C_RESET)
            for _ in range(body_rows):
                lines.append(" " * cols)
            return
        w_name = max(cols - 18, 10)
        for i in range(body_rows - 1):
            idx = start + i
            if idx >= len(self.psb_items):
                lines.append(" " * cols)
                continue
            path, size, checked = self.psb_items[idx]
            mark = "[X]" if checked else "[ ]"
            name = os.path.basename(path)
            row = f"  {mark} {clip(name, w_name).ljust(w_name)}{human_size(size).rjust(10)}"
            style = C_SEL if idx == self.psb_index else C_WHITE
            lines.append(style + row[:cols].ljust(cols) + C_RESET)

    def _draw_help(self, lines, cols, body_rows):
        help_text = [
            "  Tombol:",
            "",
            "    Panah Atas/Bawah   pilih item",
            "    Enter              buka folder / file",
            "    Backspace          folder atas",
            "    Z                  compress terpilih -> arsip.zip",
            "    P                  PSB (scan sampah .exe/.zip)",
            "    SPACE (di PSB)     tandai item",
            "    A (di PSB)         tandai semua / kosongkan",
            "    X (di PSB)         ICUL — hapus paksa ke Recycle Bin",
            "    Esc / P (di PSB)   kembali ke file manager",
            "    G                  buka KatakFILES GUI di folder ini",
            "    F5 / R             refresh",
            "    H / F1             bantuan ini",
            "    Q                  keluar",
        ]
        for i in range(body_rows):
            if i < len(help_text):
                lines.append(C_WHITE + help_text[i].ljust(cols) + C_RESET)
            else:
                lines.append(" " * cols)

    def _footer_hints(self):
        if self.mode == "files":
            msg = self.message + "  " if self.message else ""
            return msg + "Enter buka | Bksp up | Z zip | P PSB | G GUI | H bantuan | Q keluar"
        if self.mode == "psb":
            return (self.message + "  " if self.message else "") + \
                "SPACE tandai | A semua | X ICUL | P kembali | Q keluar"
        if self.mode == "help":
            return "H kembali"
        return "Q keluar"

    # ---------- input ----------
    def run(self):
        enable_ansi()
        hide_cursor(True)
        clear_screen()
        try:
            import msvcrt
            while True:
                self.draw()
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # tombol khusus
                    key = msvcrt.getwch()
                    self.handle_key(key)
                else:
                    self.handle_char(ch)
        except KeyboardInterrupt:
            pass
        finally:
            hide_cursor(False)
            clear_screen()
            print(f"{APP} — sampai jumpa! ({DEV})")

    def handle_key(self, key):
        if key == "H":      # atas
            self.move_sel(-1)
        elif key == "P":    # bawah
            self.move_sel(1)
        elif key == "K":    # kiri
            self.page_sel(-1)
        elif key == "M":    # kanan
            self.page_sel(1)
        elif key == ";":    # F5/F1 di beberapa console
            self.refresh_action()

    def handle_char(self, ch):
        low = ch.lower()
        if low == "q":
            sys.exit(0)
        if self.mode == "help":
            if low in ("h", "\x1b", "p", "\r"):
                self.mode = "files"
            return
        if low == "h" or ch == "\x00":
            self.mode = "help"
            return
        if self.mode == "psb":
            if low == "p" or ch == "\x1b":
                self.mode = "files"
                self.message = ""
            elif ch == " ":
                self._psb_toggle()
            elif low == "a":
                self._psb_toggle_all()
            elif low == "x":
                self.icul()
            return
        # mode files
        if ch == "\r":
            self.open_selected()
        elif ch == "\x08":   # Backspace
            self.go_up()
        elif low == "z":
            self.zip_selected()
        elif low == "p":
            self.open_psb()
        elif low == "g":
            if open_gui_here(self.cwd):
                self.message = "Membuka KatakFILES GUI…"
            else:
                self.message = "KatakFILES GUI tidak ditemukan"
        elif low == "r":
            self.refresh_action()
        elif low == "c":
            paths = self.selected_paths()
            if paths:
                try:
                    import subprocess
                    subprocess.run(["clip.exe"], input=paths[0].encode("utf-8"),
                                   check=False, creationflags=subprocess.CREATE_NO_WINDOW)
                    self.message = "Path disalin ke clipboard"
                except OSError as err:
                    self.message = f"Gagal: {err}"

    def move_sel(self, delta):
        if self.mode == "files":
            if self.entries:
                self.index = max(0, min(len(self.entries) - 1, self.index + delta))
        elif self.mode == "psb":
            if self.psb_items:
                self.psb_index = max(0, min(len(self.psb_items) - 1, self.psb_index + delta))

    def page_sel(self, delta):
        self.move_sel(delta * 10)

    def refresh_action(self):
        self.load_dir(self.cwd)
        self.message = "Refresh"

    def _psb_toggle(self):
        if not self.psb_items:
            return
        p, s, c = self.psb_items[self.psb_index]
        self.psb_items[self.psb_index] = (p, s, not c)

    def _psb_toggle_all(self):
        if not self.psb_items:
            return
        new = not all(c for _, _, c in self.psb_items)
        self.psb_items = [(p, s, new) for p, s, _ in self.psb_items]

def main():
    if not sys.stdin.isatty():
        print(f"{APP} butuh console interaktif — jalankan dari cmd/terminal.")
        sys.exit(1)
    app = App()
    try:
        app.run()
    except Exception as err:
        hide_cursor(False)
        print(ESC + "[2J" + ESC + "[H", end="")
        print(f"{APP} error: {err}")

if __name__ == "__main__":
    main()
