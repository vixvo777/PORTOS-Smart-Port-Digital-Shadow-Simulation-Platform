from __future__ import annotations
import csv, gzip, sqlite3, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AIS_FILE = ROOT / "data" / "source" / "ais" / "new_orleans_ais_2019-06-15_16_clean.csv.gz"
DB_FILE = Path(os.getenv("SMARTPORT_DB", ROOT / "data" / "processed" / "smartport.sqlite3"))

def main():
    if not AIS_FILE.exists():
        raise SystemExit(f"AIS file not found: {AIS_FILE}")
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_FILE)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("DROP TABLE IF EXISTS ais_positions_staging")
        con.execute("""
        CREATE TABLE ais_positions_staging (
          id INTEGER PRIMARY KEY,
          mmsi TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          longitude REAL NOT NULL,
          latitude REAL NOT NULL,
          sog REAL,
          cog REAL,
          heading REAL,
          navigation_status REAL,
          vessel_name TEXT,
          vessel_type TEXT,
          vessel_length REAL,
          width REAL,
          draft REAL,
          track_segment INTEGER NOT NULL,
          gap_seconds REAL
        )""")
        sql = """INSERT INTO ais_positions
        (mmsi,timestamp,longitude,latitude,sog,cog,heading,navigation_status,
         vessel_name,vessel_type,vessel_length,width,draft,track_segment,gap_seconds)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        batch=[]
        with gzip.open(AIS_FILE, "rt", encoding="utf-8", newline="") as f:
            reader=csv.DictReader(f)
            required={"mmsi","base_date_time","longitude","latitude","track_segment"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise SystemExit(f"Missing required AIS columns. Found: {reader.fieldnames}")
            for r in reader:
                def num(k):
                    v=(r.get(k) or "").strip()
                    if not v: return None
                    try: return float(v)
                    except ValueError: return None
                batch.append((
                    r["mmsi"],r["base_date_time"],float(r["longitude"]),float(r["latitude"]),
                    num("sog"),num("cog"),num("heading"),num("navigation_status"),
                    r.get("vessel_name") or None,r.get("vessel_type") or None,
                    num("vessel_length"),num("width"),num("draft"),
                    int(float(r["track_segment"])),num("gap_seconds")
                ))
                if len(batch)>=10000:
                    con.executemany(sql.replace("ais_positions", "ais_positions_staging"),batch); batch.clear()
            if batch: con.executemany(sql.replace("ais_positions", "ais_positions_staging"),batch)
        n=con.execute("SELECT COUNT(*),COUNT(DISTINCT mmsi),MIN(timestamp),MAX(timestamp) FROM ais_positions_staging").fetchone()
        if n[0] == 0 or n[1] == 0:
            raise SystemExit("AIS import produced no valid records; existing AIS table was not changed.")
        # Commit staging rows, then swap and index inside one transaction: any failure
        # rolls back to the previous AIS table while leaving the staging import available.
        con.commit()
        con.execute("BEGIN IMMEDIATE")
        con.execute("DROP TABLE IF EXISTS ais_positions")
        con.execute("ALTER TABLE ais_positions_staging RENAME TO ais_positions")
        con.execute("CREATE INDEX idx_ais_time ON ais_positions(timestamp)")
        con.execute("CREATE INDEX idx_ais_mmsi_time ON ais_positions(mmsi,timestamp)")
        con.execute("CREATE INDEX idx_ais_segment ON ais_positions(mmsi,track_segment,timestamp)")
        con.commit()
        print("AIS IMPORT SUCCESS")
        print(f"Rows: {n[0]:,}")
        print(f"Unique MMSI: {n[1]:,}")
        print(f"Coverage: {n[2]} -> {n[3]}")
        print("SQLite indexes created.")
    finally:
        con.close()

if __name__=="__main__":
    main()
