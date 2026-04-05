#!/bin/bash
set -e

echo "=== Setting up hkma-news-media ==="

# Create virtual environment
python3 -m venv .venv
echo "Virtual environment created at .venv/"

# Activate and install dependencies
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
echo "Dependencies installed."

# Create required directories
mkdir -p library/insight library/speech insight/output speech/output
echo "Directories created."

echo ""
echo "=== Setup complete ==="
echo "Activate the environment with: source .venv/bin/activate"
echo "Then run: bash run.sh"
