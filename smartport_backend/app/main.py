from __future__ import annotations
import json, math, os, sqlite3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parents[1]
DB_PATH=Path(os.getenv('SMARTPORT_DB', ROOT/'data'/'processed'/'smartport.sqlite3'))
app=FastAPI(title='Smart Port Digital Shadow API',version='1.0.0',description='Historical-data-driven New Orleans port analytics and counterfactual berth allocation.')
from app.ais_api import router as ais_router
app.include_router(ais_router)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['*'],allow_headers=['*'])

def db():
    if not DB_PATH.exists(): raise HTTPException(503,'Database not built. Run: python processing/build_database.py')
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def parse_time(s:str)->datetime:
    try:
        value=datetime.fromisoformat(s.replace('Z','+00:00'))
        # Offset-aware API inputs are normalized to UTC; source data itself remains timezone-unspecified.
        if value.tzinfo is not None:value=value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    except Exception: raise HTTPException(422,f'Invalid datetime: {s}. Use YYYY-MM-DDTHH:MM:SS or an ISO-8601 offset.')

def rowdict(r): return dict(r) if r else None

@app.get('/')
def root(): return {'name':'Smart Port Digital Shadow API','version':'1.0.0','docs':'/docs','health':'/api/v1/health'}

@app.get('/api/v1/health')
def health():
    c=db()
    try:
        check=c.execute('PRAGMA integrity_check').fetchone()[0]
        has_ais=bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone())
        ais={'available':False,'records':0,'vessels':0}
        if has_ais:
            a=c.execute('SELECT COUNT(*) records,COUNT(DISTINCT mmsi) vessels FROM ais_positions').fetchone()
            ais={'available':True,**dict(a)}
        return {'status':'ok' if check=='ok' else 'error','database':str(DB_PATH),'integrity':check,
            'ais':ais,'port':'New Orleans','port_id':365}
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
    try:return [dict(x) for x in c.execute('''SELECT b.berth_id,b.berth_code,b.source_number,b.centroid_lon,b.centroid_lat,COUNT(c.call_id) historical_calls FROM berths b LEFT JOIN calls c ON c.berth_id=b.berth_id GROUP BY b.berth_id ORDER BY historical_calls DESC,b.berth_code''')]
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
    expansion_berths:int=Field(0,ge=0,le=20)


def _schedule(demand, berths, strategy, timestamp, horizon_end):
    'Deterministic list scheduling. This is a heuristic, not a global optimizer.'
    free_at={b['berth_id']:timestamp for b in berths}
    assignments=[]; waits=[]; unserved=[]
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
        if finish>horizon_end:
            waits.append(max(0.0,(horizon_end-arrival).total_seconds()/3600))
            unserved.append({'demand_id':item['demand_id'],'source_call_id':item.get('call_id'),
                'mmsi':item.get('mmsi'),'counterfactual_copy':bool(item.get('scenario_copy')),
                'arrival_proxy':item['start_time'],'reason':'service_not_completed_within_horizon',
                'earliest_modeled_start':start_at.isoformat(sep=' '),'earliest_modeled_end':finish.isoformat(sep=' ')})
            continue
        free_at[berth['berth_id']]=finish; waits.append(wait)
        assignments.append({'demand_id':item['demand_id'],'source_call_id':item.get('call_id'),'mmsi':item.get('mmsi'),
            'counterfactual_copy':bool(item.get('scenario_copy')),'arrival_proxy':item['start_time'],
            'assigned_start':start_at.isoformat(sep=' '),'assigned_end':finish.isoformat(sep=' '),
            'berth_id':berth['berth_id'],'berth_code':berth['berth_code'],
            'berth_centroid_lon':berth.get('centroid_lon'),'berth_centroid_lat':berth.get('centroid_lat'),
            'synthetic_capacity':bool(berth.get('synthetic_capacity',False)),
            'modeled_wait_hours':round(wait,3),'historical_observed_berth_id':item.get('berth_id')})
    return assignments,waits,unserved


