# COTA NET — Visor GIS de escritorio (prototipo fase 1.2)

Este es un **visor independiente en Python**, no una pantalla integrada al EPANET Delphi. No modifica archivos INP ni el motor hidráulico.

## Windows 11: instalación y ejecución

Necesita Python 3.11+ de 64 bits con Tkinter disponible.

```powershell
py -3 -m venv .venv
.venv\\Scripts\\python -m pip install "rasterio>=1.3,<2" "Pillow>=10" "numpy>=1.24"
.venv\\Scripts\\python GIS_Raster\\gis_viewer.py
```

## Lo que hace

- Abre ortofotos `.tif/.tiff` georreferenciadas (incluyendo BigTIFF cuando el GDAL instalado lo admita).
- Zoom con rueda del ratón, pan arrastrando, vista completa.
- Lee bloques y los remuestrea a la resolución del lienzo (máximo interno de 1800 px); **no lee toda la ortofoto en RAM**.
- Abre MDT monobanda GeoTIFF (puede tener otro CRS).
- Consulta la elevación del píxel del MDT con clic; transforma coordenadas de ortofoto a CRS del MDT.
- Crea nodos de ejemplo con coordenadas y cota, y los exporta a JSON para una integración posterior.

## Restricciones de esta primera versión

- Prototipo sin pruebas todavía en Windows ni con datos Agisoft Metashape reales mayores de 4 GB.
- Soporta rasters orientados al norte (sin rotación/skew), no todo GeoTIFF posible.
- No es un visor multiproyecto ni carga varias capas simultáneas.
- El visor supone que la ortofoto y el proyecto comparten el CRS. Puede consultar MDT en CRS diferente.
- Elevación consultada por **vecino más cercano**; queda pendiente bilineal y método configurable.
- **Confirmar vertical datum y unidades del MDT** antes de usar cualquier valor hidráulico. El código no asigna valores a los nodos EPANET ni los reemplaza.
- Crear nodos sobre el mapa es solo demostración. No hay sincronización con IDs EPANET ni edición INP.
- La calidad/performance de formatos muy grandes depende de compresión, overviews, disco y RAM.
- Elevaciones fuera del MDT o NoData quedan vacías, no se inventa cota cero.
- Para muchos nodos simultáneos se recomienda preparar su enlace con la interfaz Delphi en una fase posterior.

## Siguiente etapa de integración

1. Probar con ortofoto de 362 MB, BigTIFF >4 GB y un MDT con puntos de control.
2. Integrar un administrador de capas y guardado del proyecto GIS.
3. Construir conector Delphi/EPANET: nodo EPANET ↔ coordenadas ↔ muestreo DEM ↔ confirmación de cambios ↔ archivo INP.
4. Probar que simulaciones EPANET preexistentes no cambien si no se aprueban nuevas cotas.
