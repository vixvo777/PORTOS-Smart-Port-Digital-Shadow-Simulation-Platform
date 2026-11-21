# Cesium TypeScript property fix

This update fixes Cesium 1.127 graphics typings in:
- `src/CesiumPort.tsx`
- `src/components/ais/AISVesselLayer.tsx`

Colors assigned to Cesium graphics properties now use `ConstantProperty` or
`ColorMaterialProperty` where the Cesium API expects a Property/MaterialProperty.
The scenario animation position is also initialized before conditional branches.

No backend or database files are changed.

Run from this folder:
```powershell
npm install
npm run typecheck
npm run build
```