def _scenario_metrics(assignments, waits, unserved, berths, start, end):
    'Compute scenario metrics over a fixed horizon; all time values are modeled.'
    horizon_s=max(1.0,(end-start).total_seconds()); horizon_h=horizon_s/3600
    ordered=sorted(waits); n=len(ordered)
    def percentile(p):
        if not ordered:return None
        return round(ordered[min(n-1,max(0,int(math.ceil(p*n)-1)))],3)
    # Sweep queue intervals [arrival, assigned start); unserved remain queued until horizon end.
    events=[]
    for a in assignments:
        arrival=datetime.fromisoformat(a['arrival_proxy']); begin=datetime.fromisoformat(a['assigned_start'])
        if begin>arrival: events.extend([(arrival,1),(begin,-1)])
    for u in unserved:
        arrival=datetime.fromisoformat(u['arrival_proxy'])
        if end>arrival: events.extend([(arrival,1),(end,-1)])
    events.sort(key=lambda x:(x[0],x[1]))
    q=peak=0
    for _,delta in events:
        q+=delta; peak=max(peak,q)
    by_berth=[]
    total_busy=0.0
    for b in berths:
        busy=0.0; count=0
        for a in assignments:
            if a['berth_id']!=b['berth_id']:continue
            x=max(start,datetime.fromisoformat(a['assigned_start']))
            y=min(end,datetime.fromisoformat(a['assigned_end']))
            if y>x: busy+=(y-x).total_seconds(); count+=1
        total_busy+=busy
        by_berth.append({'berth_id':b['berth_id'],'berth_code':b['berth_code'],
            'synthetic_capacity':bool(b.get('synthetic_capacity',False)),
            'assigned_vessels':count,'busy_hours':round(busy/3600,3),
            'utilization_pct':round(100*busy/horizon_s,2)})
    completed=[datetime.fromisoformat(a['assigned_end']) for a in assignments]
    completion=max(completed).isoformat(sep=' ') if completed else None
    return {
        'vessels_demanded':len(assignments)+len(unserved),'vessels_served':len(assignments),
        'unserved_vessels':len(unserved),'berth_assignments':len(assignments),
        'berths_used':len({a['berth_id'] for a in assignments}),
        'reassigned_vessels':sum(1 for a in assignments if a.get('historical_observed_berth_id') and a['berth_id']!=a['historical_observed_berth_id']),
        'berth_utilization_pct':round(100*total_busy/(horizon_s*max(1,len(berths))),2),
        'berth_utilization_by_berth':by_berth,
        'modeled_queue_peak':peak,'modeled_queue_mean':round(sum(waits)/len(waits),3) if waits else None,
        'average_scheduling_delay_hours':round(sum(waits)/len(waits),3) if waits else None,
        'median_scheduling_delay_hours':percentile(.5),'p90_scheduling_delay_hours':percentile(.9),
        'maximum_scheduling_delay_hours':round(max(waits),3) if waits else None,
        'throughput_vessels_per_hour':round(len(assignments)/horizon_h,4),
        'completion_time':completion,
        'completion_elapsed_hours':round((max(completed)-start).total_seconds()/3600,3) if completed else None,
        'horizon_hours':round(horizon_h,3),
        'metric_note':'All queue, delay, utilization, throughput and completion metrics are modeled scenario outputs.'
    }


def _make_demand(base, multiplier, horizon_start, horizon_hours):
    demand=list(base); extra_n=int(round(len(base)*(multiplier-1)))
    for i in range(extra_n):
        src=base[i % len(base)]
        offset=(i+1)*(horizon_hours*3600)/(extra_n+1)
        st=horizon_start+timedelta(seconds=offset)
        demand.append({**src,'start_time':st.isoformat(sep=' '),
            'end_time':(st+timedelta(seconds=max(60,float(src['duration_s'])))).isoformat(sep=' '),
            'scenario_copy':True,'demand_id':f"CF-{i+1:05d}-{src['call_id']}"})
    return demand,extra_n


def _run_policy(demand, berths, strategy, start, end):
    assignments,waits,unserved=_schedule(demand,berths,strategy,start,end)
    return {'assignments':assignments,'waits':waits,'unserved_items':unserved,
            'metrics':_scenario_metrics(assignments,waits,unserved,berths,start,end)}


