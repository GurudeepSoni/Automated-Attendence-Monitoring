@echo off
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate
pip install -q -r requirements.txt
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:5000"
python app.py
pause
