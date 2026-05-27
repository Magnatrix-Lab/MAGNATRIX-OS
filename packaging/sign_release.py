#!/usr/bin/env python3
"""
MAGNATRIX-OS Release Signing Script
Sign release tarball/zip with GPG and generate checksums.
Usage:
    python packaging/sign_release.py packages/magnatrix-os-linux/
"""
import os, sys, hashlib, subprocess, argparse, json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_gpg(path: Path) -> Path:
    sig_path = path.with_suffix(path.suffix + ".asc")
    try:
        subprocess.run(
            ["gpg", "--detach-sign", "--armor", "-o", str(sig_path), str(path)],
            check=True,
            capture_output=True,
        )
        print(f"[SIGN] GPG signature: {sig_path}")
        return sig_path
    except FileNotFoundError:
        print("[WARN] gpg not found, skipping GPG signature")
        return None
    except subprocess.CalledProcessError as e:
        print(f"[WARN] GPG signing failed: {e}")
        return None


def create_manifest(dist_dir: Path) -> Path:
    manifest = {"files": {}, "checksums": {}}
    for f in sorted(dist_dir.rglob("*")):
        if f.is_file() and f.name != "manifest.json":
            rel = f.relative_to(dist_dir).as_posix()
            manifest["checksums"][rel] = sha256_file(f)
            manifest["files"][rel] = {"size": f.stat().st_size}

    manifest_path = dist_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[SIGN] Manifest: {manifest_path}")
    return manifest_path


def sign_manifest(manifest_path: Path) -> Path:
    return sign_gpg(manifest_path)


def verify_signature(path: Path, sig_path: Path) -> bool:
    try:
        subprocess.run(
            ["gpg", "--verify", str(sig_path), str(path)],
            check=True,
            capture_output=True,
        )
        print(f"[VERIFY] {path.name}: VALID")
        return True
    except Exception as e:
        print(f"[VERIFY] {path.name}: INVALID ({e})")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dist_dir", type=Path, help="Distribution directory to sign")
    args = parser.parse_args()

    if not args.dist_dir.exists():
        print(f"[ERR] Directory not found: {args.dist_dir}")
        sys.exit(1)

    print(f"[SIGN] Signing release: {args.dist_dir}")
    manifest = create_manifest(args.dist_dir)
    sign_manifest(manifest)
    print("[SIGN] Done.")


if __name__ == "__main__":
    main()
