#!/usr/bin/env python3
"""Safe COTA NET EPANET INP elevation adapter.
Requires rasterio. Preview by default; --apply writes NEW INP only.
Only [JUNCTIONS] elevations are updated; tank/reservoir semantics differ.
Coordinates come from [COORDINATES] in the selected INP.
"""
import argparse
import json
import math
from pathlib import Path
import re
import sys

SECTION = re.compile(r"^\s*\[([^]]+)\]", re.I)
NUM = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")

def fields(line):
    body, sep, comment = line.partition(";")
    return body.split(), (sep + comment if sep else "")

def load_inp(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)
    section = ""
    coords, junctions = {}, {}
    for ix, line in enumerate(lines):
        m = SECTION.match(line)
        if m:
            section = m.group(1).strip().upper()
            continue
        vals, _ = fields(line)
        if not vals:
            continue
        if section == "COORDINATES" and len(vals) >= 3:
            coords[vals[0].upper()] = (float(vals[1]), float(vals[2]))
        elif section == "JUNCTIONS" and len(vals) >= 2:
            junctions[vals[0].upper()] = (ix, vals[0], vals[1])
    return lines, coords, junctions

def compute(inp, dem_path, epsg):
    import rasterio
    from rasterio.warp import transform
    from rasterio.windows import Window
    lines, coords, junctions = load_inp(inp)
    reports = []
    updates = {}
    with rasterio.open(dem_path) as dem:
        if not dem.crs or dem.count != 1:
            raise ValueError("MDT debe tener CRS y una sola banda")
        if not epsg:
            raise ValueError("Es obligatorio indicar el EPSG de las coordenadas INP")
        units = dem.units[0] if dem.units else None
        if units and units.lower() not in ("m","meter","metre","meters","metres"):
            raise ValueError("Las unidades verticales del MDT no son metros")
        for key, (index, original, previous) in junctions.items():
            item = {"id":original, "old_elevation":previous, "new_elevation":None}
            if key not in coords:
                item["status"] = "missing_coordinates"
            elif not NUM.fullmatch(previous):
                item["status"] = "invalid_original_elevation"
            else:
                x, y = coords[key]
                xx, yy = transform(f"EPSG:{epsg}", dem.crs, [x], [y])
                row, col = dem.index(xx[0], yy[0])
                if not (0 <= row < dem.height and 0 <= col < dem.width):
                    item["status"] = "outside_dem"
                else:
                    z = dem.read(1, window=Window(col,row,1,1), masked=True)[0,0]
                    if bool(getattr(z, "mask", False)) or not math.isfinite(float(z)):
                        item["status"] = "nodata"
                    else:
                        value = float(z)
                        item["new_elevation"] = round(value, 3)
                        item["status"] = "ready"
                        updates[index] = (original, f"{value:.3f}")
            reports.append(item)
    return lines, reports, updates

def patch(lines, updates):
    result = lines[:]
    for ix, (name, new_value) in updates.items():
        line = lines[ix]
        body, sep, comment = line.partition(";")
        newline = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
        match = re.match(r"^(\s*\S+\s+)(\S+)(.*)$", body.rstrip("\r\n"))
        if not match or match.group(1).strip().upper() != name.upper():
            raise ValueError(f"No se pudo modificar el nodo: {name}")
        result[ix] = match.group(1) + new_value + match.group(3) + (sep + comment.rstrip("\r\n") if sep else "") + newline
    return result

def main():
    p=argparse.ArgumentParser(description="Vista previa segura de elevaciones INP ← MDT")
    p.add_argument("inp")
    p.add_argument("dem")
    p.add_argument("--epsg",type=int,required=True,help="EPSG del bloque [COORDINATES] INP")
    p.add_argument("--apply",action="store_true",help="Escribir archivo de salida nuevo")
    p.add_argument("--output",help="Ruta de nuevo INP; nunca se sobrescribe")
    p.add_argument("--vertical-datum-verified",action="store_true",help="Confirmación explícita de datum/unidades verticales")
    args=p.parse_args()
    lines,reports,updates=compute(args.inp,args.dem,args.epsg)
    summary={"junctions":len(reports),"ready":len(updates),"skipped":len(reports)-len(updates),
             "vertical_datum_verified":args.vertical_datum_verified,"changes":reports}
    if args.apply:
        if not args.vertical_datum_verified:
            p.error("Para aplicar, confirme --vertical-datum-verified")
        source=Path(args.inp).resolve()
        output=Path(args.output).resolve() if args.output else source.with_name(source.stem+"_con_cotas.inp")
        if source==output or output.exists():
            p.error("La salida debe ser un archivo nuevo, distinto del INP original")
        output.write_text("".join(patch(lines, updates)),encoding="utf-8")
        summary["saved_to"]=str(output)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(json.dumps({"error":str(e)},ensure_ascii=False),file=sys.stderr)
        sys.exit(1)
