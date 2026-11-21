PORTOS V3 — STANDALONE CESIUM + HISTORICAL AIS + WHAT-IF

The Digital Shadow navigation opens public/twin3d.html as a standalone Cesium viewer. The React dashboard remains the command centre; its embedded Cesium preview is not the V3 Digital Shadow page.

The viewer supports actual AIS track playback, selectable vessel sample size (80 / 200 / all available MMSIs), individual AIS vessel inspection, separate AIS and density layers, historical port-call context, scenario allocation, six experiment presets, synthetic capacity expansion assumptions, and modeled performance metrics.

AIS tracks are returned by MMSI and split by track_segment. The viewer never joins distinct track segments. The source timezone is unspecified; timestamps are preserved and mapped onto Cesium's UTC clock for display only.

The six scenario presets are parameter configurations, not validated real-world forecasts. Synthetic capacity units reuse representative existing cluster centroids. The allocation method is a deterministic greedy heuristic, not a global optimizer.

Run backend and frontend using START_HERE.txt.
