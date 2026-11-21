# New Orleans Smart Port — Dataset Audit

Audit generated from the three user-uploaded archives on 2026-11-20.

## Selection
- Port: New Orleans, United States of America
- Dataset port ID: 365
- Source coverage: 2019-01-01 to 2019-12-31

## Observed source data
- Raw port-call rows for port 365: 184,455
- Valid port-call rows (duration > 0 and < 30 days): 183,637
- Distinct MMSIs in valid calls: 4,088
- Berth geometry records: 99 (all are MultiPolygon geometries)
- Valid calls with coordinates: 140,603 (76.6%)
- Coordinate-bearing valid calls inside one of the berth polygons: 124,758 (88.7% of coordinate-bearing calls)
- Distinct MMSIs with valid calls represented in semantic trajectory table: 4,044
- Semantic trajectory rows for these MMSIs (all ports in their trajectory sequences): 403,158
- Semantic trajectory events involving New Orleans as origin or destination: 196,082
- Daily area-presence rows for target MMSIs: 4,088

## Dwell duration from recorded port-call intervals
- Mean: 6.29 hours
- Median: 1.15 hours
- P90: 15.35 hours
- P95: 25.50 hours

These are port-call/stopping durations, **not verified anchorage queue waiting times**. The source records `ts_start` and `ts_end` for port-call events, but does not directly provide a distinct anchorage-arrival and berth-entry timestamp pair.

## Important interpretation limits
1. The 99 `berths.csv` records are observed stopping-location berth clusters with polygon geometry; do not assume they are 99 independently engineered/operational berths with verified length, draft or vessel compatibility.
2. The `trajectories.csv` file is semantic port-to-port event data (`port_origin`, `port_destination`, `ts`), not continuous timestamped AIS latitude/longitude tracks. It cannot train an in-port raw AIS trajectory model by itself.
3. `areapresence.csv` is daily vessel-presence flags, not precise intraday movement.
4. `docking.csv` contains only three broad, dataset-wide geometry features (`quay`, `wharf`, `offshore`) whose extents are not New Orleans-specific. It is intentionally not treated as New Orleans berth geometry.
5. A historical-data-driven what-if engine can optimize assignments against observed calls, intervals and berth clusters. Queue waiting will be labelled derived/estimated unless supported by distinct queue/berth-entry observations.
6. For visual vessel movement in What-If mode, we can generate smooth illustrative paths from historical stopping locations and available geometry, but those paths are generated animation, not actual AIS tracks or certified navigation.

## Files in this package
- `csv/portcalls_new_orleans.csv`: all port-call rows for port 365
- `csv/berths_new_orleans.csv`: 99 berth-cluster records
- `csv/ports_new_orleans.csv`: port record and source geometry
- `csv/trajectories_target_vessels.csv`: semantic trajectory histories for MMSIs with valid New Orleans calls
- `csv/areapresence_target_vessels.csv`: daily area-presence records for those MMSIs
- vessel type tables, port traffic row and port-related route aggregates
- `geojson/berths_new_orleans.geojson`: 99 berth polygons
- `geojson/port_new_orleans.geojson`: source port geometry

## Monthly valid port calls
- 01: 17,246
- 02: 14,063
- 03: 16,762
- 04: 15,416
- 05: 15,824
- 06: 14,436
- 07: 15,165
- 08: 17,452
- 09: 13,840
- 10: 14,756
- 11: 14,515
- 12: 14,162
