from __future__ import annotations
import json, math, os, sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parents[1]
DB_PATH=Path(os.getenv('SMARTPORT_DB', ROOT/'data'/'processed'/'smartport.sqlite3'))
app=FastAPI(title='Smart Port Digital Shadow API',version='1.0.0',description='Historical-data-driven New Orleans port analytics and counterfactual berth allocation.')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['*'],allow_headers=['*'])

def db():
    if not DB_PATH.exists(): raise HTTPException(503,'Database not built. Run: python processing/build_database.py')
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def parse_time(s:str)->datetime:
    try: return datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=None)
    except Exception: raise HTTPException(422,f'Invalid datetime: {s}. Use YYYY-MM-DDTHH:MM:SS.')

def rowdict(r): return dict(r) if r else None

@app.get('/')
def root(): return {'name':'Smart Port Digital Shadow API','version':'1.0.0','docs':'/docs','health':'/api/v1/health'}

@app.get('/api/v1/health')
def health():
    c=db()
    try:
        check=c.execute('PRAGMA integrity_check').fetchone()[0]
        return {'status':'ok' if check=='ok' else 'error','database':str(DB_PATH),'integrity':check,'port':'New Orleans','port_id':365}
    finally:c.close()

@app.get('/api/v1/overview')
def overview():
    c=db()
    try:
        n=c.execute('SELECT COUNT(*) n,COUNT(DISTINCT mmsi) vessels,MIN(start_time) first,MAX(end_time) last,AVG(duration_s) mean, SUM(CASE WHEN berth_id IS NOT NULL THEN 1 ELSE 0 END) assigned FROM calls').fetchone()
        d=c.execute('SELECT duration_s FROM calls ORDER BY duration_s').fetchall()
        vals=[x[0]/3600 for x in d]
        def pct(p): return round(vals[min(len(vals)-1,max(0,int(math.ceil(p*len(vals))-1)))],2) if vals else None
        return {'port':'New Orleans','country':'United States of America','port_id':365,'calls':n['n'],'vessels':n['vessels'],'berth_clusters':c.execute('SELECT COUNT(*) FROM berths').fetchone()[0],'calls_with_spatial_berth_match':n['assigned'],'first_event':n['first'],'last_event':n['last'],'mean_call_duration_hours':round(n['mean']/3600,2),'median_call_duration_hours':pct(.5),'p90_call_duration_hours':pct(.9),'p95_call_duration_hours':pct(.95),'interpretation':'Recorded port-call/stopping duration, not verified anchorage waiting time.'}
    finally:c.close()

@app.get('/api/v1/map/port')
def port_geojson():
    p=ROOT/'data'/'source'/'geojson'/'port_new_orleans.geojson'; return json.loads(p.read_text())
@app.get('/api/v1/map/berths')
def berth_geojson():
    p=ROOT/'data'/'source'/'geojson'/'berths_new_orleans.geojson'; return json.loads(p.read_text())

@app.get('/api/v1/berths')
def berths():
    c=db()
    try:return [dict(x) for x in c.execute('SELECT berth_id,berth_code,source_number,centroid_lon,centroid_lat FROM berths ORDER BY berth_code')]
    finally:c.close()

@app.get('/api/v1/calls')
def calls(start:str=Query(...),end: str=Query(...),limit:int=Query(500,ge=1,le=10000),offset:int=Query(0,ge=0),mmsi:Optional[str]=None,berth_id:Optional[str]=None):
    a=parse_time(start).isoformat(sep=' '); b=parse_time(end).isoformat(sep=' ')
    if b<=a: raise HTTPException(422,'end must be after start')
    c=db()
    try:
        sql='''SELECT call_id,mmsi,start_time,end_time,duration_s,confidence,latitude,longitude,nb_messages,berth_id FROM calls WHERE start_time>=? AND start_time<?'''; args=[a,b]
        if mmsi:sql+=' AND mmsi=?';args.append(mmsi)
        if berth_id:sql+=' AND berth_id=?';args.append(berth_id)
        total=c.execute('SELECT COUNT(*) FROM ('+sql+')',args).fetchone()[0]
        rows=c.execute(sql+' ORDER BY start_time LIMIT ? OFFSET ?',args+[limit,offset]).fetchall()
        return {'total':total,'limit':limit,'offset':offset,'items':[dict(x) for x in rows]}
    finally:c.close()

