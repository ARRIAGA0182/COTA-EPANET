$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path ".venv/Scripts/python.exe")) { py -3 -m venv .venv }
$python = Resolve-Path ".venv/Scripts/python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m unittest discover -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) { throw "Pruebas fallidas: compilación cancelada." }
& $python -m PyInstaller --noconfirm --clean --onedir --windowed --name "COTA-NET-GIS" --collect-all rasterio integrated_viewer.py
if ($LASTEXITCODE -ne 0) { throw "Error en PyInstaller" }
Write-Host "Compilado en GIS_Raster/dist/COTA-NET-GIS/COTA-NET-GIS.exe"
