# PORTOS completion package

This ZIP contains the repaired PORTOS project in two sibling folders:

- `smartport_backend/` — FastAPI, SQLite database, historical data, AIS importer, ETL and tests.
- `smartport_phase2_complete_frontend/` — React command centre and V3 standalone Cesium Digital Shadow.
- `PLAN.md` — consolidated implementation, methodology, experiment definitions, run instructions and limitations.
- `TEST_REPORT.md` — verification evidence and remaining external checks.

## Quick start (Windows)

**Terminal 1**

```bat
cd /d PATH\TO\smartport_backend
run_windows.bat
```

**Terminal 2**

```bat
cd /d PATH\TO\smartport_phase2_complete_frontend
npm ci
npm run dev
```

Open `http://localhost:5173`, then click Digital Shadow. The V3 page is also available at `http://localhost:5173/twin3d.html`.

Read `PLAN.md` before presenting the model. In particular, the AIS source timezone is unspecified, port-call dwell is not anchorage waiting, berth clusters are spatial proxies, and all What-If queue/delay outputs are modeled.


## Cesium berth GeoJSON + automatic AIS replay update

The original `public/twin3d.html` UI is retained. The Cesium scene loads the source GeoJSON files served by `/api/v1/map/port` and `/api/v1/map/berths`. All 99 berth MultiPolygon features are rendered as the berth layer; berth status is shown with text labels and polygon color changes (no circular berth pins). The historical AIS bulk endpoint supplies observed positions for the default 15 June 2019 view. Replay starts automatically at the selected playback speed, and each vessel hull follows its timestamped AIS samples with a velocity-derived orientation. AIS gaps over five minutes and source track-segment boundaries are not connected.
