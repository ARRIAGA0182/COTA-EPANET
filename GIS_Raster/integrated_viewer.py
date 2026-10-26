"""COTA NET GIS: visor combinado de ortofoto, MDT y nodos reales EPANET.

Prototipo independiente. No altera Delphi ni archivos originales.
Ejecutar desde GIS_Raster: python integrated_viewer.py
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import math
import json
from rasterio.warp import transform as reproject
from gis_viewer import GisViewer
from epanet_elevations import load_inp, compute, patch


class IntegratedViewer(GisViewer):
    def __init__(self, root):
        super().__init__(root)
        root.title("COTA NET — GIS + EPANET (prototipo)")
        self.inp_path = None
        self.inp_epsg = None
        self.inp_lines = None
        self.inp_node_positions = {}
        self.inp_records = {}
        self.inp_originals = {}
        self.checked_vertical = tk.BooleanVar(value=False)
        self.current_node = None
        bar = ttk.Frame(root, padding=5)
        bar.pack(before=self.canvas, fill="x")
        ttk.Button(bar, text="Importar red EPANET (.inp)", command=self.import_inp).pack(side="left", padx=3)
        ttk.Button(bar, text="Revisar cotas de toda la red", command=self.review_all).pack(side="left", padx=3)
        ttk.Button(bar, text="Guardar nueva red (.inp)", command=self.save_inp).pack(side="left", padx=3)
        ttk.Checkbutton(bar, text="Datum vertical y unidades revisados", variable=self.checked_vertical).pack(side="left", padx=8)
        self.detail = tk.StringVar(value="Seleccione un nodo EPANET sobre la ortofoto para consultar su elevación.")
        ttk.Label(root, textvariable=self.detail, padding=5).pack(before=self.canvas, fill="x")
        self.root.bind("<Escape>", lambda _: self.clear_selection())

    def open_ortho(self):
        old = self.ortho
        super().open_ortho()
        if self.ortho is not None and self.ortho is not old:
            # CRS changed: existing INP projected locations must be recalculated.
            self.refresh_inp_nodes()

    def open_dem(self):
        old = self.dem
        super().open_dem()
        if self.dem is not old:
            self.checked_vertical.set(False)
            self.refresh_elevations()

    def import_inp(self):
        if self.ortho is None:
            messagebox.showwarning("Primero ortofoto", "Cargue una ortofoto georreferenciada antes del INP.")
            return
        source = filedialog.askopenfilename(filetypes=[("EPANET INP", "*.inp")])
        if not source:
            return
        epsg = self.ask_epsg()
        if epsg is None:
            return
        try:
            lines, coordinates, junctions = load_inp(source)
            if not junctions:
                raise ValueError("El INP no contiene nodos [JUNCTIONS].")
            self.inp_path, self.inp_epsg, self.inp_lines = source, epsg, lines
            self.inp_records = {key: (ix, display, original) for key, (ix, display, original) in junctions.items()}
            self.inp_originals = coordinates
            self.checked_vertical.set(False)
            self.refresh_inp_nodes()
            self.detail.set(f"Red EPANET: {Path(source).name} | {len(junctions)} nodos | EPSG:{epsg}")
        except Exception as exc:
            messagebox.showerror("INP inválido", str(exc))

    def ask_epsg(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Sistema de coordenadas de EPANET")
        dialog.transient(self.root)
        dialog.grab_set()
        ttk.Label(dialog, text="EPSG real de [COORDINATES] en el INP (GTM: 5482):", padding=12).pack()
        value = tk.StringVar(value="5482")
        entry = ttk.Entry(dialog, textvariable=value)
        entry.pack(padx=12, fill="x")
        result = []
        def accept():
            try:
                code = int(value.get())
                if code <= 0: raise ValueError()
                result.append(code)
                dialog.destroy()
            except ValueError:
                messagebox.showerror("EPSG", "Introduzca un código EPSG positivo.", parent=dialog)
        ttk.Button(dialog, text="Continuar", command=accept).pack(pady=12)
        dialog.bind("<Return>", lambda _: accept())
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        entry.focus_set()
        self.root.wait_window(dialog)
        return result[0] if result else None

    def refresh_inp_nodes(self):
        self.inp_node_positions = {}
        if not self.ortho or not self.inp_path:
            return
        try:
            for key in self.inp_records:
                if key not in self.inp_originals:
                    continue
                x, y = self.inp_originals[key]
                xx, yy = reproject(f"EPSG:{self.inp_epsg}", self.ortho.crs, [x], [y])
                self.inp_node_positions[key] = (xx[0], yy[0])
            self.refresh_elevations()
        except Exception as exc:
            messagebox.showerror("Coordenadas", f"No se pudo reproyectar nodos: {exc}")

    def refresh_elevations(self):
        self.checked_vertical.set(False)
        self.current_node = None
        self.redraw()

    def draw_nodes(self):
        super().draw_nodes()
        if not hasattr(self, "inp_node_positions") or not self.ortho or not self.extent:
            return
        self.canvas.delete("inp_nodes")
        for key, (x, y) in self.inp_node_positions.items():
            sx, sy = self.to_screen(x, y)
            w, h = self.canvas_size()
            if not (-10 <= sx <= w+10 and -10 <= sy <= h+10):
                continue
            selected = key == self.current_node
            self.canvas.create_oval(sx-5, sy-5, sx+5, sy+5,
                                    fill="#ffb300" if selected else "#e05048",
                                    outline="white", width=2, tags="inp_nodes")
            if selected:
                self.canvas.create_text(sx+10, sy-12, text=self.inp_records[key][1],
                                        anchor="w", fill="#203343", font=("Segoe UI", 11, "bold"), tags="inp_nodes")

    def clear_selection(self):
        self.current_node = None
        self.draw_nodes()

    def mouse_up(self, event):
        # Preserve panning and free-node mode from the base viewer.
        if not self.drag:
            return
        x0, y0, _, moved = self.drag
        if moved or self.query_mode.get() == "node":
            return super().mouse_up(event)
        self.drag = None
        point = self.to_world(event.x, event.y)
        # Select a real INP node within a screen-space hit radius.
        nearby = []
        for key, pos in self.inp_node_positions.items():
            sx, sy = self.to_screen(*pos)
            dist = math.hypot(sx - event.x, sy - event.y)
            if dist <= 12:
                nearby.append((dist, key))
        if not nearby:
            self.current_node = None
            z, status = self.sample_dem(*point)
            self.detail.set(f"Consulta libre | X {point[0]:.3f}, Y {point[1]:.3f} | MDT: {z if z is not None else '—'} m ({status})")
        else:
            self.current_node = min(nearby)[1]
            key = self.current_node
            _, name, previous = self.inp_records[key]
            z, status = self.sample_dem(*self.inp_node_positions[key])
            self.detail.set(f"Nodo {name} | Cota INP: {previous} | MDT: {z if z is not None else '—'} m | {status}")
        self.draw_nodes()

    def review_all(self):
        if not self.inp_path or not self.dem:
            messagebox.showwarning("Faltan datos", "Importe primero ortofoto, red INP y MDT.")
            return
        try:
            _, self.reports, self.updates = compute(self.inp_path, self.dem.name, self.inp_epsg)
            dlg = tk.Toplevel(self.root)
            dlg.title("Vista previa — elevaciones MDT / EPANET")
            dlg.geometry("820x470")
            tree = ttk.Treeview(dlg, columns=("id","actual","mdt","estado"), show="headings")
            for key, title in [("id","Nodo"),("actual","Cota actual"),("mdt","Cota MDT (m)"),("estado","Estado")]:
                tree.heading(key, text=title)
                tree.column(key, width=160)
            tree.pack(fill="both", expand=True, padx=10, pady=10)
            for item in self.reports:
                tree.insert("", "end", values=(item["id"],item["old_elevation"],
                       item["new_elevation"] if item["new_elevation"] is not None else "—", item["status"]))
            ttk.Label(dlg, text=f"Con cota disponible: {len(self.updates)} / {len(self.reports)}. Esta vista no modifica el INP.").pack(pady=8)
        except Exception as exc:
            messagebox.showerror("Error consultando MDT", str(exc))

    def save_inp(self):
        if not self.inp_path or not self.dem:
            messagebox.showwarning("Faltan datos", "Importe red y MDT y revise sus cotas.")
            return
        if not self.checked_vertical.get():
            messagebox.showwarning("Verificación vertical", "Verifique datum vertical y unidades del MDT y de EPANET.")
            return
        try:
            # Recompute against the original INP and the currently opened MDT.
            lines, report, updates = compute(self.inp_path, self.dem.name, self.inp_epsg)
            if not updates:
                messagebox.showinfo("Sin resultados", "Ningún nodo tiene cota MDT válida.")
                return
            target = filedialog.asksaveasfilename(defaultextension=".inp", filetypes=[("EPANET INP", "*.inp")],
                                                   initialfile=Path(self.inp_path).stem+"_con_cotas.inp")
            if not target:
                return
            if Path(target).resolve() == Path(self.inp_path).resolve() or Path(target).exists():
                messagebox.showerror("Seguridad", "La salida debe ser un archivo nuevo; no se sobrescriben archivos existentes.")
                return
            if not messagebox.askyesno("Confirmar", f"¿Guardar {len(updates)} elevaciones en un nuevo INP? El original no cambiará."):
                return
            with open(target, "x", encoding="utf-8", newline="") as f:
                f.write("".join(patch(lines, updates)))
            self.detail.set(f"INP nuevo guardado: {target}. Original conservado.")
        except Exception as exc:
            messagebox.showerror("No se pudo exportar", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    IntegratedViewer(root)
    root.mainloop()
