@echo off
setlocal
cd /d %~dp0
if not exist .venv (py -3 -m venv .venv)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
if not exist data\processed\smartport.sqlite3 python processing\build_database.py
if errorlevel 1 exit /b 1
python -c "import sqlite3,sys; c=sqlite3.connect('data/processed/smartport.sqlite3'); sys.exit(0 if any(x[0]=='ais_positions' for x in c.execute('select name from sqlite_master')) else 1)"
if errorlevel 1 python processing\import_ais.py
if errorlevel 1 exit /b 1
python processing\validate_database.py
if errorlevel 1 exit /b 1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
