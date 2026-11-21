import sqlite3,json,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'data'/'processed'/'smartport.sqlite3'
if not p.exists(): print('DATABASE_MISSING');sys.exit(1)
c=sqlite3.connect(p)
checks={
 'integrity':c.execute('PRAGMA integrity_check').fetchone()[0],
 'calls':c.execute('SELECT COUNT(*) FROM calls').fetchone()[0],
 'berths':c.execute('SELECT COUNT(*) FROM berths').fetchone()[0],
 'distinct_vessels':c.execute('SELECT COUNT(DISTINCT mmsi) FROM calls').fetchone()[0],
 'null_timestamps':c.execute("SELECT COUNT(*) FROM calls WHERE start_time IS NULL OR end_time IS NULL").fetchone()[0],
 'negative_durations':c.execute('SELECT COUNT(*) FROM calls WHERE duration_s<=0').fetchone()[0],
 'trajectory_events':c.execute('SELECT COUNT(*) FROM trajectories').fetchone()[0],
 'vessel_types':c.execute('SELECT COUNT(*) FROM vessel_types').fetchone()[0],
 'ais_records':c.execute("SELECT COUNT(*) FROM ais_positions").fetchone()[0] if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone() else 0,
 'ais_vessels':c.execute('SELECT COUNT(DISTINCT mmsi) FROM ais_positions').fetchone()[0] if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone() else 0,
}
c.close();print(json.dumps(checks,indent=2))
assert checks['integrity']=='ok' and checks['calls']>100000 and checks['berths']==99 and checks['negative_durations']==0 and checks['null_timestamps']==0
assert checks['ais_records']==651044 and checks['ais_vessels']==477, 'AIS table missing or incomplete; run processing/import_ais.py'
