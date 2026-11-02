@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
flask --app app run --host=0.0.0.0 --port=5001 --debug
