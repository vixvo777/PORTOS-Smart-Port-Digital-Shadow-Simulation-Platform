# PORTOS — Smart Port Digital Shadow
## Consolidated recovery, completion and demonstration plan

**Project location:** New Orleans, Louisiana, USA  
**Primary UI:** V3 standalone Cesium viewer (`smartport_phase2_complete_frontend/public/twin3d.html`)  
**Historical AIS source:** 15–16 June 2019  
**Backend:** FastAPI + SQLite  
**Frontend:** React + TypeScript + Vite + standalone CesiumJS

## 1. Project truth and architecture

PORTOS is a historical-data-driven digital-twin prototype with a separate counterfactual berth-scheduling experiment. It is not a live VTMS, certified route planner, navigation-safety system or operational berth optimizer.

Keep three data classes separate in code, UI, metrics and the presentation:

1. **Observed AIS:** timestamped position observations from the supplied compressed CSV. Each MMSI can have multiple `track_segment` values. Never join distinct segments and never interpolate across gaps greater than five minutes.
2. **Historical port-call and reference data:** recorded port-call intervals, representative stop coordinates, spatial berth/stopping-cluster polygons and port boundary. Port-call duration is dwell, not measured anchorage waiting. Spatial matches are not certified operational berth assignments.
3. **Counterfactual scenario data:** generated demand copies and modeled berth assignments. These are not observed AIS or new observed vessels.

The React application remains the command centre. The Digital Shadow navigation opens the V3 standalone Cesium page. The older React `CesiumPort.tsx` is a dashboard preview and must not replace V3.

## 2. Verified source-data inventory

Verified against the supplied ZIP and SQLite database:

| Dataset / table | Verified quantity | Intended use |
|---|---:|---|
| `ais_positions` | 651,044 observations | Historical vessel positions |
| AIS MMSIs | 477 | Distinct observed vessels |
| AIS track segments | 5,461 | Independent continuous track fragments |
| `calls` | 183,637 | Historical port-call/stopping events |
| Port-call MMSIs | 4,088 | Vessel population in port-call records |
| `berths` | 99 | Spatial berth/stopping-cluster proxies |
| `trajectories` | 403,158 | Semantic port-to-port events, not continuous intraport AIS |
| `area_presence` | 4,088 | Area-presence reference data |
| `vessel_types` | 2,416 | Vessel type enrichment |

AIS coverage in the database is `2019-06-15 00:00:00` through `2019-06-16 23:59:59`. The source timezone is **not specified**. Source timestamps are retained as supplied. The browser maps naive timestamps onto Cesium's UTC clock only as a display convention; this does not prove that the source timestamps are UTC.

## 3. Changes included in this completion package

### Backend

- Added `/api/v1/ais/vessels` to list distinct MMSIs, with each track request returning all track segments for one vessel.
- AIS API now honours `SMARTPORT_DB`, matching the main API and processing scripts.
- Health response includes AIS availability and record/vessel counts.
- Added AIS quality, speed-over-ground, spatial observation-density and candidate low-speed episode endpoints.
- Low-speed episodes split at high-speed observations, track-segment boundaries and gaps greater than five minutes. They are candidates only, not verified anchorage events.
- Expanded What-If metrics: served/unserved vessels, assignments, per-berth and aggregate utilization, peak modeled queue, mean/median/P90/maximum modeled scheduling delay, throughput and completion time.
- Added like-for-like strategy comparison: `historical_fifo` and `optimized` receive the same demand, horizon and active capacity.
- Added hypothetical `expansion_berths` (0–20). These are explicitly synthetic capacity units at representative existing cluster centroids, not actual new berths.
- The `optimized` policy remains a deterministic greedy earliest-completion heuristic. It is not a global optimizer.
- API timestamps with explicit offsets are normalized to UTC for comparison; naive timestamps are interpreted as source-time strings.

### Data recovery and startup

- Database rebuild writes to `smartport.building.sqlite3`, validates it, preserves an existing `ais_positions` table and its indexes when available, then atomically replaces the database. This rebuild was run successfully on the supplied project database and preserved all 651,044 AIS rows.
- AIS import uses a staging table and transactional swap so a failed import does not delete the previous AIS table. The import was also tested against a temporary database copy and reproduced 651,044 rows / 477 MMSIs.
- Windows and Linux/macOS startup scripts check for the AIS table, import the bundled AIS dataset if missing, validate the database and then start FastAPI.
- Validation now requires the supplied 651,044-row / 477-vessel AIS dataset.

### V3 standalone Cesium

