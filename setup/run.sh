#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"

if [ ! -x "${VENV_PYTHON}" ]; then
    echo "Virtual environment not found."
    echo "Please run ./setup/setup.sh first."
    exit 1
fi

echo "Running M-WAVE..."
"${VENV_PYTHON}" -m m_wave
