# PORTOS AIS + What-If implementation notes

## Primary implementation

The primary Digital Shadow is the standalone V3 page at `public/twin3d.html`. It loads the observed AIS data directly from the FastAPI endpoints, maintains separate track-segment entities, supports vessel selection, and includes the What-If controls. The React command centre opens this page through its Digital Shadow navigation.

## Supporting React modules

- `services/aisApi.ts` — typed AIS API client.
- `hooks/useHistoricalAIS.ts` — React hook for historical track retrieval.
- `utils/aisPlayback.ts` — interpolation within one segment, with a hard five-minute gap guard.
- `components/ais/AISVesselLayer.tsx` and `AISPlaybackControls.tsx` — reusable components retained for future dashboard integration; they are not the V3 standalone viewer's active rendering path.
- `CesiumPort.tsx` — embedded Cesium preview in the React dashboard, not a replacement for V3.

## Data rules

1. Each MMSI may have multiple `track_segment` values. Never join distinct segments.
2. Do not interpolate across gaps greater than 300 seconds.
3. AIS source timezone is unspecified. The UI maps naive timestamps onto Cesium's UTC clock for display only; it does not establish source timezone.
4. Historical port-call dwell is not measured anchorage queue waiting.
5. What-If scheduling delay is modeled, not observed.
6. Low-speed AIS episodes are candidates only, not verified anchorage events.

See the repository-root `PLAN.md` for the full architecture, API contracts, metric definitions and verification results.
