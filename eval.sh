#!/usr/bin/env bash
# Run the evaluation. Examples:   bash eval.sh            (all 27 documents)
#                                 bash eval.sh --limit 5  (first 5 only, saves free-tier quota)
cd "$(dirname "$0")"
VENV="${QUGATE_VENV:-$HOME/.venvs/qu-gate}"
exec "$VENV/bin/python" -m eval.run_eval "$@"
