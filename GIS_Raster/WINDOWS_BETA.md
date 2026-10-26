# COTA NET GIS — Windows prototype build

This creates a **portable test folder**, not an MSI installer, not a signed/notarized app, and not the Delphi application. No 30-day expiry is implemented in this prototype.

## GitHub Actions
Open the repository **Actions → GIS Windows prototype build → Run workflow**, selecting `feature/gis-raster`. If workflow permissions are enabled and all steps succeed, download the artifact `COTA-NET-GIS-Windows-prototype`. Extract the **entire folder** and start `COTA-NET-GIS.exe`.

## Local build on Windows 11
From PowerShell at repository root:
```powershell
powershell -ExecutionPolicy Bypass -File .\GIS_Raster\build_windows.ps1
```
Built executable: `GIS_Raster/dist/COTA-NET-GIS/COTA-NET-GIS.exe`.

## Validation required before calling release ready
- Import real Metashape orthophoto (362 MB), large BigTIFF >4 GB, and corresponding DTM.
- Inspect real CRS and transformation to GTM EPSG:5482.
- Check map pan/zoom at multiple scales and memory use.
- Compare sampled DTM elevations at surveyed control locations with QGIS/Metashape.
- Confirm vertical datum and units of both raster and EPANET INP.
- Confirm that original INP is unchanged and generated INP opens and simulates in EPANET.
- Test Windows 11 clean computer and ensure all rasterio/GDAL dependencies are packaged.

Limitations: independent Python/Tkinter viewer; no integration yet with legacy Delphi GUI. The Windows GitHub Actions workflow creates an **unsigned prototype**, and successful compilation does not imply successful runtime validation.