- V3 remains the primary Digital Shadow page.
- AIS sample selector: 80 (default), 200 or all available MMSIs. The all-vessel option can be heavy on laptops.
- AIS entities can be selected to inspect MMSI, vessel name/type, observation count and segment time range.
- Observed AIS visibility and AIS density hotspot layers can be toggled separately.
- Renderer adds a second continuity guard: it splits a reused segment ID at gaps greater than 300 seconds.
- Added a selected-date AIS analysis panel: quality summary, observed speed distribution, density hotspots and candidate low-speed episodes.
- Added six scenario presets and a synthetic-capacity expansion control.
- What-If HUD includes modeled served/unserved, queue, utilization, throughput and policy-comparison information.
- API URL defaults to the current host on port 8000; dashboard can pass `VITE_API_BASE_URL` into the standalone page.

### React command centre

- Added synthetic capacity expansion control.
- Added served/unserved, utilization, queue and throughput metrics to scenario results.
- Added a like-for-like strategy comparison display.
- Corrected date query end to the next midnight (exclusive), avoiding omission of the final second.
- Uses current host + port 8000 as fallback API address; explicit `VITE_API_BASE_URL` is passed to V3.
- Source-time labels no longer assert an unverified UTC timezone.

## 4. What-If experiment definitions

The API request is `POST /api/v1/scenarios/allocate`.

```json
{
  "timestamp": "2019-06-15T08:00:00",
  "horizon_hours": 24,
  "active_berths": 6,
  "traffic_multiplier": 1.5,
  "strategy": "optimized",
  "blocked_berth_ids": [],
  "expansion_berths": 0
}
```

| Experiment | Configuration |
|---|---|
| 1. Baseline | 1.0× demand, all 99 existing clusters active, no blocks, no synthetic expansion |
| 2. Traffic surge | Increase `traffic_multiplier` (1.0–3.0) |
| 3. Berth closure | Add one or more existing IDs to `blocked_berth_ids` |
| 4. Combined disruption | Increase traffic and block one or more clusters |
| 5. Capacity expansion | Set `expansion_berths` (0–20); units are synthetic assumptions |
| 6. Strategy comparison | Compare `optimized` and `historical_fifo`; API returns both under identical scenario demand/capacity |

The reference baseline uses original historical demand and all unblocked existing clusters. The scenario run first chooses the nominal active set by historical call frequency, then applies closures. A closure inside that set reduces active capacity rather than being silently backfilled. It also applies the requested traffic multiplier, expansion and selected policy. Baseline-vs-scenario is therefore a counterfactual comparison; use the dedicated strategy comparison for a controlled policy comparison.

All delay, queue, utilization, throughput and completion values are modeled outputs. The source does not provide verified queue-entry and berth-entry timestamp pairs.

## 5. Metric definitions

- **Vessels demanded:** historical calls in the selected source-time horizon plus generated counterfactual copies.
- **Vessels served:** assignments whose modeled service finishes within the horizon.
- **Unserved vessels:** demand whose earliest modeled service cannot finish by the horizon end.
- **Berth utilization:** modeled service seconds within the horizon divided by available berth-seconds across all active modeled capacity units.
- **Modeled queue peak:** maximum concurrent modeled waiting intervals. Unserved demand remains queued until horizon end for this metric.
- **Scheduling delay:** modeled time from source call start-time proxy to modeled service start. For unserved demand, the reported wait contribution is capped at horizon end.
- **Throughput:** served vessel services divided by horizon hours.
- **Completion time:** latest modeled service end among served assignments.
- **Reassigned vessels:** served assignments whose assigned cluster differs from the spatially matched historical cluster.

These are scenario metrics, not calibrated port performance indicators.

## 6. AIS analytics definitions

- **Speed:** speed over ground (`sog`) from AIS observations, filtered to 0–60 knots for summary statistics.
- **Density:** count of recorded observations in approximate degree-grid cells. This is not unique-vessel density and not a calibrated kernel-density surface.
- **Candidate low-speed episode:** consecutive low-speed observations within one MMSI and one track segment, split by any higher-speed observation or gap greater than five minutes, lasting at least the selected duration. Without anchorage polygons and navigational context, it is not labelled a verified anchorage event.

## 7. Startup instructions

### Windows

Terminal 1:

```bat
cd /d PATH\TO\smartport_backend
run_windows.bat
```

Wait for Uvicorn on `http://127.0.0.1:8000`. Check:

- `http://127.0.0.1:8000/api/v1/health`
- `http://127.0.0.1:8000/api/v1/ais/coverage`
- `http://127.0.0.1:8000/docs`

Terminal 2:

```bat
cd /d PATH\TO\smartport_phase2_complete_frontend
npm ci
npm run dev
```

