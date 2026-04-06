#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://127.0.0.1:8000 >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:8000 >/dev/null 2>&1 || true
fi
python3 app.py
