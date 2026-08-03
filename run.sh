#!/usr/bin/env bash
set -e

# Change to script directory / project root
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Virtual environment not found."
    echo "Please run ./setup.sh first."
    exit 1
fi

echo "Running the app..."
.venv/bin/python -m m_wave