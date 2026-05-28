# MAGNATRIX-OS Windows Build — Task Brief

## Goal
Buatkan build system untuk mengubah MAGNATRIX-OS menjadi aplikasi Windows native (.exe) yang bisa dijalankan tanpa install Python.

## Output yang diharapkan

### 1. PyInstaller Spec (`build/windows/magnatrix.spec`)
- Bundle seluruh Python codebase (493 file, 183 native)
- Bundle folder `website/` (HTML/CSS/JS dashboard + panels)
- Bundle C++ HFT engine compiled .pyd (jika tersedia, fallback ke pure Python)
- Bundle Rust crypto engine compiled .pyd (jika tersedia, fallback ke pure Python)
- Entry point: `magnatrix_win.py` — start kernel + web server + system tray
- Windowed app (no console), dengan fallback console untuk debug
- Icon Windows (.ico) — buat dari ASCII art logo MAGNATRIX

### 2. Windows Entry Point (`build/windows/magnatrix_win.py`)
File ini jadi target PyInstaller. Fungsinya:
```
1. Parse CLI args: --console, --port, --no-tray, --debug
2. Setup logging ke file %APPDATA%\MAGNATRIX-OS\logs\
3. Start kernel (import dari kernel/kernel_native.py)
4. Start HTTP server untuk dashboard (serve website/ folder)
5. Start system tray (WindowsTray dari desktop_tray/tray_native.py)
6. Register signal handler untuk graceful shutdown
7. Keep main thread alive sampai tray exit atau Ctrl+C
```

### 3. Build Scripts
- `build/windows/build_exe.bat` — Build .exe via PyInstaller (Windows batch)
- `build/windows/build_exe.sh` — Build .exe via Wine/PyInstaller (Linux cross-compile)
- `build/windows/requirements_build.txt` — Dependencies khusus build

### 4. NSIS Installer Script (`build/windows/installer.nsi`)
Installer .exe yang:
- Install ke `C:\Program Files\MAGNATRIX-OS\`
- Buat shortcut di Start Menu + Desktop
- Buat uninstaller
- Register ke Windows Registry (HKLM\Software\MAGNATRIX-OS)
- Opsi install service (run at startup)

### 5. Windows Service Wrapper (`build/windows/service_wrapper.py`)
Opsional: wrapper agar MAGNATRIX-OS bisa jadi Windows Service (via pywin32 atau NSSM).

### 6. Version Info (`build/windows/version_info.txt`)
Resource file untuk Windows properties (FileVersion, ProductName, dll).

## Technical Details

### Entry point behavior
```python
# magnatrix_win.py pseudo-code
def main():
    args = parse_args()
    setup_logging(args.log_dir or "%APPDATA%/MAGNATRIX-OS/logs")
    
    kernel = NativeKernel()
    kernel.boot()
    
    web_server = HTTPServer(port=args.port or 8080, root="website/")
    web_server.start_thread()
    
    if not args.no_tray:
        tray = WindowsTray(TrayConfig(tooltip="MAGNATRIX-OS"))
        tray.register("dashboard", lambda: open_browser(f"http://localhost:{args.port}"))
        tray.register("trading", lambda: start_trading())
        tray.register("status", lambda: show_status())
        tray.start()
    
    try:
        while kernel.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        kernel.shutdown()
        web_server.stop()
```

### PyInstaller key configs
- `onefile=False` (folder mode lebih cepat startup, lebih mudah update)
- `windowed=True`
- `icon='build/windows/magnatrix.ico'`
- `datas=[('website', 'website'), ('*.md', '.')]`
- Hidden imports untuk semua native modules (auto-scan `*_native.py`)

## Struktur output build
```
dist/MAGNATRIX-OS/
├── magnatrix.exe          # Entry point
├── python311.dll          # Python runtime
├── _internal/             # PyInstaller internal
│   ├── ...
├── kernel/
├── ai/
├── runtime/
├── website/
│   ├── dashboard.html
│   └── panels/
├── trading/
│   └── cpp_hft_engine/
├── security/
│   └── rust_crypto_engine/
└── ...
```

## Acceptance Criteria
- [ ] `python -m PyInstaller build/windows/magnatrix.spec` berhasil
- [ ] `dist/MAGNATRIX-OS/magnatrix.exe` bisa dijalankan
- [ ] System tray muncul saat dijalankan
- [ ] Dashboard bisa dibuka dari browser (http://localhost:8080)
- [ ] NSIS installer compile berhasil (makensis installer.nsi)
- [ ] Semua file pure Python tetap berfungsi (fallback jika C++/Rust .pyd tidak ada)
