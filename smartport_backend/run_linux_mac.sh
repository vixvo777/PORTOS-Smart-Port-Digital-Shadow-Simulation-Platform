#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f data/processed/smartport.sqlite3 ]; then python processing/build_database.py; fi
python -c "import sqlite3,sys; c=sqlite3.connect('data/processed/smartport.sqlite3'); sys.exit(0 if any(x[0]=='ais_positions' for x in c.execute('select name from sqlite_master')) else 1)" || python processing/import_ais.py
python processing/validate_database.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
