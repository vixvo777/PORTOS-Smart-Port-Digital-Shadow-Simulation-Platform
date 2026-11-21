PORTOS CESIUM RESTORE PATCH

Use this if you already extracted smartport_phase2_complete_frontend v2.

1. Stop Vite in the frontend terminal: Ctrl+C.
2. Extract this ZIP directly into your existing smartport_phase2_complete_frontend folder.
3. Allow App.tsx to be replaced. The ZIP adds public/twin3d.html.
4. Re-run: npm run dev
5. Open http://localhost:5173 and click Digital Shadow.

No backend/database changes and no npm reinstall are required. CesiumJS is loaded from its CDN by twin3d.html, so the browser needs internet access to cesium.com and tile.openstreetmap.org.

To restore the prior dashboard-only app, restore your backup of src/App.tsx.