@app.post('/api/v1/scenarios/allocate')
def allocate(req:ScenarioRequest):
    'Run a counterfactual berth schedule; outputs are modeled, not observed queue data.'
    t=parse_time(req.timestamp); horizon_end=t+timedelta(hours=req.horizon_hours)
    c=db()
    try:
        allb=[dict(r) for r in c.execute('SELECT berth_id,berth_code,centroid_lon,centroid_lat FROM berths').fetchall()]
        if not allb: raise HTTPException(503,'No berth clusters loaded')
        known={b['berth_id'] for b in allb}; blocked=set(req.blocked_berth_ids)
        unknown=sorted(blocked-known)
        if unknown: raise HTTPException(422,f'Unknown blocked berth IDs: {unknown[:10]}')
        usable=[b for b in allb if b['berth_id'] not in blocked]
        if not usable: raise HTTPException(422,'Scenario has no available berth clusters')
        hist=c.execute('SELECT call_id,mmsi,start_time,end_time,duration_s,latitude,longitude,berth_id FROM calls WHERE start_time>=? AND start_time<? ORDER BY start_time',
            (t.isoformat(sep=' '),horizon_end.isoformat(sep=' '))).fetchall()
        base=[{**dict(x),'scenario_copy':False,'demand_id':str(x['call_id'])} for x in hist]
        if not base:
            return {'timestamp':t.isoformat(),'horizon_hours':req.horizon_hours,'strategy':req.strategy,
                'baseline':{'historical_calls':0,'modeled_queue_wait_hours':None,'metrics':None},
                'scenario':{'demand_events':0,'historical_events':0,'counterfactual_demand_copies':0,'metrics':None},
                'comparison':{'comparison_type':'no_demand_in_selected_window'},'items':[],'unserved_items':[],
                'notes':['No historical calls start in this time window. Choose another source-data timestamp.']}
        usage={r['berth_id']:r['n'] for r in c.execute('SELECT berth_id,COUNT(*) n FROM calls WHERE berth_id IS NOT NULL GROUP BY berth_id')}
        # Choose the nominal active set first, then apply closures. A closure therefore removes
        # capacity instead of silently backfilling it with another cluster.
        selected_pool=sorted(allb,key=lambda b:(-usage.get(b['berth_id'],0),b['berth_code']))[:req.active_berths]
        selected=[b for b in selected_pool if b['berth_id'] not in blocked]
        if not selected and req.expansion_berths==0:
            raise HTTPException(422,'All nominally active berth clusters are blocked; increase active capacity or add hypothetical expansion.')
        # Hypothetical capacity units are explicitly synthetic copies of representative cluster locations.
        expansion=[]
        expansion_refs=selected or usable[:1]
        for i in range(req.expansion_berths):
            ref=expansion_refs[i % len(expansion_refs)]
            expansion.append({**ref,'berth_id':f'SYNTH-{i+1:03d}','berth_code':f'SYNTH-{i+1:03d}',
                'synthetic_capacity':True})
        active=selected+expansion
        demand,extra_n=_make_demand(base,req.traffic_multiplier,t,req.horizon_hours)
        # Reference baseline: original demand, all unblocked existing clusters, selected policy.
        baseline_run=_run_policy(base,selected_pool,req.strategy,t,horizon_end)
        scenario_run=_run_policy(demand,active,req.strategy,t,horizon_end)
        # Strategy comparison holds demand, active capacity and horizon constant.
        policy_runs={}
        for policy in ('historical_fifo','optimized'):
            r=_run_policy(demand,active,policy,t,horizon_end)
            policy_runs[policy]={'metrics':r['metrics']}
        bs=baseline_run['metrics']; ss=scenario_run['metrics']
        return {'timestamp':t.isoformat(),'horizon_hours':req.horizon_hours,'strategy':req.strategy,
            'configuration':{'active_berths':len(active),'selected_existing_berths':len(selected),
                'synthetic_expansion_berths':len(expansion),'total_unblocked_existing_clusters':len(usable),'baseline_active_berths':len(selected_pool),
                'selected_active_berth_ids':[b['berth_id'] for b in active],
                'synthetic_berths':[{'berth_id':b['berth_id'],'berth_code':b['berth_code'],'centroid_lon':b['centroid_lon'],'centroid_lat':b['centroid_lat'],'synthetic_capacity':True} for b in expansion],
                'blocked_berth_ids':sorted(blocked),'traffic_multiplier':req.traffic_multiplier,
                'expansion_assumption':'Synthetic capacity units reuse representative existing cluster centroids; not verified new infrastructure.'},
            'baseline':{'historical_calls':len(base),'modeled_queue_wait_hours':{
                'mean':bs['average_scheduling_delay_hours'],'median':bs['median_scheduling_delay_hours'],
                'p90':bs['p90_scheduling_delay_hours'],'max':bs['maximum_scheduling_delay_hours']},
                'mean_verified_queue_wait_hours':None,'metrics':bs,
                'queue_wait_note':'Baseline uses original historical demand and the same nominal active berth count as the scenario, before closures, traffic surge or expansion.'},
            'scenario':{'demand_events':len(demand),'historical_events':len(base),
                'counterfactual_demand_copies':extra_n,'modeled_queue_wait_hours':{
                    'mean':ss['average_scheduling_delay_hours'],'median':ss['median_scheduling_delay_hours'],
                    'p90':ss['p90_scheduling_delay_hours'],'max':ss['maximum_scheduling_delay_hours']},
                'mean_modeled_queue_wait_hours':ss['average_scheduling_delay_hours'],
                'max_modeled_queue_wait_hours':ss['maximum_scheduling_delay_hours'],
                'berths_used':ss['berths_used'],'metrics':ss},
            'comparison':{'mean_wait_change_hours':round(ss['average_scheduling_delay_hours']-bs['average_scheduling_delay_hours'],3)
                if ss['average_scheduling_delay_hours'] is not None and bs['average_scheduling_delay_hours'] is not None else None,
                'max_wait_change_hours':round(ss['maximum_scheduling_delay_hours']-bs['maximum_scheduling_delay_hours'],3)
                if ss['maximum_scheduling_delay_hours'] is not None and bs['maximum_scheduling_delay_hours'] is not None else None,
                'comparison_type':'modeled_schedule_comparison_not_observed_queue_wait_same_nominal_capacity'},
            'strategy_comparison':policy_runs,
            'items':scenario_run['assignments'],'unserved_items':scenario_run['unserved_items'],
            'notes':['Counterfactual copies reuse observed historical call templates; they are not new observed AIS events.',
                'All scheduling delay and queue metrics are modeled, not measured historical anchorage waiting.',
                'Existing berth clusters are spatial proxies, not verified operational berths.',
                'Synthetic expansion units are hypothetical capacity assumptions, not observed infrastructure.',
                'The optimized policy is a deterministic greedy earliest-completion heuristic, not a globally optimal solver.',
                'Strategy comparison uses identical demand, active capacity and horizon for both policies.',
                'Baseline-versus-scenario comparison holds nominal active berth count constant; closures, expansion and traffic changes are isolated in the scenario.']}
    finally:c.close()


