#!/bin/bash
cd "$(dirname "$0")"

echo "[1/4] Python 확인..."
python3 --version >/dev/null 2>&1 || {
  echo "Python3가 설치되어 있지 않습니다."
  exit 1
}

echo "[2/4] 가상환경 준비..."
[ -d .venv ] || python3 -m venv .venv

echo "[3/4] 패키지 설치..."
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo "[4/4] 웹 실행..."
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:5000" >/dev/null 2>&1
elif command -v open >/dev/null 2>&1; then
  open "http://127.0.0.1:5000"
fi
./.venv/bin/python app.py
