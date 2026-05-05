#!/usr/bin/env bash
# vecpic GUI launcher
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python3"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install -e "$PROJECT_DIR"
fi

exec "$VENV_PYTHON" -m vecpic --gui
