"""COTA NET GIS: GUI for safe DEM -> EPANET INP elevation transfer.

Separate Windows Tkinter prototype. Does not modify Delphi or the original INP.
"""
import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from epanet_elevations import compute, patch

class App:
    def __init__(self, root):
        self.root=root
        root.title("COTA NET GIS — Elevaciones EPANET")
        root.geometry("1020x650")
        self.inp=tk.StringVar()
        self.dem=tk.StringVar()
        self.epsg=tk.StringVar(value="5482")
        self.verified=tk.BooleanVar(value=False)
        self.status=tk.StringVar(value="Seleccione un archivo EPANET INP y un MDT GeoTIFF.")
        self.lines=None
        self.reports=[]
        self.updates={}
        body=ttk.Frame(root,padding=14)
        body.pack(fill="both",expand=True)
        for i,(name,var,typ) in enumerate((("Archivo EPANET (.inp)",self.inp,"inp"),("Modelo digital del terreno (.tif)",self.dem,"dem"))):
            ttk.Label(body,text=name).grid(row=i,column=0,sticky="w",pady=5)
            ttk.Entry(body,textvariable=var).grid(row=i,column=1,sticky="ew",padx=8)
            ttk.Button(body,text="Examinar",command=lambda t=typ:self.browse(t)).grid(row=i,column=2)
        ttk.Label(body,text="EPSG de las coordenadas INP").grid(row=2,column=0,sticky="w")
        ttk.Entry(body,textvariable=self.epsg,width=12).grid(row=2,column=1,sticky="w",padx=8,pady=6)
        ttk.Button(body,text="Consultar elevaciones",command=self.preview).grid(row=2,column=2,pady=6)
        body.columnconfigure(1,weight=1)
        self.tree=ttk.Treeview(body,columns=("id","before","after","state"),show="headings",height=18)
        for col,heading,width in (("id","Nodo",150),("before","Cota actual",150),("after","Cota MDT (m)",150),("state","Resultado",250)):
            self.tree.heading(col,text=heading)
            self.tree.column(col,width=width,stretch=True)
        self.tree.grid(row=3,column=0,columnspan=3,sticky="nsew",pady=(8,4))
        scrollbar=ttk.Scrollbar(body,orient="vertical",command=self.tree.yview)
        scrollbar.grid(row=3,column=3,sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        body.rowconfigure(3,weight=1)
        ttk.Checkbutton(body,text="He verificado datum vertical y unidades del MDT y de EPANET",variable=self.verified).grid(row=4,column=0,columnspan=3,sticky="w",pady=8)
        buttons=ttk.Frame(body)
        buttons.grid(row=5,column=0,columnspan=3,sticky="ew")
        ttk.Button(buttons,text="Exportar revisión CSV",command=self.export_csv).pack(side="left",padx=3)
        ttk.Button(buttons,text="Guardar nuevo INP con cotas",command=self.save).pack(side="right",padx=3)
        ttk.Label(body,textvariable=self.status,wraplength=940).grid(row=6,column=0,columnspan=3,sticky="w",pady=8)
        for var in (self.inp,self.dem,self.epsg):
            var.trace_add("write",lambda *_:self.invalidate())

    def invalidate(self):
        self.lines=None
        self.reports=[]
        self.updates={}
        self.verified.set(False)
        self.tree.delete(*self.tree.get_children())

    def browse(self,typ):
        path=filedialog.askopenfilename(filetypes=[("EPANET INP","*.inp")] if typ=="inp" else [("GeoTIFF","*.tif *.tiff")])
        if path:
            (self.inp if typ=="inp" else self.dem).set(path)

    def preview(self):
        self.invalidate()
        try:
            if not self.inp.get() or not self.dem.get():
                raise ValueError("Debe seleccionar archivos INP y MDT.")
            epsg=int(self.epsg.get())
            self.lines,self.reports,self.updates=compute(self.inp.get(),self.dem.get(),epsg)
            for row in self.reports:
                self.tree.insert("","end",values=(row["id"],row["old_elevation"],row["new_elevation"] if row["new_elevation"] is not None else "—",row["status"]))
            self.status.set(f"Nodos revisados: {len(self.reports)} | Con cota válida: {len(self.updates)} | Sin actualización: {len(self.reports)-len(self.updates)}.")
        except Exception as exc:
            messagebox.showerror("Error de consulta",str(exc))

    def export_csv(self):
        if not self.reports:
            messagebox.showinfo("Sin datos","Primero consulte las elevaciones.")
            return
        dest=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")])
        if not dest:
            return
        if Path(dest).exists():
            messagebox.showerror("Archivo existente","Seleccione un nombre nuevo para conservar los archivos existentes.")
            return
        with open(dest,"x",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["id","old_elevation","new_elevation","status"])
            w.writeheader()
            w.writerows(self.reports)
        self.status.set(f"Revisión exportada: {dest}")

    def save(self):
        if self.lines is None or not self.reports:
            messagebox.showwarning("Sin revisión","Primero consulte las elevaciones.")
            return
        if not self.updates:
            messagebox.showwarning("Sin cotas","No hay elevaciones válidas para aplicar.")
            return
        if not self.verified.get():
            messagebox.showwarning("Validación requerida","Confirme datum vertical y unidades antes de aplicar.")
            return
        dest=filedialog.asksaveasfilename(defaultextension=".inp",filetypes=[("EPANET INP","*.inp")],
                                            initialfile=Path(self.inp.get()).stem+"_con_cotas.inp")
        if not dest:
            return
        if Path(dest).resolve()==Path(self.inp.get()).resolve() or Path(dest).exists():
            messagebox.showerror("Protección del original","Elija una ruta nueva. No se sobrescriben archivos.")
            return
        if not messagebox.askyesno("Confirmar",f"¿Guardar un nuevo INP con {len(self.updates)} cotas actualizadas?"):
            return
        try:
            with open(dest,"x",encoding="utf-8",newline="") as f:
                f.write("".join(patch(self.lines,self.updates)))
            self.status.set(f"Nuevo INP guardado: {dest}. El original permanece intacto.")
        except Exception as exc:
            messagebox.showerror("Error al guardar",str(exc))

if __name__=="__main__":
    root=tk.Tk()
    App(root)
    root.mainloop()
