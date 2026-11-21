import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)
def test_health():
    r=client.get('/api/v1/health'); assert r.status_code==200 and r.json()['integrity']=='ok' and r.json()['ais']['available'] is True
def test_overview():
    j=client.get('/api/v1/overview').json(); assert j['calls']==183637 and j['berth_clusters']==99
def test_geojson():
    assert len(client.get('/api/v1/map/berths').json()['features'])==99
def test_scenario():
    r=client.post('/api/v1/scenarios/allocate',json={'timestamp':'2019-06-15T08:00:00','horizon_hours':24,'active_berths':60,'traffic_multiplier':1.5,'strategy':'optimized'})
    assert r.status_code==200
    j=r.json(); assert j['scenario']['counterfactual_demand_copies']>0
    assert any(x['counterfactual_copy'] for x in j['items'])
def test_illustrative_route():
    r=client.get('/api/v1/routes/illustrative?from_lon=-90.07&from_lat=29.95&to_berth_id=1590')
    assert r.status_code==200 and len(r.json()['coordinates'])==40


def test_ais_coverage():
    j=client.get('/api/v1/ais/coverage').json()
    assert j['available'] is True and j['records']==651044 and j['vessels']==477
    assert 'timezone' in j['timestamp_semantics'].lower()

def test_scenario_metrics_and_strategy_comparison():
    r=client.post('/api/v1/scenarios/allocate',json={'timestamp':'2019-06-15T08:00:00','horizon_hours':24,
        'active_berths':12,'traffic_multiplier':1.5,'strategy':'optimized','expansion_berths':2})
    assert r.status_code==200
    j=r.json(); m=j['scenario']['metrics']
    assert m['vessels_demanded']==j['scenario']['demand_events']
    assert m['vessels_served']+m['unserved_vessels']==m['vessels_demanded']
    assert 'berth_utilization_pct' in m and 'throughput_vessels_per_hour' in m
    assert j['configuration']['synthetic_expansion_berths']==2
    assert len(j['configuration']['synthetic_berths'])==2
    assert all(x['synthetic_capacity'] for x in j['configuration']['synthetic_berths'])
    assert set(j['strategy_comparison'])=={'historical_fifo','optimized'}

def test_scenario_rejects_unknown_blocked_berth():
    r=client.post('/api/v1/scenarios/allocate',json={'timestamp':'2019-06-15T08:00:00','blocked_berth_ids':['NOT-A-BERTH']})
    assert r.status_code==422

def test_ais_analytics_endpoints():
    assert client.get('/api/v1/analytics/ais/quality').json()['available'] is True
    assert client.get('/api/v1/analytics/ais/speed').json()['count']>0
    assert len(client.get('/api/v1/analytics/ais/density?limit=5').json()['items'])>0


def test_ais_vessel_index():
    j=client.get('/api/v1/ais/vessels?start=2019-06-15T00:00:00&end=2019-06-17T00:00:00&limit=477').json()
    assert j['total_returned']==477
    assert all(x['track_segments']>=1 for x in j['items'])


def test_low_speed_episode_classification_is_cautious():
    j=client.get('/api/v1/analytics/ais/low-speed-episodes?start=2019-06-15T00:00:00&end=2019-06-16T00:00:00&limit=5').json()
    assert j['classification']=='candidate_low_speed_or_stationary_episodes'
    assert 'not be called verified anchorage' in j['note']


def test_berth_closure_reduces_nominal_active_capacity():
    ranked=client.get('/api/v1/berths').json()
    blocked_id=ranked[0]['berth_id']
    r=client.post('/api/v1/scenarios/allocate',json={'timestamp':'2019-06-15T08:00:00','horizon_hours':24,
        'active_berths':6,'traffic_multiplier':1.0,'strategy':'optimized','blocked_berth_ids':[blocked_id]})
    assert r.status_code==200
    j=r.json()
    assert j['configuration']['selected_existing_berths']==5
    assert blocked_id not in j['configuration']['selected_active_berth_ids']


def test_individual_ais_track_returns_segment_ids():
    vessels=client.get('/api/v1/ais/vessels?start=2019-06-15T00:00:00&end=2019-06-17T00:00:00&limit=1').json()['items']
    mmsi=vessels[0]['mmsi']
    r=client.get(f'/api/v1/ais/track/{mmsi}?start=2019-06-15T00:00:00&end=2019-06-17T00:00:00')
    assert r.status_code==200 and r.json()['count']>1
    assert all('track_segment' in x for x in r.json()['items'])



def test_phase3_scenario_presets_and_like_for_like_baseline():
    ranked=client.get('/api/v1/berths').json()
    blocked=[ranked[0]['berth_id'],ranked[1]['berth_id']]
    cases=[
        ('baseline',{'active_berths':99,'traffic_multiplier':1.0,'blocked_berth_ids':[],'expansion_berths':0}),
        ('surge',{'active_berths':6,'traffic_multiplier':2.0,'blocked_berth_ids':[],'expansion_berths':0}),
        ('closure',{'active_berths':6,'traffic_multiplier':1.0,'blocked_berth_ids':[ranked[0]['berth_id']],'expansion_berths':0}),
        ('combined',{'active_berths':6,'traffic_multiplier':2.0,'blocked_berth_ids':blocked,'expansion_berths':0}),
        ('expansion',{'active_berths':6,'traffic_multiplier':1.0,'blocked_berth_ids':[],'expansion_berths':5}),
        ('comparison',{'active_berths':6,'traffic_multiplier':1.5,'blocked_berth_ids':[],'expansion_berths':0}),
    ]
    for name,params in cases:
        payload={'timestamp':'2019-06-15T08:00:00','horizon_hours':24,'strategy':'optimized',**params}
        r=client.post('/api/v1/scenarios/allocate',json=payload)
        assert r.status_code==200, (name,r.text)
        j=r.json()
        assert j['configuration']['baseline_active_berths']==params['active_berths']
        assert j['scenario']['metrics']['vessels_demanded']==j['scenario']['metrics']['vessels_served']+j['scenario']['metrics']['unserved_vessels']
        assert j['scenario']['metrics']['berth_utilization_by_berth']
        assert set(j['strategy_comparison'])=={'historical_fifo','optimized'}
        assert j['comparison']['comparison_type'].endswith('same_nominal_capacity')
        if name=='surge':
            assert j['scenario']['counterfactual_demand_copies']>0
        if name=='closure':
            assert j['configuration']['selected_existing_berths']==5
        if name=='expansion':
            assert j['configuration']['synthetic_expansion_berths']==5
        if name=='combined':
            assert len(j['configuration']['blocked_berth_ids'])==2


def test_phase3_rejects_all_nominal_capacity_closed_without_expansion():
    ranked=client.get('/api/v1/berths').json()
    blocked=[x['berth_id'] for x in ranked[:6]]
    r=client.post('/api/v1/scenarios/allocate',json={'timestamp':'2019-06-15T08:00:00',
        'horizon_hours':24,'active_berths':6,'blocked_berth_ids':blocked})
    assert r.status_code==422