@app.get('/api/v1/analytics/ais/quality')
def ais_quality():
    'Return reproducible coverage and basic AIS validity counts.'
    c=db()
    try:
        exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone()
        if not exists:return {'available':False,'message':'Import AIS with python processing/import_ais.py'}
        r=c.execute('''SELECT COUNT(*) records,COUNT(DISTINCT mmsi) vessels,
            COUNT(DISTINCT mmsi || ':' || track_segment) track_segments,
            MIN(timestamp) start_time,MAX(timestamp) end_time,
            SUM(CASE WHEN longitude NOT BETWEEN -180 AND 180 OR latitude NOT BETWEEN -90 AND 90 THEN 1 ELSE 0 END) invalid_coordinates,
            SUM(CASE WHEN sog<0 OR sog>60 THEN 1 ELSE 0 END) unusual_speed_records
            FROM ais_positions''').fetchone()
        return {'available':True,**dict(r),'timestamp_semantics':'Source timezone is unspecified. Timestamps are preserved as supplied; the browser maps naive source times onto a UTC Cesium clock for playback only.'}
    finally:c.close()


@app.get('/api/v1/analytics/ais/speed')
def ais_speed(start:Optional[str]=None,end:Optional[str]=None):
    c=db()
    try:
        exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone()
        if not exists:raise HTTPException(503,'AIS positions are not imported.')
        sql='SELECT sog FROM ais_positions WHERE sog IS NOT NULL AND sog>=0 AND sog<=60';args=[]
        if start:sql+=' AND timestamp>=?';args.append(parse_time(start).isoformat(sep=' '))
        if end:sql+=' AND timestamp<?';args.append(parse_time(end).isoformat(sep=' '))
        vals=sorted(float(r[0]) for r in c.execute(sql,args))
        if not vals:return {'count':0,'metric':'observed_AIS_speed_knots'}
        def pct(p):return round(vals[min(len(vals)-1,int(math.ceil(p*len(vals))-1))],2)
        return {'count':len(vals),'mean_knots':round(sum(vals)/len(vals),2),'median_knots':pct(.5),
            'p90_knots':pct(.9),'max_knots':round(vals[-1],2),'metric':'observed_AIS_speed_knots',
            'note':'Speed over ground from observed AIS records; not a forecast.'}
    finally:c.close()


