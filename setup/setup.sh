#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"

echo "Project root: ${PROJECT_ROOT}"
echo

if [ ! -x "${VENV_PYTHON}" ]; then
    echo "Virtual environment not found. Creating it..."

    uv venv \
        --python 3.11 \
        --prompt m-wave \
        "${PROJECT_ROOT}/.venv"
else
    echo "Virtual environment found."
fi

echo
echo "Installing requirements..."

if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
    uv pip install \
        -r "${PROJECT_ROOT}/requirements.txt" \
        --python "${VENV_PYTHON}"
fi

echo
echo "Installing m_wave package in editable mode..."

uv pip install \
    -e "${PROJECT_ROOT}" \
    --python "${VENV_PYTHON}"

echo
echo "Virtual environment ready at:"
echo "${PROJECT_ROOT}/.venv"
echo
echo "Activate it with:"
echo "source .venv/bin/activate"
echo
echo "Run the application with:"
echo "python -m m_wave"
