#!/usr/bin/env bash
# Start the QU-Gate app. Stop it with Ctrl+C.
cd "$(dirname "$0")"
VENV="${QUGATE_VENV:-$HOME/.venvs/qu-gate}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "The environment is missing. Run this first:   bash setup.sh"
  exit 1
fi
echo "Open in your browser:   http://localhost:8501"
exec "$VENV/bin/python" -m streamlit run app.py
