# before setup make sure the scripts are executable
# with chmod +x setup.sh run.sh

#!/usr/bin/env bash
set -e

# Change to script directory / project root
cd "$(dirname "$0")"

echo "Checking for virtual environment..."

if [ ! -x ".venv/bin/python" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv .venv
else
    echo "Virtual environment found."
fi

echo "DONE"
echo

echo "Installing requirements and upgrading pip..."
.venv/bin/python -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    .venv/bin/python -m pip install -r requirements.txt
else
    echo "requirements.txt not found. Skipping requirements installation."
fi

echo "DONE"
echo

echo "Installing m_wave package in editable mode..."
.venv/bin/python -m pip install -e .

echo "DONE"
echo
echo "Virtual environment ready at:"
echo "$(pwd)/.venv"
echo
echo "To activate the environment in Linux/macOS, run:"
echo "source .venv/bin/activate"
echo
echo "To run the app, run:"
echo "python -m m_wave"