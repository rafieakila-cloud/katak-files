# KatakFILES

> File manager ringan untuk Windows — mirip File Explorer, tanpa Electron.
> Python + Tkinter + tkinterdnd2. Ikon: Segoe MDL2 Assets (font bawaan Windows).

## Jalankan

Klik dua kali `run.bat`, atau:

```bat
pythonw katakfiles.py
```

## Fitur

- Sidebar: Akses cepat, semua **drive** (terdeteksi: tetap/USB removable/jaringan),
  **Linux (WSL)** + **Rufus** bila terpasang
- Drag & drop **dari Explorer ke aplikasi** + seret antar-folder di dalam aplikasi
- Double-click buka; klik kolom untuk mengurutkan; folder selalu di atas
- Pencarian langsung (filter nama)
- **Copy / Cut / Paste**, Rename (F2), Hapus ke **Recycle Bin** (Del)
- **File besar (>= 500 MB)**: animasi kodok membersihkan tempat sampah saat menghapus
- ZIP: **Extract Here / Extract to… / Compress to .zip** — aman dari zip-slip
- New Folder / New File, klik kanan untuk semua aksi
- Status bar: jumlah item + sisa ruang drive saat ini
- Dark theme hijau katak, Segoe MDL2 Assets

## Roadmap

- dikemas `.exe` (PyInstaller) + installer muncul di **Settings → Apps**
- tab, preview gambar, toggle dark/light, icon file custom
- pembakar sampah temp/cache dengan mode pratinjau