@app.get('/api/v1/vessels/{mmsi}')
def vessel(mmsi:str):
    c=db()
    try:
        rows=c.execute('''SELECT c.*,v.vessel_type,v.source as vessel_type_source FROM calls c LEFT JOIN vessel_types v USING(mmsi) WHERE c.mmsi=? ORDER BY c.start_time''',(mmsi,)).fetchall()
        if not rows:raise HTTPException(404,'Vessel MMSI not found in New Orleans historical calls')
        return {'mmsi':mmsi,'vessel_type':rows[0]['vessel_type'],'calls':[dict(x) for x in rows]}
    finally:c.close()

@app.get('/api/v1/analytics/dwell')
def dwell(start:Optional[str]=None,end:Optional[str]=None):
    c=db()
    try:
        sql='SELECT duration_s FROM calls WHERE 1=1';args=[]
        if start:sql+=' AND start_time>=?';args.append(parse_time(start).isoformat(sep=' '))
        if end:sql+=' AND start_time<?';args.append(parse_time(end).isoformat(sep=' '))
        vals=[r[0]/3600 for r in c.execute(sql,args)]
        if not vals:return {'count':0}
        vals.sort()
        def p(x):return round(vals[min(len(vals)-1,int(math.ceil(x*len(vals))-1))],2)
        return {'count':len(vals),'mean_hours':round(sum(vals)/len(vals),2),'median_hours':p(.5),'p75_hours':p(.75),'p90_hours':p(.9),'p95_hours':p(.95),'metric':'recorded_port_call_duration','not_queue_waiting':True}
    finally:c.close()

@app.get('/api/v1/analytics/berths')
def berth_analytics(start:Optional[str]=None,end:Optional[str]=None):
    c=db()
    try:
        sql='''SELECT b.berth_id,b.berth_code,b.centroid_lon,b.centroid_lat,COUNT(c.call_id) calls,COALESCE(SUM(c.duration_s),0) occupied_seconds FROM berths b LEFT JOIN calls c ON c.berth_id=b.berth_id''';args=[]; cond=[]
        if start:cond.append('c.start_time>=?');args.append(parse_time(start).isoformat(sep=' '))
        if end:cond.append('c.start_time<?');args.append(parse_time(end).isoformat(sep=' '))
        if cond:sql+=' AND '+' AND '.join(cond)
        sql+=' GROUP BY b.berth_id ORDER BY calls DESC'
        return {'items':[dict(x) for x in c.execute(sql,args)],'assignment_note':'Spatial point-in-polygon matches to observed stopping-cluster polygons; not verified operational berth assignments.'}
    finally:c.close()

@app.get('/api/v1/analytics/timeline')
def timeline(granularity:str=Query('day',pattern='^(day|month)$')):
    fmt='%Y-%m' if granularity=='month' else '%Y-%m-%d'
    c=db()
    try:
        rows=c.execute('SELECT start_time,duration_s FROM calls ORDER BY start_time').fetchall(); agg={}
        for r in rows:
            k=datetime.fromisoformat(r['start_time']).strftime(fmt); a=agg.setdefault(k,{'calls':0,'duration_hours':0.0});a['calls']+=1;a['duration_hours']+=r['duration_s']/3600
        return {'granularity':granularity,'items':[{'period':k,'calls':v['calls'],'duration_hours':round(v['duration_hours'],2)} for k,v in sorted(agg.items())]}
    finally:c.close()

class ScenarioRequest(BaseModel):
    timestamp:str
    horizon_hours:int=Field(24,ge=1,le=168)
    active_berths:int=Field(99,ge=1,le=99)
    traffic_multiplier:float=Field(1.0,ge=1.0,le=3.0)
    strategy:str=Field('optimized',pattern='^(historical_fifo|optimized)$')
    blocked_berth_ids:list[str]=Field(default_factory=list)


