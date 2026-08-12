#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$SCRIPT_DIR/../../.venv-cuas/python.exe" ]; then
  PYTHON="$SCRIPT_DIR/../../.venv-cuas/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi
"$PYTHON" "$SCRIPT_DIR/verify_hashes.py"
