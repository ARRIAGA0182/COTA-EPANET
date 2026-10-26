# COTA NET GIS — Conexión inicial con EPANET INP

Este módulo es un **adaptador independiente**. No está integrado a la ventana Delphi y no modifica la simulación ni los archivos originales. Opera únicamente sobre nodos de [JUNCTIONS] y sus coordenadas en [COORDINATES].

## Uso desde Windows
Instalar rasterio según GIS_Raster/VIEWER.md.

Primero generar una vista previa **sin escribir archivos**:

```powershell
python GIS_Raster/epanet_elevations.py red.inp terreno_mdt.tif --epsg 5482
```

Después de revisar los resultados, CRS horizontal y datum vertical del MDT, crear un **nuevo** INP:

```powershell
python GIS_Raster/epanet_elevations.py red.inp terreno_mdt.tif --epsg 5482 --vertical-datum-verified --apply --output red_con_cotas.inp
```

**Importante:** `--epsg 5482` se refiere a las coordenadas del INP, no necesariamente al CRS del MDT. El programa transforma los puntos al CRS del MDT antes de consultar valores.

El programa modifica solamente el campo Elevation de nodos tipo Junction para los que existe un valor MDT válido. No modifica demandas, tuberías, bombas, depósitos, tanques ni otras propiedades. Nodos sin coordenadas, fuera del MDT o sin datos quedan sin cambios.

## Limitaciones
- Los valores del MDT se obtienen por el píxel más cercano, no por interpolación bilineal.
- Se requiere confirmar unidades y referencia vertical antes de aplicar cambios. La opción --vertical-datum-verified solo registra la confirmación del operador; no constituye una comprobación geodésica automática.
- Los valores de cotas del EPANET INP dependen de las unidades del proyecto. Verificar que la red trabaje en metros antes de transferir un MDT en metros.
- Las redes EPANET con coordenadas de dibujo arbitrarias deben georreferenciarse primero; indicar EPSG no corrige coordenadas locales.
- El adaptador no escribe sobre archivos existentes, pero **no realiza una copia de seguridad automática** porque siempre genera un archivo nuevo.
- No procesa otros tipos de nodos que requieren reglas hidráulicas diferentes: tanques y embalses.
- No está probado con datos reales de Metashape ni con archivos mayores de 4 GB.
- El lector de INP asume texto UTF-8. Proyectos con codificaciones legadas requieren conversión previa.

## Prueba básica
```powershell
cd GIS_Raster
python -m unittest test_epanet_elevations.py
```

## Próximo paso
Integrar una interfaz de revisión en Delphi: seleccionar MDT, previsualizar cambios por nodo, confirmar reemplazos y abrir el nuevo INP con los resultados sin perder la red anterior.
