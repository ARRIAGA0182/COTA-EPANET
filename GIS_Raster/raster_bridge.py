#!/usr/bin/env python3
"""COTA NET GIS raster bridge (prototype). Uses rasterio/GDAL; never reads entire raster.
Examples:
  python raster_bridge.py inspect orthophoto.tif
  python raster_bridge.py elevation terrain.tif --x 550000 --y 1800000 --epsg 5482
  python raster_bridge.py assign terrain.tif nodes.json --epsg 5482
  python raster_bridge.py preview orthophoto.tif output.png --width 1400
Node input: [{"id":"N1","x":550000,"y":1800000}, ...]
JSON output is meant for later integration with Delphi and EPANET.
"""
import argparse
import json
import math
import sys

def emit(obj):
    print(json.dumps(obj, ensure_ascii=False, allow_nan=False))

def check_crs(ds):
    if ds.crs is None:
        raise ValueError("Raster sin sistema de coordenadas; georreferenciar antes de usar.")

def point_to_raster(ds, x, y, epsg):
    check_crs(ds)
    if epsg is None:
        raise ValueError("Es necesario indicar el EPSG de las coordenadas de entrada.")
    from rasterio.warp import transform
    xx, yy = transform(f"EPSG:{epsg}", ds.crs, [float(x)], [float(y)])
    return xx[0], yy[0]

def elevation(ds, x, y, epsg):
    xx, yy = point_to_raster(ds, x, y, epsg)
    from rasterio.transform import rowcol
    row, col = rowcol(ds.transform, xx, yy)
    if not (0 <= row < ds.height and 0 <= col < ds.width):
        return {"elevation_m": None, "status": "outside_coverage"}
    # Read exactly one pixel, as a masked value. No full raster allocation.
    from rasterio.windows import Window
    value = ds.read(1, window=Window(col, row, 1, 1), masked=True)[0, 0]
    if bool(getattr(value, "mask", False)):
        return {"elevation_m": None, "status": "nodata"}
    height = float(value)
    if not math.isfinite(height):
        return {"elevation_m": None, "status": "invalid"}
    if ds.units and ds.units[0] and str(ds.units[0]).lower() not in ("m", "metre", "meter", "metres", "meters"):
        return {"elevation_m": None, "status": "unsupported_vertical_unit"}
    # WARNING: units and vertical datum must be verified independently.
    return {"elevation_m": round(height, 3), "status": "ok"}

def main():
    p = argparse.ArgumentParser(description="COTA NET GeoTIFF / BigTIFF prototype")
    sub = p.add_subparsers(dest="command", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("raster")
    e = sub.add_parser("elevation")
    e.add_argument("raster")
    e.add_argument("--x", type=float, required=True)
    e.add_argument("--y", type=float, required=True)
    e.add_argument("--epsg", type=int, required=True)
    a = sub.add_parser("assign")
    a.add_argument("raster")
    a.add_argument("nodes_json")
    a.add_argument("--epsg", type=int, required=True)
    v = sub.add_parser("preview")
    v.add_argument("raster")
    v.add_argument("output_png")
    v.add_argument("--width", type=int, default=1200)
    args = p.parse_args()
    import rasterio
    from rasterio.enums import Resampling
    with rasterio.open(args.raster) as ds:
        if args.command == "inspect":
            emit({"driver": ds.driver, "width": ds.width, "height": ds.height,
                  "count": ds.count, "dtype": list(ds.dtypes), "crs": str(ds.crs) if ds.crs else None,
                  "bounds": list(ds.bounds), "resolution": list(ds.res),
                  "nodata": ds.nodata, "units": list(ds.units),
                  "overviews": ds.overviews(1), "gtm_5482": ds.crs is not None and ds.crs.to_epsg() == 5482,
                  "file_bytes": __import__("os").path.getsize(args.raster)})
        elif args.command == "elevation":
            emit(elevation(ds, args.x, args.y, args.epsg))
        elif args.command == "assign":
            if ds.count != 1:
                raise ValueError("Para asignar cotas se requiere MDT de una banda, no ortofoto RGB.")
            with open(args.nodes_json, encoding="utf-8") as f:
                nodes = json.load(f)
            if not isinstance(nodes, list):
                raise ValueError("nodes_json debe ser una lista de nodos")
            result = []
            for node in nodes:
                z = elevation(ds, node["x"], node["y"], args.epsg)
                result.append({"id": node["id"], **z})
            emit({"source_crs": str(ds.crs), "input_epsg": args.epsg,
                  "vertical_datum": "UNVERIFIED", "nodes": result})
        elif args.command == "preview":
            import numpy as np
            from PIL import Image
            width = max(1, min(args.width, 4096))
            height = max(1, int(ds.height * width / ds.width))
            bands = [1, 2, 3] if ds.count >= 3 else [1]
            img = ds.read(bands, out_shape=(len(bands), height, width),
                          resampling=Resampling.bilinear, masked=True)
            array = np.ma.filled(img, 0)
            if array.dtype != np.uint8:
                # Simple percentile contrast stretch for visualization only.
                output = []
                for band in array:
                    p2, p98 = np.percentile(band, [2, 98])
                    output.append(np.uint8(np.clip((band - p2) * 255 / max(p98 - p2, 1), 0, 255)))
                array = np.stack(output)
            pixels = np.moveaxis(array, 0, -1)
            if len(bands) == 1:
                pixels = pixels[:, :, 0]
            Image.fromarray(pixels).save(args.output_png)
            emit({"output": args.output_png, "width": width, "height": height})

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit({"status": "error", "message": str(exc)})
        sys.exit(1)
