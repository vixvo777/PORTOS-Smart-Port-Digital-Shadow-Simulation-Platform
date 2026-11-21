from __future__ import annotations
import sqlite3, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/ais", tags=["Historical AIS"])
DB_PATH = Path(os.getenv("SMARTPORT_DB", Path(__file__).resolve().parents[1] / "data" / "processed" / "smartport.sqlite3"))

def connect():
    if not DB_PATH.exists():
        raise HTTPException(503, "Smart Port database is missing.")
    c=sqlite3.connect(DB_PATH)
    c.row_factory=sqlite3.Row
    return c

def iso(s: str) -> str:
    try:
        value=datetime.fromisoformat(s.replace("Z","+00:00"))
        if value.tzinfo is not None:value=value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat(sep=" ")
    except Exception: raise HTTPException(422, "Use an ISO-8601 timestamp; source data timezone is unspecified")

@router.get("/coverage")
def coverage():
    c=connect()
    try:
        exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone()
        if not exists: return {"available":False,"message":"Run python processing/import_ais.py first."}
        r=c.execute("""SELECT COUNT(*) records,COUNT(DISTINCT mmsi) vessels,
          MIN(timestamp) start_time,MAX(timestamp) end_time,
          MIN(longitude) min_lon,MAX(longitude) max_lon,
          MIN(latitude) min_lat,MAX(latitude) max_lat FROM ais_positions""").fetchone()
        return {"available":True,**dict(r),"source":"Uploaded New Orleans AIS sample","historical":True,"timestamp_semantics":"Source timezone unspecified; timestamps are preserved as supplied."}
    finally:c.close()

@router.get("/tracks")
def tracks(start:str=Query(...),end:str=Query(...),mmsi:str|None=None,
           limit:int=Query(200,ge=1,le=2000),min_points:int=Query(2,ge=2,le=100)):
    a,b=iso(start),iso(end)
    if b<=a: raise HTTPException(422,"end must be after start")
    c=connect()
    try:
        sql="""SELECT mmsi,track_segment,COUNT(*) point_count,MIN(timestamp) start_time,
        MAX(timestamp) end_time,MIN(vessel_name) vessel_name,MIN(vessel_type) vessel_type
        FROM ais_positions WHERE timestamp>=? AND timestamp<?"""
        args=[a,b]
        if mmsi: sql+=" AND mmsi=?"; args.append(mmsi)
        sql+=" GROUP BY mmsi,track_segment HAVING COUNT(*)>=? ORDER BY point_count DESC LIMIT ?"
        args.extend([min_points,limit])
        return {"start":a,"end":b,"items":[dict(x) for x in c.execute(sql,args)]}
    finally:c.close()

@router.get("/vessels")
def vessels(start:str=Query(...),end:str=Query(...),limit:int=Query(477,ge=1,le=1000),min_points:int=Query(1,ge=1,le=1000)):
    """List distinct MMSIs by observation volume; each track request returns all segments for that vessel."""
    a,b=iso(start),iso(end)
    if b<=a: raise HTTPException(422,"end must be after start")
    c=connect()
    try:
        rows=c.execute("""SELECT mmsi,COUNT(*) point_count,COUNT(DISTINCT track_segment) track_segments,
            MIN(timestamp) start_time,MAX(timestamp) end_time,MIN(vessel_name) vessel_name,MIN(vessel_type) vessel_type
            FROM ais_positions WHERE timestamp>=? AND timestamp<? GROUP BY mmsi
            HAVING COUNT(*)>=? ORDER BY point_count DESC LIMIT ?""",(a,b,min_points,limit)).fetchall()
        return {"start":a,"end":b,"items":[dict(x) for x in rows],"total_returned":len(rows),
            "note":"Each listed MMSI may contain multiple separate track_segment values; render each segment independently."}
    finally:c.close()

