#!/usr/bin/env python3
"""
MAGNATRIX-OS PyInstaller Build Script
Build single executable for Windows, macOS, and Linux.
Usage:
    python packaging/pyinstaller_build.py --platform linux
"""
import os, sys, shutil, subprocess, argparse, json, platform, glob
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
PACKAGES = REPO_ROOT / "packages"

ASSETS = [
    ("website", "website"),
    ("config", "config"),
]


def detect_platform():
    s = platform.system().lower()
    if s == "darwin": return "mac"
    if s == "windows": return "win"
    return "linux"


def run(cmd, cwd=None):
    print(f"[BUILD] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or str(REPO_ROOT), check=True)


def ensure_pyinstaller():
    try:
        import PyInstaller
    except ImportError:
        print("[BUILD] Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def collect_hidden_imports():
    hidden = []
    for pyfile in REPO_ROOT.rglob("*_native.py"):
        rel = pyfile.relative_to(REPO_ROOT)
        mod = str(rel.with_suffix("")).replace(os.sep, ".")
        hidden.append(mod)
    return list(set(hidden))


def build(platform_id: str):
    ensure_pyinstaller()
    PACKAGES.mkdir(exist_ok=True)
    output_name = f"magnatrix-os-{platform_id}"
    output_dir = PACKAGES / output_name
    if output_dir.exists():
        shutil.rmtree(output_dir)

    hidden = collect_hidden_imports()
    hidden_args = []
    for h in hidden[:100]:
        hidden_args.extend(["--hidden-import", h])

    data_args = []
    for src, dst in ASSETS:
        src_path = REPO_ROOT / src
        if src_path.exists():
            data_args.extend(["--add-data", f"{src_path}{os.pathsep}{dst}"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "magnatrix-os",
        "--onefile",
        "--distpath", str(output_dir),
        "--workpath", str(PACKAGES / "build"),
        "--specpath", str(PACKAGES),
        "--clean",
        "--noconfirm",
    ] + hidden_args + data_args + [str(REPO_ROOT / "magnatrix.py")]

    run(cmd)

    # Copy binary assets
    lib_dir = output_dir / "lib"
    lib_dir.mkdir(exist_ok=True)
    for pattern in [
        "trading/cpp_hft_engine/build/*.so",
        "security/rust_crypto_engine/target/release/*.so",
    ]:
        for f in REPO_ROOT.glob(pattern):
            shutil.copy2(f, lib_dir)
            print(f"[BUILD] Copied binary: {f.name}")

    meta = {
        "version": "0.9.5-alpha",
        "platform": platform_id,
        "python": platform.python_version(),
    }
    (output_dir / "build-info.json").write_text(json.dumps(meta, indent=2))
    print(f"[BUILD] Done: {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["linux", "win", "mac"], default=detect_platform())
    args = parser.parse_args()
    build(args.platform)


if __name__ == "__main__":
    main()
