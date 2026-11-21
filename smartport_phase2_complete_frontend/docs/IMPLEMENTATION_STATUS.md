# PORTOS implementation status

Updated with the completion package. For the full file-by-file plan, API behavior, metric definitions, startup steps and limitations, see the repository-root `PLAN.md`.

## Completed in this package

- V3 standalone Cesium remains the primary Digital Shadow page.
- Historical AIS vessel index returns distinct MMSIs and all track segments per MMSI.
- AIS renderer splits segment boundaries and any gaps greater than 300 seconds.
- AIS vessel selection, AIS/density layer toggles and selected-date analytics are available.
- Added AIS quality, speed, density and candidate low-speed episode APIs.
- What-If response includes served/unserved, queue peak, berth utilization, throughput, completion time and delay statistics.
- Strategy comparison runs both supported policies on identical demand and capacity.
- Added explicit synthetic capacity expansion assumption.
- Database rebuild preserves existing AIS data; AIS import uses a staging table and transactional swap.
- Startup scripts import AIS when absent and validate the expected source coverage.
- Backend smoke tests pass.
- Full database rebuild was exercised and preserved all 651,044 AIS records.
- AIS import was exercised against a temporary database copy and recreated the full 651,044 / 477 coverage.
- Six scenario configurations were exercised through the API, including a closure that reduces active capacity.

## Validation summary

- Backend tests: 13 passed.
- SQLite integrity: `ok`.
- Port calls: 183,637.
- Berth clusters: 99.
- AIS positions: 651,044 across 477 MMSIs.
- V3 inline JavaScript syntax: passed.
- Python compile checks: passed.

## Pending external verification

The packaging environment could not complete `npm ci` (timeout), so Vite build and interactive browser testing remain to be run on the target laptop. Use `npm ci`, `npm run build`, and then test V3 in Chrome with the backend running.

## Interpretation limits

The AIS source timezone is unspecified. Port-call duration is dwell, not observed anchorage waiting. Low-speed episodes are candidates, not verified anchorage. Spatial berth clusters are proxies. Greedy earliest-completion is a deterministic heuristic, not a global optimizer. Synthetic capacity expansion is hypothetical. Route curves are illustrative and not safe navigation routes.