@router.get("/track/{mmsi}")
def vessel_track(mmsi:str,start:str=Query(...),end:str=Query(...)):
    a,b=iso(start),iso(end)
    if b<=a: raise HTTPException(422,"end must be after start")
    c=connect()
    try:
        rows=c.execute("""SELECT timestamp,longitude,latitude,sog,cog,heading,
          navigation_status,track_segment,gap_seconds,vessel_name,vessel_type
          FROM ais_positions WHERE mmsi=? AND timestamp>=? AND timestamp<?
          ORDER BY timestamp""",(mmsi,a,b)).fetchall()
        if not rows: raise HTTPException(404,"No AIS positions for this MMSI in the requested time range.")
        return {"mmsi":mmsi,"count":len(rows),"items":[dict(x) for x in rows],
          "track_rule":"Render each track_segment as a separate line; never bridge segments."}
    finally:c.close()


@router.get("/tracks/bulk")
def bulk_tracks(start:str=Query(...),end:str=Query(...),limit_vessels:int=Query(120,ge=1,le=477),min_points:int=Query(2,ge=2,le=1000)):
    """Fetch a ranked set of observed vessel tracks in one request for the 3D viewer."""
    a,b=iso(start),iso(end)
    if b<=a: raise HTTPException(422,"end must be after start")
    c=connect()
    try:
        vessels=c.execute("""SELECT mmsi,COUNT(*) point_count,MIN(vessel_name) vessel_name,MIN(vessel_type) vessel_type
            FROM ais_positions WHERE timestamp>=? AND timestamp<? GROUP BY mmsi
            HAVING COUNT(*)>=? ORDER BY point_count DESC LIMIT ?""",(a,b,min_points,limit_vessels)).fetchall()
        ids=[str(v["mmsi"]) for v in vessels]
        if not ids:return {"start":a,"end":b,"items":[],"vessels":0,"positions":0}
        marks=",".join("?" for _ in ids)
        rows=c.execute(f"""WITH ranked AS (
            SELECT mmsi,timestamp,longitude,latitude,sog,cog,heading,track_segment,gap_seconds,
              vessel_name,vessel_type,
              ROW_NUMBER() OVER(PARTITION BY mmsi,track_segment ORDER BY timestamp) rn,
              COUNT(*) OVER(PARTITION BY mmsi,track_segment) n
            FROM ais_positions WHERE mmsi IN ({marks}) AND timestamp>=? AND timestamp<?
          ) SELECT mmsi,timestamp,longitude,latitude,sog,cog,heading,track_segment,vessel_name,vessel_type
            FROM ranked WHERE rn=1 OR rn=n OR rn % MAX(1,CAST((n+299)/300 AS INTEGER))=0 OR gap_seconds>300
            ORDER BY mmsi,track_segment,timestamp""",(*ids,a,b)).fetchall()
        grouped={m:{"mmsi":m,"vessel_name":next((v["vessel_name"] for v in vessels if str(v["mmsi"])==m),None),
            "vessel_type":next((v["vessel_type"] for v in vessels if str(v["mmsi"])==m),None),"items":[]} for m in ids}
        for r in rows: grouped[str(r["mmsi"])]["items"].append(dict(r))
        return {"start":a,"end":b,"items":[grouped[m] for m in ids if len(grouped[m]["items"])>=2],
            "vessels":len(ids),"positions":len(rows),"note":"Observed AIS positions, visually sampled to at most about 300 points per track segment while retaining endpoints and >5-minute gap boundaries; track_segment boundaries must remain separate."}
    finally:c.close()

@router.get("/positions")
def positions(timestamp:str=Query(...),window_seconds:int=Query(60,ge=1,le=3600),
              limit:int=Query(3000,ge=1,le=10000)):
    t=datetime.fromisoformat(iso(timestamp))
    a=(t-timedelta(seconds=window_seconds)).isoformat(sep=" ")
    b=(t+timedelta(seconds=window_seconds)).isoformat(sep=" ")
    c=connect()
    try:
        rows=c.execute("""SELECT p.* FROM ais_positions p
          JOIN (SELECT mmsi,MAX(timestamp) ts FROM ais_positions
          WHERE timestamp<=? AND timestamp>=? GROUP BY mmsi) x
          ON p.mmsi=x.mmsi AND p.timestamp=x.ts
          ORDER BY p.mmsi LIMIT ?""",(b,a,limit)).fetchall()
        return {"timestamp":t.isoformat(sep=" "),"window_seconds":window_seconds,
          "count":len(rows),"items":[dict(x) for x in rows],
          "interpretation":"Latest observed position per vessel within the requested time window; not a live feed."}
    finally:c.close()