Open `http://localhost:5173`, then click Digital Shadow. Direct V3: `http://localhost:5173/twin3d.html`.

For a production build:

```bat
npm run build
npm run preview
```

If backend and frontend are on different hosts, create `.env.local` from `.env.example` and set `VITE_API_BASE_URL=http://YOUR_BACKEND_HOST:8000` before starting/building Vite.

Stop the backend before manually rebuilding the SQLite database. The automated rebuild is designed to preserve AIS, but the database should not be replaced while another process holds it open.

## 8. Verification completed in the packaging environment

- Backend smoke tests: **13 passed** (see `smartport_backend/tests/smoke_test.py`).
- SQLite integrity: `ok`.
- Port calls: 183,637.
- Berth clusters: 99.
- AIS positions: 651,044.
- AIS MMSIs: 477.
- AIS quality endpoint: returned coverage successfully.
- AIS speed endpoint: returned 651,005 valid SOG observations for the full dataset.
- AIS density endpoint: returned spatial bins.
- Candidate low-speed episode endpoint: returned 1,883 candidates for 15 June 2019 using 0.5 knots / 30 minutes; this is not a verified anchorage count.
- Standalone V3 inline JavaScript: Node syntax check passed.
- All six scenario configurations were exercised through the API; berth closure reduced nominal active capacity and synthetic expansion was returned with explicit centroid metadata.
- Python modules: compile checks passed.

**Not verified here:** Vite production build and interactive browser testing. `npm ci` timed out in the isolated packaging environment before dependencies could be installed. Run `npm ci` and `npm run build` on the target laptop before the professor demonstration. No claim is made that browser rendering or all 477-vessel mode has been interactively performance-tested.

## 9. Remaining known limitations

1. Original source timezone is unspecified.
2. AIS covers only 15–16 June 2019.
3. Port-call duration is dwell, not anchorage queue waiting.
4. Spatial berth/stopping clusters are proxies, not certified physical berth definitions.
5. Verified berth dimensions, draft/depth limits and vessel compatibility are absent.
6. Hypothetical capacity units are synthetic assumptions at representative centroids.
7. Greedy earliest-completion is a heuristic, not a global optimization proof.
8. Low-speed episodes are not verified anchorage events.
9. Vessel routes shown for historical port-call context or What-If animation are illustrative, not AIS-derived routes or safe navigation paths.
10. The application is a research prototype, not a certified VTMS.

## 10. Final demonstration order

1. Open PORTOS command centre and show API online.
2. Open V3 standalone Cesium.
3. Show AIS coverage and source-time caveat.
4. Load 15 June 2019 and play observed AIS.
5. Select an AIS vessel and inspect MMSI, vessel type, observations and segment time.
6. Show observed AIS density hotspots and speed analysis.
7. Show candidate low-speed episodes with the anchorage classification caveat.
8. Show historical port-call context and spatial berth-cluster geometry.
9. Run baseline What-If.
10. Run traffic surge and berth closure / combined disruption.
11. Run synthetic capacity expansion.
12. Compare greedy earliest-completion and historical FIFO under identical scenario demand and capacity.
13. Explain observed AIS vs historical port-call records vs counterfactual simulation.
14. Finish with limitations and test report.

## 11. Definition of done

- [x] V3 standalone Cesium retained as primary Digital Shadow page.
- [x] AIS data verified in supplied database.
- [x] AIS track index endpoint lists all MMSIs.
- [x] AIS continuity safeguards in renderer.
- [x] AIS quality, speed, density and low-speed candidate analytics endpoints.
- [x] What-If metric extension and controlled policy comparison.
- [x] Synthetic expansion is explicitly labelled.
- [x] Safe database rebuild/import startup workflow.
- [x] Backend smoke tests pass.
- [ ] `npm ci` and `npm run build` pass on target laptop.
- [ ] Interactive browser test on target laptop.
- [ ] Professor demonstration rehearsal.


## Latest requested correction: source GeoJSON + moving AIS

- Keep the original PORTOS Cesium UI; do not add circles or redesign the sidebar.
- Render the complete `data/source/geojson/berths_new_orleans.geojson` MultiPolygon set (99 berth footprints) and `port_new_orleans.geojson` boundary through the existing map API endpoints.
- Use text labels and polygon fill/outline state for FREE/BUSY; no circular berth pins.
- Load the default AIS date automatically and start the Cesium clock automatically. AIS ship hulls follow the sampled observed positions and velocity orientation; split at track-segment boundaries and gaps over five minutes.
- Confirm final browser playback, berth footprints, and labels after running the package locally.
