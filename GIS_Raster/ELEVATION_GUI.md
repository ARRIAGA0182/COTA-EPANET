# Ventana gráfica para asignar cotas a EPANET

Esta versión es una **herramienta Windows independiente en Tkinter**. La integración dentro de los formularios Delphi del EPANET original sigue pendiente.

## Iniciar en Windows 11
```powershell
py -3 -m venv .venv
.venv\\Scripts\\python -m pip install "rasterio>=1.3,<2" "numpy>=1.24" "Pillow>=10"
.venv\\Scripts\\python GIS_Raster\\elevation_gui.py
```

## Flujo
1. Elegir red EPANET INP georreferenciada.
2. Elegir MDT monobanda georreferenciado desde Metashape.
3. Especificar el EPSG **de [COORDINATES] del INP**, por ejemplo 5482 cuando realmente estén en GTM.
4. Seleccionar **Consultar elevaciones**; revisar cotas anteriores/nuevas y estados.
5. Confirmar manualmente sistema vertical y unidades, y guardar un **INP nuevo**.
6. Opcional: exportar CSV para revisión.

**No modifica el INP original ni el motor hidráulico.** Solo cambia el campo Elevation de [JUNCTIONS] cuando el MDT tiene un dato válido. No procesa tanques ni reservorios. El campo de verificación vertical **no valida automáticamente** un datum ni la calidad del levantamiento.

Pendientes para la aplicación integrada: editor de propiedades Delphi, sincronización bidireccional de nodos, selector visual sobre el mapa, gestión de capas, y pruebas en Windows con ortofotos BigTIFF de más de 4 GB. Antes de distribución revisar compatibilidad con unidades del proyecto, CRS, datum vertical, codificaciones INP y rendimiento.
