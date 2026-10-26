# COTA NET — GIS Raster (fase 1, prototipo técnico)

Rama: `feature/gis-raster`. Esta carpeta NO está conectada todavía a la interfaz Delphi EPANET y no modifica el motor hidráulico.

## Alcance iniciado
- Lectura por demanda de GeoTIFF/BigTIFF con Rasterio (basado en GDAL); el límite real depende de GDAL/almacenamiento.
- Inspección de proyección, extensión, tamaño, resolución, bandas, unidades y overviews.
- Vista previa reducida sin decodificar el raster completo en RAM.
- Consulta de elevación por coordenadas, transformando desde EPSG de entrada al CRS del raster.
- Asignación por lotes de elevaciones de MDT a nodos en JSON; salida compatible con un adaptador posterior a EPANET.

## Instalación del prototipo
Se recomienda Python 3.11+ en Windows x64 y un entorno virtual.
```powershell
python -m pip install "rasterio>=1.3,<2" "numpy>=1.24" "Pillow>=10"
python GIS_Raster/raster_bridge.py inspect "C:\\GIS\\ortofoto.tif"
python GIS_Raster/raster_bridge.py preview "C:\\GIS\\ortofoto.tif" "preview.png" --width 1400
python GIS_Raster/raster_bridge.py elevation "C:\\GIS\\mdt.tif" --x 500000 --y 1700000 --epsg 5482
python GIS_Raster/raster_bridge.py assign "C:\\GIS\\mdt.tif" "nodes.json" --epsg 5482
```
Las coordenadas del ejemplo son ilustrativas. `nodes.json`:
```json
[{"id":"N-01","x":500000,"y":1700000},{"id":"N-02","x":500040,"y":1700050}]
```

## Precauciones hidráulicas y de calidad
1. Usar MDT/DTM de terreno, no DSM con árboles/techos.
2. Confirmar datum vertical y unidades de las alturas antes de transferir a EPANET. El CRS horizontal GTM EPSG:5482 no determina por sí solo el datum vertical.
3. La lectura actual es **nearest pixel** (sin interpolación); interpolación bilineal validada queda pendiente.
4. Nodos fuera de cobertura o sobre NODATA quedan sin cota; nunca sustituir por 0 silenciosamente.
5. La ortofoto RGB no es fuente de elevaciones.
6. El programa no convierte por ahora nodos de JSON en archivos INP ni modifica EPANET.
7. Para rasters grandes optimizar con pirámides (GDAL `gdaladdo`) o COG, sujeto a espacio en disco. La vista previa de este prototipo está limitada a 4096 píxeles de ancho.

## Próximas integraciones
- Motor de teselas/ventanas para zoom y panorámica interactiva en Delphi.
- Administrador de capas y selección de ortofoto/MDT.
- Persistencia CRS por proyecto, GTM predeterminado opcional y reproyección de puntos.
- Enlace entre IDs de nodos EPANET y coordenadas cartográficas; confirmación antes de reemplazar elevaciones existentes.
- Pruebas de BigTIFF >4 GB, archivos Metashape, rasters sin CRS, NODATA, verticales, nodos fuera de cobertura y rendimiento en Windows.
