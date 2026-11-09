#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/sphero-neu"

PYTHON_EXE=""
if [ -x ".venv/bin/python" ]; then
    PYTHON_EXE=".venv/bin/python"
elif [ -x "../.venv/bin/python" ]; then
    PYTHON_EXE="../.venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON_EXE=".venv/Scripts/python.exe"
elif [ -x "../.venv/Scripts/python.exe" ]; then
    PYTHON_EXE="../.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_EXE="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXE="python"
else
    echo "Error: Python 3 not found. Please install Python 3.10+." >&2
    exit 1
fi

exec "$PYTHON_EXE" web/server.py --host 0.0.0.0 --port 8080 "$@"
