"""Build a validated SQLite database from the New Orleans source tables."""
from __future__ import annotations
import csv, json, sqlite3, sys, os
from pathlib import Path
from datetime import datetime
import pandas as pd
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data' / 'source'
OUT = ROOT / 'data' / 'processed' / 'smartport.sqlite3'
BUILD_OUT = OUT.with_name('smartport.building.sqlite3')
PORT_ID = 365

def read_pipe(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep='|', dtype=str, keep_default_na=False, low_memory=False)

def safe_float(v):
    try:
        x=float(v)
        return x if pd.notna(x) else None
    except (TypeError, ValueError): return None

def parse_dt(v):
    try: return datetime.strptime(v, '%Y-%m-%d %H:%M:%S').isoformat(sep=' ')
    except (ValueError, TypeError): return None

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if BUILD_OUT.exists(): BUILD_OUT.unlink()
    calls=read_pipe(SRC/'csv'/'portcalls_new_orleans.csv')
    calls['duration_s_num']=pd.to_numeric(calls['duration'],errors='coerce')
    calls['lat_num']=pd.to_numeric(calls['latitude'],errors='coerce')
    calls['lon_num']=pd.to_numeric(calls['longitude'],errors='coerce')
    calls=calls[(calls.duration_s_num>0)&(calls.duration_s_num<30*86400)].copy()
    calls['start_iso']=calls.ts_start.map(parse_dt); calls['end_iso']=calls.ts_end.map(parse_dt)
    calls=calls[calls.start_iso.notna() & calls.end_iso.notna()].copy()

    berth_gj=json.loads((SRC/'geojson'/'berths_new_orleans.geojson').read_text())
    feats=berth_gj['features']
    berth_shapes=[shape(f['geometry']) for f in feats]
    tree=STRtree(berth_shapes)
    berth_rows=[]
    for f,g in zip(feats,berth_shapes):
        p=f['properties']; c=g.representative_point()
        berth_rows.append((str(p.get('berth_id')),str(p.get('berth')),int(p.get('number') or 0),float(c.x),float(c.y),json.dumps(f)))

    conn=sqlite3.connect(BUILD_OUT)
    conn.executescript('''
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE calls(call_id TEXT PRIMARY KEY,mmsi TEXT NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,duration_s REAL NOT NULL,confidence REAL,latitude REAL,longitude REAL,nb_messages INTEGER,berth_id TEXT);
    CREATE INDEX idx_calls_start ON calls(start_time);
    CREATE INDEX idx_calls_end ON calls(end_time);
    CREATE INDEX idx_calls_mmsi ON calls(mmsi);
    CREATE INDEX idx_calls_berth ON calls(berth_id);
    CREATE TABLE berths(berth_id TEXT PRIMARY KEY,berth_code TEXT,source_number INTEGER,centroid_lon REAL,centroid_lat REAL,feature_json TEXT NOT NULL);
    CREATE TABLE vessel_types(mmsi TEXT PRIMARY KEY,vessel_type TEXT,source TEXT);
    CREATE TABLE trajectories(id TEXT PRIMARY KEY,idtraj TEXT,rank_in_traj INTEGER,mmsi TEXT,port_origin TEXT,port_destination TEXT,event_time TEXT);
    CREATE INDEX idx_traj_mmsi ON trajectories(mmsi,event_time);
    CREATE TABLE area_presence(mmsi TEXT PRIMARY KEY,presence_json TEXT NOT NULL);
    ''')
    conn.executemany('INSERT INTO berths VALUES(?,?,?,?,?,?)',berth_rows)

    # Spatially assign coordinate-bearing calls to a berth polygon; use covers to include boundary points.
    call_rows=[]
    for r in calls.itertuples(index=False):
        lat=safe_float(r.latitude); lon=safe_float(r.longitude); assigned=None
        if lat is not None and lon is not None and -90<=lat<=90 and -180<=lon<=180:
            pt=Point(lon,lat)
            for ix in tree.query(pt):
                if berth_shapes[int(ix)].covers(pt):
                    assigned=str(feats[int(ix)]['properties'].get('berth_id')); break
        call_rows.append((str(r.id),str(r.mmsi),r.start_iso,r.end_iso,float(r.duration_s_num),safe_float(r.conf),lat,lon,int(float(r.nb_mes)) if str(r.nb_mes).strip() else None,assigned))
    conn.executemany('INSERT OR REPLACE INTO calls VALUES(?,?,?,?,?,?,?,?,?,?)',call_rows)

    for fn,source in [('vesseltype_original.csv','original'),('vesseltype_enriched.csv','enriched')]:
        df=read_pipe(SRC/'csv'/fn)
        for r in df.itertuples(index=False):
            # Enriched is preferred when it has a usable type.
            old=conn.execute('SELECT vessel_type FROM vessel_types WHERE mmsi=?',(str(r.mmsi),)).fetchone()
            typ=str(r.vesseltype) if str(r.vesseltype).strip() else None
            if typ and (source=='enriched' or not old or not old[0]):
                conn.execute('INSERT OR REPLACE INTO vessel_types VALUES(?,?,?)',(str(r.mmsi),typ,source))

    traj=read_pipe(SRC/'csv'/'trajectories_target_vessels.csv')
    traj_rows=[]
    for r in traj.itertuples(index=False):
        dt=parse_dt(r.ts)
        if dt:
            traj_rows.append((str(r.id),str(r.idtraj),int(r.rankintraj) if str(r.rankintraj).isdigit() else None,str(r.mmsi),str(r.port_origin),str(r.port_destination),dt))
    conn.executemany('INSERT OR REPLACE INTO trajectories VALUES(?,?,?,?,?,?,?)',traj_rows)

    ap=read_pipe(SRC/'csv'/'areapresence_target_vessels.csv')
    conn.executemany('INSERT OR REPLACE INTO area_presence VALUES(?,?)',[(str(r.mmsi),json.dumps(r._asdict(),separators=(',',':'))) for r in ap.itertuples(index=False)])
    metadata={'port_name':'New Orleans','country':'United States of America','port_id':str(PORT_ID),'source_year':'2019','source_timezone':'UTC not specified by source; timestamps retained as source-local/unspecified','calls_valid':str(len(call_rows)),'berth_clusters':str(len(berth_rows)),'trajectory_events':str(len(traj_rows)),'schema_version':'1.0'}
    conn.executemany('INSERT INTO metadata VALUES(?,?)',metadata.items())
    # Preserve a previously imported AIS table when rebuilding the port-call database.
    conn.commit()
    preserved_ais = 0
    if OUT.exists():
        conn.execute('ATTACH DATABASE ? AS previous_db', (str(OUT),))
        has_ais = conn.execute("SELECT 1 FROM previous_db.sqlite_master WHERE type='table' AND name='ais_positions'").fetchone()
        if has_ais:
            conn.execute('CREATE TABLE ais_positions AS SELECT * FROM previous_db.ais_positions')
            conn.executescript('''
                CREATE INDEX idx_ais_time ON ais_positions(timestamp);
                CREATE INDEX idx_ais_mmsi_time ON ais_positions(mmsi,timestamp);
                CREATE INDEX idx_ais_segment ON ais_positions(mmsi,track_segment,timestamp);
            ''')
            preserved_ais = conn.execute('SELECT COUNT(*) FROM ais_positions').fetchone()[0]
        conn.execute('DETACH DATABASE previous_db')
    conn.commit()
    # Validate the complete replacement before atomically swapping it into place.
    n=conn.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
    b=conn.execute('SELECT COUNT(*) FROM berths').fetchone()[0]
    assert n==len(call_rows) and n>100000, f'Unexpected call count {n}'
    assert b==99, f'Unexpected berth feature count {b}'
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.close()
    os.replace(BUILD_OUT, OUT)
    print(json.dumps({'database':str(OUT),'valid_calls':n,'berth_clusters':b,'trajectory_events':len(traj_rows),
        'preserved_ais_records':preserved_ais,'size_mb':round(OUT.stat().st_size/1024/1024,2)},indent=2))
if __name__=='__main__': main()