def _schedule(demand, berths, strategy, timestamp):
    free_at={b['berth_id']:timestamp for b in berths}
    assignments=[]; waits=[]
    for item in sorted(demand,key=lambda x:(x['start_time'],str(x['demand_id']))):
        arrival=datetime.fromisoformat(item['start_time'])
        duration=max(60.0,float(item['duration_s'] or 60))
        ranked=[]
        for b in berths:
            start_at=max(free_at[b['berth_id']],arrival)
            finish=start_at+timedelta(seconds=duration)
            dist=0.0
            if item.get('latitude') is not None and item.get('longitude') is not None:
                dx=(float(b['centroid_lon'] or 0)-float(item['longitude']))*math.cos(math.radians(float(item['latitude'])))
                dy=float(b['centroid_lat'] or 0)-float(item['latitude'])
                dist=math.hypot(dx,dy)
            ranked.append((start_at,finish,dist,b))
        if strategy=='historical_fifo':
            preferred=next((z for z in ranked if z[3]['berth_id']==item.get('berth_id')),None)
            chosen=preferred if preferred is not None else min(ranked,key=lambda z:(z[0],z[1],z[2],z[3]['berth_id']))
        else:
            chosen=min(ranked,key=lambda z:(z[1],z[0],z[2],z[3]['berth_id']))
        start_at,finish,_,berth=chosen
        wait=max(0.0,(start_at-arrival).total_seconds()/3600)
        free_at[berth['berth_id']]=finish; waits.append(wait)
        assignments.append({'demand_id':item['demand_id'],'source_call_id':item['call_id'],'mmsi':item['mmsi'],
            'counterfactual_copy':bool(item['scenario_copy']),'arrival_proxy':item['start_time'],
            'assigned_start':start_at.isoformat(sep=' '),'assigned_end':finish.isoformat(sep=' '),
            'berth_id':berth['berth_id'],'berth_code':berth['berth_code'],
            'modeled_wait_hours':round(wait,3),'historical_observed_berth_id':item.get('berth_id')})
    return assignments,waits


@app.post('/api/v1/scenarios/allocate')
def allocate(req:ScenarioRequest):
    """Compare a modeled historical-demand baseline with a counterfactual schedule."""
    t=parse_time(req.timestamp); horizon_end=t+timedelta(hours=req.horizon_hours)
    c=db()
    try:
        allb=[dict(r) for r in c.execute('SELECT berth_id,berth_code,centroid_lon,centroid_lat FROM berths').fetchall()]
        if not allb: raise HTTPException(503,'No berth clusters loaded')
        known={b['berth_id'] for b in allb}; blocked=set(req.blocked_berth_ids)
        unknown=sorted(blocked-known)
        if unknown: raise HTTPException(422,f'Unknown blocked berth IDs: {unknown[:10]}')
        usable=[b for b in allb if b['berth_id'] not in blocked]
        if not usable: raise HTTPException(422,'Scenario has no active berth clusters')
        hist=c.execute('SELECT call_id,mmsi,start_time,end_time,duration_s,latitude,longitude,berth_id FROM calls WHERE start_time>=? AND start_time<? ORDER BY start_time',
            (t.isoformat(sep=' '),horizon_end.isoformat(sep=' '))).fetchall()
        base=[{**dict(x),'scenario_copy':False,'demand_id':str(x['call_id'])} for x in hist]
        if not base:
            return {'timestamp':t.isoformat(),'horizon_hours':req.horizon_hours,'baseline':{'historical_calls':0,'modeled_queue_wait_hours':None,'mean_verified_queue_wait_hours':None},
                'scenario':{'demand_events':0,'historical_events':0,'counterfactual_demand_copies':0,'mean_modeled_queue_wait_hours':None,'max_modeled_queue_wait_hours':None,'berths_used':0},'items':[],
                'notes':['No historical calls start in this time window. Choose another 2019 timestamp.']}
        usage={r['berth_id']:r['n'] for r in c.execute('SELECT berth_id,COUNT(*) n FROM calls WHERE berth_id IS NOT NULL GROUP BY berth_id')}
        active=sorted(usable,key=lambda b:(-usage.get(b['berth_id'],0),b['berth_code']))[:req.active_berths]
        _,baseline_waits=_schedule(base,usable,'optimized',t)
        demand=list(base); extra_n=int(round(len(base)*(req.traffic_multiplier-1)))
        for i in range(extra_n):
            src=base[i % len(base)]; offset=(i+1)*(req.horizon_hours*3600)/(extra_n+1); st=t+timedelta(seconds=offset)
            demand.append({**src,'start_time':st.isoformat(sep=' '),'end_time':(st+timedelta(seconds=max(60,float(src['duration_s'])))).isoformat(sep=' '),
                'scenario_copy':True,'demand_id':f"CF-{i+1:05d}-{src['call_id']}"})
        assignments,waits=_schedule(demand,active,req.strategy,t)
        def stats(values):
            if not values:return {'mean':None,'median':None,'p90':None,'max':None}
            a=sorted(values); n=len(a)
            return {'mean':round(sum(a)/n,3),'median':round(a[int(.5*(n-1))],3),'p90':round(a[int(.9*(n-1))],3),'max':round(a[-1],3)}
        bs=stats(baseline_waits); ss=stats(waits)
        return {'timestamp':t.isoformat(),'horizon_hours':req.horizon_hours,'strategy':req.strategy,
            'configuration':{'active_berths':len(active),'total_unblocked_berth_clusters':len(usable),'selected_active_berth_ids':[b['berth_id'] for b in active],
                'blocked_berth_ids':sorted(blocked),'traffic_multiplier':req.traffic_multiplier},
            'baseline':{'historical_calls':len(base),'modeled_queue_wait_hours':bs,'mean_verified_queue_wait_hours':None,
                'queue_wait_note':'Modeled baseline using original historical calls and all unblocked berth clusters; source does not contain verified queue-entry/berth-entry timestamp pairs.'},
            'scenario':{'demand_events':len(demand),'historical_events':len(base),'counterfactual_demand_copies':extra_n,'modeled_queue_wait_hours':ss,
                'mean_modeled_queue_wait_hours':ss['mean'],'max_modeled_queue_wait_hours':ss['max'],'berths_used':len({x['berth_id'] for x in assignments})},
            'comparison':{'mean_wait_change_hours':round(ss['mean']-bs['mean'],3) if ss['mean'] is not None and bs['mean'] is not None else None,
                'max_wait_change_hours':round(ss['max']-bs['max'],3) if ss['max'] is not None and bs['max'] is not None else None,
                'comparison_type':'modeled_schedule_comparison_not_observed_queue_wait'},
            'items':assignments,'notes':['Counterfactual copies reuse observed historical call templates; they are not new observed AIS events.',
                'Waiting values are modeled scheduling delays, not measured historical anchorage waiting.',
                'Active berth clusters are selected by historical call frequency; blocked berth IDs are excluded.',
                'Berth clusters are capacity proxies; verified berth length, draft and vessel compatibility constraints are unavailable.']}
    finally:c.close()

