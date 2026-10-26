"""Register DLL search paths for bundled Rasterio/GDAL on Windows."""
import os
import sys
from pathlib import Path

_DLL_HANDLES = []
if sys.platform == "win32":
    root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    for base in (root, root / "_internal"):
        for name in ("rasterio.libs", "numpy.libs", "shapely.libs", "pyproj.libs", "rasterio", "pyproj"):
            folder = base / name
            if folder.is_dir():
                _DLL_HANDLES.append(os.add_dll_directory(str(folder)))
