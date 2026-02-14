@echo off
cd /d %~dp0
python price_gap_alert_gui.py
if errorlevel 1 (
  python3 price_gap_alert_gui.py
)
pause
