# Windows portable build — test candidate

Candidate: GIS Raster prototype, 2026-10-25.
Build workflow: .github/workflows/gis-windows-beta.yml
Branch: feature/gis-raster

Compilation is expected to be performed on GitHub Actions Windows runner. This is a Windows 11 x64 test candidate, not the legacy Delphi GUI and not a signed MSI installer.

Acceptance checks:
- unit tests pass;
- PyInstaller exits successfully;
- uploaded artifact contains COTA-NET-GIS.exe;
- manual launch and Metashape GeoTIFF/MDT validation required.

IMPORTANT: successful CI packaging does not prove >4 GB BigTIFF throughput or full runtime behavior.
