#!/bin/bash
# magnatrix — Shell wrapper for MAGNATRIX CLI
# Tambahkan direktori ini ke PATH atau symlink ke /usr/local/bin
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/cli/magnatrix_cli.py" "$@"