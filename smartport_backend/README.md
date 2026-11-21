# Smart Port Digital Shadow — New Orleans Backend

A historical-data-driven backend for the 2019 New Orleans port-call dataset (port ID 365). This package includes source data, a reproducible ETL pipeline, SQLite database generation, validation, analytics APIs, a counterfactual berth allocation engine, and a visual-only curved vessel path endpoint.

## Requirements
- Python 3.10+
- Windows: run `run_windows.bat`
- macOS/Linux: run `./run_linux_mac.sh`

The launcher creates a virtual environment, installs dependencies, builds and validates the SQLite database, preserves a previously imported AIS table during a rebuild, imports AIS if missing, then starts FastAPI at `http://127.0.0.1:8000`. API docs: `http://127.0.0.1:8000/docs`.

## Manual setup
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python processing/build_database.py
python processing/validate_database.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Main endpoints
- `GET /api/v1/health` — database integrity
- `GET /api/v1/overview` — port and historical call summary
- `GET /api/v1/map/port` — port geometry GeoJSON
- `GET /api/v1/map/berths` — 99 berth-cluster polygons
- `GET /api/v1/berths` — berth cluster metadata
- `GET /api/v1/calls?start=2019-01-01T00:00:00&end=2019-02-01T00:00:00&limit=500` — paginated historical calls
- `GET /api/v1/vessels/{mmsi}` — vessel call history
- `GET /api/v1/analytics/dwell` — recorded port-call duration statistics (not queue wait)
- `GET /api/v1/analytics/berths` — point-in-polygon berth-cluster match counts
- `GET /api/v1/analytics/timeline?granularity=month` — monthly calls and recorded duration
- `GET /api/v1/analytics/ais/quality` — AIS coverage and basic quality counts
- `GET /api/v1/analytics/ais/speed` — observed speed-over-ground distribution
- `GET /api/v1/analytics/ais/density` — approximate spatial observation-density grid
- `GET /api/v1/analytics/ais/low-speed-episodes` — candidate low-speed episodes (not verified anchorage)
- `POST /api/v1/scenarios/allocate` — counterfactual allocation from a selected historical time
- `GET /api/v1/routes/illustrative?...` — curved visual animation path to a berth cluster

### Scenario request example
```json
{
  "timestamp": "2019-06-15T08:00:00",
  "horizon_hours": 24,
  "active_berths": 60,
  "traffic_multiplier": 1.5,
  "strategy": "optimized",
  "blocked_berth_ids": [],
  "expansion_berths": 0
}
```
`traffic_multiplier > 1` adds counterfactual demand copies based on observed historical call templates. They are explicitly marked `counterfactual_copy: true`; they are not claimed to be newly observed vessels. `strategy` accepts `optimized` or `historical_fifo`. The response includes a like-for-like comparison of both strategies under identical demand and capacity, per-berth utilization, modeled queue peak, served/unserved demand, throughput, completion time and modeled delay statistics. `expansion_berths` adds explicitly synthetic capacity units at representative existing cluster centroids; it does not assert that new physical berths exist.

## Data interpretation — important
- `portcalls_new_orleans.csv` has observed stopping-event intervals (`ts_start`, `ts_end`) and a representative position. `duration_s` is recorded port-call/stopping duration, **not verified anchorage waiting time**.
- `berths_new_orleans.geojson` contains 99 observed berth-cluster polygons. They are not 99 independently verified engineered berths. The source does not provide complete berth length, draft, or vessel compatibility attributes.
- `trajectories_target_vessels.csv` contains semantic port-to-port events, not continuous intraport AIS positions.
- The allocation engine chooses the nominal active cluster set by historical call frequency and then applies blocked-cluster closures, so a closure inside the selected set reduces capacity rather than being backfilled. It treats remaining clusters as interchangeable capacity units because verified compatibility is unavailable. Its `modeled_wait_hours` is a counterfactual scheduling result, not observed queue waiting.
- The illustrative route endpoint generates a smooth curved path for visual animation. It is not a safe navigational route, a trained AIS forecast, or an observed track.
- Timestamps are retained as provided; source timezone semantics are not asserted. The standalone viewer maps naive source timestamps onto Cesium’s UTC clock as a display convention only; it does not establish the source timezone.

## Data processing
The AIS importer stages the complete CSV.GZ import and swaps it into the database transactionally; a failed import does not delete the previously imported AIS table.
`processing/build_database.py` reads pipe-delimited tables, filters valid port-call intervals (duration > 0 and < 30 days), assigns coordinate-bearing calls to berth-cluster polygons with Shapely, imports vessel type and semantic trajectory records, and writes a temporary validated SQLite database before atomically replacing `data/processed/smartport.sqlite3`. If the previous database has `ais_positions`, the AIS table and indexes are copied into the replacement. Stop the API before rebuilding so the database file is not held open.
`processing/validate_database.py` checks SQLite integrity, record counts, timestamps, durations and berth counts.

## Known limitations
2. Exact anchorage-to-berth waiting time cannot be measured from the supplied event timestamps.
3. Berth compatibility constraints (LOA, draft, depth, equipment) are unavailable; optimizer outputs are scenario-level estimates.
4. Route curves are visual-only. A navigable water network would be required for route safety.
5. Low-speed AIS episodes are candidates only; anchorage polygons and operational context are required for verified anchorage classification.
6. Synthetic capacity expansion units are illustrative assumptions at representative cluster centroids, not surveyed new berths.
7. The allocation heuristic is deterministic greedy scheduling and does not prove global optimality.

## Smoke tests
After installing requirements and building the database:
```bash
pip install pytest httpx
pytest -q
```
The tests check database health, expected record counts, berth GeoJSON, scenario allocation and illustrative route generation.