@app.get('/api/v1/routes/illustrative')
def illustrative_route(from_lon:float,from_lat:float,to_berth_id:str,points:int=Query(40,ge=8,le=200),speed_knots:float=Query(8,gt=0,le=25)):
    """Visual-only smooth path; not a navigational route or AIS prediction."""
    c=db()
    try:
        b=c.execute('SELECT * FROM berths WHERE berth_id=?',(to_berth_id,)).fetchone()
        if not b:raise HTTPException(404,'Unknown berth cluster')
        x0,y0=from_lon,from_lat;x3,y3=b['centroid_lon'],b['centroid_lat']
        dx=x3-x0;dy=y3-y0;length=math.hypot(dx,dy) or 1
        # Curved cubic Bezier with modest perpendicular offset for visual distinction.
        off=min(length*0.12,0.012);px=-dy/length*off;py=dx/length*off
        x1,y1=x0+dx*.33+px,y0+dy*.33+py;x2,y2=x0+dx*.72+px,y0+dy*.72+py
        coords=[]
        for i in range(points):
            u=i/(points-1);v=1-u
            x=v**3*x0+3*v*v*u*x1+3*v*u*u*x2+u**3*x3
            y=v**3*y0+3*v*v*u*y1+3*v*u*u*y2+u**3*y3
            # Ease-in/ease-out speed profile: slow at departure and berth approach.
            speed=speed_knots*(0.35+0.65*math.sin(math.pi*u)**0.65)
            coords.append({'lon':x,'lat':y,'progress':round(u,4),'speed_knots':round(speed,2)})
        return {'berth_id':to_berth_id,'berth_code':b['berth_code'],'type':'illustrative_counterfactual_animation_path','is_real_ais':False,'is_navigation_safe':False,'coordinates':coords,'warning':'Generated for visualization only. Not a real AIS track or safe navigational route.'}
    finally:c.close()
