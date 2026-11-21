# PORTOS test report

## Passed checks

- Backend smoke suite: **13 passed**.
- SQLite `PRAGMA integrity_check`: `ok`.
- Port-call rows: 183,637.
- Berth clusters: 99.
- AIS rows: 651,044.
- AIS MMSIs: 477.
- Database rebuild executed successfully and preserved all 651,044 AIS records.
- AIS importer executed against a temporary database copy and recreated 651,044 rows / 477 MMSIs with all three indexes.
- AIS quality, speed, density and low-speed episode APIs returned successful responses.
- Six What-If configurations were executed through the API: baseline, surge, berth closure, combined disruption, capacity expansion and strategy comparison.
- Berth closure test confirmed that blocking one of six nominally active clusters reduces existing active capacity to five instead of silently backfilling it.
- V3 inline JavaScript passed `node --check`.
- All Python backend and processing modules passed `py_compile`.
- All TypeScript/TSX source files parsed without syntax errors using the TypeScript parser.

## Not completed in this environment

- `npm ci` timed out while attempting to retrieve frontend packages. A complete Vite production build and full TypeScript type-check could not be run because dependencies were unavailable.
- Interactive Chrome testing of Cesium playback, click selection, timeline, OSM tiles and the 477-vessel mode was not possible in this environment.

## Required on the target laptop

1. Run `npm ci` in `smartport_phase2_complete_frontend`.
2. Run `npm run build` and resolve any environment-specific TypeScript/build issue if reported.
3. Run the backend using `run_windows.bat`.
4. Open the frontend and test `twin3d.html` in Chrome.
5. Test the default 80-vessel AIS mode first; use 200 or all 477 only if laptop performance is acceptable.
6. Rehearse the six What-If experiments and verify the source-time caveat is explained.

## Follow-up visual/AIS patch (20 Nov 2026)
- Added `GET /api/v1/ais/tracks/bulk` so the Cesium viewer loads selected observed AIS tracks in one indexed request instead of issuing hundreds of per-vessel requests.
- Bulk track payload is visually sampled per track segment (retains endpoints and >5-minute gap boundaries) to keep Cesium rendering responsive while preserving segment separation.
- Historical replay camera now opens on the Mississippi River terminal area (close port view) rather than the previous wide regional view.
- Verified bulk endpoint against the included database for 15–16 June 2019: 120 vessels returned, 36,517 sampled positions, max 855 points per vessel across separate segments.
- Backend smoke tests after this patch: 13 passed.


## Follow-up Cesium GeoJSON/AIS replay checks

- Confirmed source berth GeoJSON contains 99 MultiPolygon features and the port GeoJSON contains the New Orleans port boundary.
- Confirmed all 99 berth source features are represented by the backend map endpoint and matched to berth rows for labels/status.
- Removed circular berth point markers; the GeoJSON polygons themselves are the berth footprints. Floating text labels show berth code and FREE/BUSY state.
- Confirmed the packaged SQLite database contains 651,044 AIS positions from 2019-06-15 00:00:00 through 2019-06-16 23:59:59 across 477 MMSIs.
- Simulated the default bulk selection: 120 vessels, 36,517 sampled source positions, 137 source track segments, and 108 continuous drawable runs (3,120 retained positions) after respecting the five-minute gap rule.
- Changed Cesium clock to start playback automatically after the default historical day loads; AIS sampled positions use linear interpolation between observed samples.
- HTML/CSS controls were not redesigned. Browser visual playback remains to be confirmed on the user's machine; syntax and data-level checks do not replace that browser test.
