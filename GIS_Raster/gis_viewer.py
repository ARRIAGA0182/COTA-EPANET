#!/usr/bin/env python3
"""COTA NET GIS desktop raster viewer (prototype).

Tkinter + Rasterio/GDAL + Pillow; zoom, pan, and DTM elevation sampling.
Read only the visible raster window (resampled to the canvas size).
Does not change EPANET data or the raster. Python 3.11+ on Windows.
"""
import json
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
import rasterio
from PIL import Image, ImageTk
from rasterio.enums import Resampling
from rasterio.windows import Window
from rasterio.warp import transform as crs_transform


class GisViewer:
    def __init__(self, root):
        self.root = root
        root.title("COTA NET — Visor GIS (prototipo)")
        root.geometry("1180x750")
        self.ortho = None
        self.dem = None
        self.photo = None
        self.extent = None  # (left, bottom, right, top) in ortho CRS
        self.drag = None
        self.nodes = []
        self.node_counter = 1
        self.query_mode = tk.StringVar(value="query")
        self.status = tk.StringVar(value="Abra una ortofoto GeoTIFF para comenzar")
        toolbar = ttk.Frame(root, padding=6)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Abrir ortofoto", command=self.open_ortho).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Abrir MDT", command=self.open_dem).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Vista completa", command=self.full_extent).pack(side="left", padx=3)
        ttk.Radiobutton(toolbar, text="Consultar cota", variable=self.query_mode, value="query").pack(side="left", padx=8)
        ttk.Radiobutton(toolbar, text="Crear nodo", variable=self.query_mode, value="node").pack(side="left", padx=8)
        ttk.Button(toolbar, text="Exportar nodos JSON", command=self.export_nodes).pack(side="right", padx=3)
        self.canvas = tk.Canvas(root, bg="#dde5e3", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        ttk.Label(root, textvariable=self.status, padding=6).pack(fill="x")
        self.canvas.bind("<Configure>", self.redraw)
        self.canvas.bind("<ButtonPress-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)
        self.canvas.bind("<MouseWheel>", self.mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self.zoom(e.x, e.y, 0.8))
        self.canvas.bind("<Button-5>", lambda e: self.zoom(e.x, e.y, 1.25))
        root.protocol("WM_DELETE_WINDOW", self.close)

    def open_ortho(self):
        path = filedialog.askopenfilename(filetypes=[("GeoTIFF/BigTIFF", "*.tif *.tiff"), ("Todos", "*.*")])
        if not path:
            return
        try:
            ds = rasterio.open(path)
            if not ds.crs:
                raise ValueError("La ortofoto no tiene CRS; georreferénciela antes de importarla.")
            if ds.count < 1:
                raise ValueError("Raster sin bandas.")
            if self.ortho:
                self.ortho.close()
            self.ortho = ds
            self.nodes.clear()
            self.node_counter = 1
            self.extent = None
            self.full_extent()
            self.status.set(f"Ortofoto: {ds.width}×{ds.height} px | {ds.crs} | {ds.count} bandas")
        except Exception as exc:
            messagebox.showerror("No se pudo importar", str(exc))

    def open_dem(self):
        path = filedialog.askopenfilename(filetypes=[("MDT GeoTIFF", "*.tif *.tiff"), ("Todos", "*.*")])
        if not path:
            return
        try:
            ds = rasterio.open(path)
            if not ds.crs or ds.count != 1:
                raise ValueError("El MDT debe tener CRS y una banda de elevación.")
            if self.dem:
                self.dem.close()
            self.dem = ds
            self.status.set(f"MDT listo: {ds.width}×{ds.height} px | {ds.crs}. Verifique datum vertical y unidades.")
            self.draw_nodes()
        except Exception as exc:
            messagebox.showerror("No se pudo importar MDT", str(exc))

    def full_extent(self):
        if not self.ortho:
            return
        b = self.ortho.bounds
        self.extent = (b.left, b.bottom, b.right, b.top)
        self.redraw()

    def canvas_size(self):
        return max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())

    def fitted_extent(self):
        if not self.extent:
            return None
        l, b, r, t = self.extent
        w, h = self.canvas_size()
        cx, cy = (l + r) / 2, (b + t) / 2
        span_x, span_y = max(1e-6, r - l), max(1e-6, t - b)
        units = max(span_x / w, span_y / h)
        return (cx - units * w / 2, cy - units * h / 2,
                cx + units * w / 2, cy + units * h / 2)

    def to_world(self, sx, sy):
        l, b, r, t = self.fitted_extent()
        w, h = self.canvas_size()
        return l + sx * (r - l) / w, t - sy * (t - b) / h

    def to_screen(self, x, y):
        l, b, r, t = self.fitted_extent()
        w, h = self.canvas_size()
        return (x - l) * w / (r - l), (t - y) * h / (t - b)

    def redraw(self, event=None):
        if not self.ortho or not self.extent:
            return
        try:
            # North-up rasters only in prototype. Rotated rasters require GDAL WarpedVRT.
            if not math.isclose(self.ortho.transform.b, 0, abs_tol=1e-12) or not math.isclose(self.ortho.transform.d, 0, abs_tol=1e-12):
                raise ValueError("Raster girado: hay que reproyectarlo a north-up (futura mejora).")
            l, b, r, t = self.fitted_extent()
            w, h = self.canvas_size()
            # Cap output resolution, never decode a full original multi-GB file.
            scale = min(1.0, 1800 / max(w, h))
            ow, oh = max(1, int(w * scale)), max(1, int(h * scale))
            win = rasterio.windows.from_bounds(l, b, r, t, transform=self.ortho.transform)
            indexes = [1, 2, 3] if self.ortho.count >= 3 else [1]
            data = self.ortho.read(indexes, window=win, out_shape=(len(indexes), oh, ow),
                                    boundless=True, masked=True, fill_value=0,
                                    resampling=Resampling.bilinear)
            out = np.ma.filled(data, 0)
            if out.dtype != np.uint8:
                # Simple visualization range; no changes to source data.
                transformed = []
                for band in out:
                    valid = band[np.isfinite(band)]
                    lo, hi = np.percentile(valid, [2, 98]) if valid.size else (0, 1)
                    transformed.append(np.uint8(np.clip((band - lo) * 255 / max(hi - lo, 1), 0, 255)))
                out = np.stack(transformed)
            pix = np.moveaxis(out, 0, -1)
            if len(indexes) == 1:
                pix = pix[:, :, 0]
            img = Image.fromarray(pix).resize((w, h), Image.Resampling.BILINEAR)
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
            self.draw_nodes()
        except Exception as exc:
            self.status.set(f"Error mostrando raster: {exc}")

    def sample_dem(self, x, y):
        if not self.dem or not self.ortho:
            return None, "sin MDT"
        try:
            if self.dem.crs != self.ortho.crs:
                xs, ys = crs_transform(self.ortho.crs, self.dem.crs, [x], [y])
                x, y = xs[0], ys[0]
            row, col = self.dem.index(x, y)
            if not (0 <= row < self.dem.height and 0 <= col < self.dem.width):
                return None, "fuera de cobertura"
            value = self.dem.read(1, window=Window(col, row, 1, 1), masked=True)[0, 0]
            if np.ma.is_masked(value) or not math.isfinite(float(value)):
                return None, "sin dato"
            if self.dem.units and self.dem.units[0] and self.dem.units[0].lower() not in ("m", "metre", "meter", "metres", "meters"):
                return None, "unidad vertical no compatible"
            return round(float(value), 3), "válido (datum vertical sin verificar)"
        except Exception as exc:
            return None, str(exc)

    def mouse_down(self, event):
        if self.ortho:
            self.drag = (event.x, event.y, self.fitted_extent(), False)

    def mouse_drag(self, event):
        if not self.drag:
            return
        x0, y0, (l, b, r, t), _ = self.drag
        w, h = self.canvas_size()
        dx, dy = (event.x - x0) * (r - l) / w, (event.y - y0) * (t - b) / h
        self.extent = (l - dx, b + dy, r - dx, t + dy)
        self.drag = (x0, y0, (l, b, r, t), True)
        # Avoid expensive redraw on each event. Refresh on mouse release.

    def mouse_up(self, event):
        if not self.drag:
            return
        _, _, _, moved = self.drag
        self.drag = None
        if moved:
            self.redraw()
            return
        x, y = self.to_world(event.x, event.y)
        z, state = self.sample_dem(x, y)
        if self.query_mode.get() == "node":
            name = f"N-{self.node_counter:03d}"
            self.node_counter += 1
            self.nodes.append(dict(id=name, x=round(x, 3), y=round(y, 3), elevation_m=z,
                                   elevation_status=state))
            self.draw_nodes()
        self.status.set(f"{self.ortho.crs}: X {x:.3f}, Y {y:.3f} | Elevación: {z if z is not None else '—'} m ({state})")

    def draw_nodes(self):
        if not self.ortho or not self.extent:
            return
        self.canvas.delete("nodes")
        for n in self.nodes:
            sx, sy = self.to_screen(n["x"], n["y"])
            self.canvas.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill="#10a4f0", outline="white", width=2, tags="nodes")
            self.canvas.create_text(sx + 10, sy - 10, text=n["id"], anchor="w",
                                    fill="#0a2635", font=("Segoe UI", 10, "bold"), tags="nodes")

    def zoom(self, sx, sy, factor):
        if not self.extent:
            return
        x, y = self.to_world(sx, sy)
        l, b, r, t = self.fitted_extent()
        self.extent = (x + (l - x) * factor, y + (b - y) * factor,
                       x + (r - x) * factor, y + (t - y) * factor)
        self.redraw()

    def mouse_wheel(self, event):
        self.zoom(event.x, event.y, 0.8 if event.delta > 0 else 1.25)

    def export_nodes(self):
        if not self.nodes:
            messagebox.showinfo("Sin nodos", "Seleccione 'Crear nodo' y haga clic sobre el mapa.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"crs": str(self.ortho.crs), "vertical_datum_verified": False,
                           "nodes": self.nodes}, f, ensure_ascii=False, indent=2)
            self.status.set(f"Nodos exportados: {len(self.nodes)}. No se han escrito datos EPANET.")

    def close(self):
        if self.ortho:
            self.ortho.close()
        if self.dem:
            self.dem.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    GisViewer(root)
    root.mainloop()
