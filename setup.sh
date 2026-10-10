#!/usr/bin/env bash
# QU-Gate setup for Ubuntu / WSL. Run from the project folder:   bash setup.sh
# It needs no sudo. It is safe to run again.
set -euo pipefail
cd "$(dirname "$0")"
VENV="${QUGATE_VENV:-$HOME/.venvs/qu-gate}"
export PATH="$HOME/.local/bin:$PATH"

echo "== 1/4  Python 3.12 environment at $VENV"
if [ ! -x "$VENV/bin/python" ]; then
  mkdir -p "$(dirname "$VENV")"
  if [ -z "${QUGATE_FORCE_UV:-}" ] && command -v python3.12 >/dev/null 2>&1 \
     && python3.12 -m venv "$VENV" >/dev/null 2>&1 && [ -x "$VENV/bin/pip" ]; then
    echo "   created with the system python3.12"
  else
    rm -rf "$VENV"
    if ! command -v uv >/dev/null 2>&1; then
      echo "   python3.12 with venv was not found. Installing uv (a small tool that downloads Python 3.12)..."
      if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
      else
        wget -qO- https://astral.sh/uv/install.sh | sh
      fi
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    fi
    uv venv --python 3.12 --seed "$VENV"
    echo "   created with uv"
  fi
else
  echo "   already exists"
fi
"$VENV/bin/python" --version

echo "== 2/4  Installing packages (this takes a few minutes the first time)"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -r requirements.txt pytest

echo "== 3/4  Settings file"
if [ -f .env ]; then
  echo "   .env already exists (not changed)"
else
  cp .env.example .env
  echo "   created .env  (add your API key there; without a key the app runs in DEMO MODE)"
fi

echo "== 4/4  Running the tests"
"$VENV/bin/python" -m pytest -q -p no:cacheprovider

echo
echo "SETUP DONE."
echo "Start the app with:   bash run.sh"
echo "Then open in your browser:   http://localhost:8501"