@app.get('/api/v1/analytics/ais/density')
def ais_density(start:Optional[str]=None,end:Optional[str]=None,cell_degrees:float=Query(0.01,gt=0.001,le=0.1),limit:int=Query(500,ge=1,le=5000)):
    c=db()
    try:
        exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone()
        if not exists:raise HTTPException(503,'AIS positions are not imported.')
        sql='SELECT AVG(longitude) longitude,AVG(latitude) latitude,COUNT(*) n FROM ais_positions WHERE 1=1';args=[]
        if start:sql+=' AND timestamp>=?';args.append(parse_time(start).isoformat(sep=' '))
        if end:sql+=' AND timestamp<?';args.append(parse_time(end).isoformat(sep=' '))
        sql+=f' GROUP BY CAST(longitude/{cell_degrees} AS INTEGER),CAST(latitude/{cell_degrees} AS INTEGER) ORDER BY n DESC LIMIT ?';args.append(limit)
        rows=c.execute(sql,args).fetchall()
        return {'cell_degrees':cell_degrees,'items':[{'longitude':r['longitude'],'latitude':r['latitude'],'observations':r['n']} for r in rows],
            'metric':'observed_AIS_position_density','note':'Counts of recorded AIS observations per approximate degree grid cell; not unique vessel counts.'}
    finally:c.close()


@app.get('/api/v1/analytics/ais/low-speed-episodes')
def ais_low_speed_episodes(start:Optional[str]=None,end:Optional[str]=None,threshold_knots:float=Query(0.5,ge=0,le=3),minimum_minutes:int=Query(30,ge=5,le=1440),limit:int=Query(500,ge=1,le=5000)):
    'Identify candidate stationary/low-speed episodes; not authoritative anchorage classification.'
    c=db()
    try:
        exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ais_positions'").fetchone()
        if not exists:raise HTTPException(503,'AIS positions are not imported.')
        sql='SELECT mmsi,timestamp,longitude,latitude,sog,track_segment,vessel_name FROM ais_positions WHERE 1=1';args=[]
        if start:sql+=' AND timestamp>=?';args.append(parse_time(start).isoformat(sep=' '))
        if end:sql+=' AND timestamp<?';args.append(parse_time(end).isoformat(sep=' '))
        sql+=' ORDER BY mmsi,track_segment,timestamp'
        rows=c.execute(sql,args); episodes=[]; current=[]
        def flush(group):
            if len(group)<2:return
            a=datetime.fromisoformat(group[0]['timestamp']);b=datetime.fromisoformat(group[-1]['timestamp'])
            mins=(b-a).total_seconds()/60
            if mins>=minimum_minutes:
                episodes.append({'mmsi':group[0]['mmsi'],'vessel_name':group[0]['vessel_name'],
                    'track_segment':group[0]['track_segment'],'start_time':group[0]['timestamp'],'end_time':group[-1]['timestamp'],
                    'duration_minutes':round(mins,1),'mean_sog_knots':round(sum(float(x['sog']) for x in group)/len(group),2),
                    'centroid_lon':round(sum(float(x['longitude']) for x in group)/len(group),6),
                    'centroid_lat':round(sum(float(x['latitude']) for x in group)/len(group),6)})
        last_key=None;last_time=None
        for r in rows:
            key=(r['mmsi'],r['track_segment']);ts=datetime.fromisoformat(r['timestamp'])
            if r['sog'] is None or float(r['sog'])>threshold_knots:
                flush(current);current=[];last_key=None;last_time=None
                continue
            if current and (key!=last_key or (ts-last_time).total_seconds()>300):
                flush(current);current=[]
            current.append(r);last_key=key;last_time=ts
        flush(current)
        episodes.sort(key=lambda x:x['duration_minutes'],reverse=True)
        return {'threshold_knots':threshold_knots,'minimum_minutes':minimum_minutes,'count':len(episodes),
            'items':episodes[:limit],'classification':'candidate_low_speed_or_stationary_episodes',
            'note':'These are AIS-derived low-speed episodes only. Without authoritative anchorage polygons or navigational context they must not be called verified anchorage events.'}
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
