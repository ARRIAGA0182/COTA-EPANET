# COTA NET GIS — visor de red hidráulica con MDT (prototipo integrado)

> Es una sola **ventana independiente de Python/Tkinter**. Todavía NO reemplaza ni se integra dentro de la interfaz original Delphi EPANET.

## Ejecutar en Windows 11

Desde la raíz del repositorio:

```powershell
py -3 -m venv .venv
.venv\\Scripts\\python -m pip install "rasterio>=1.3,<2" "numpy>=1.24" "Pillow>=10"
.venv\\Scripts\\python GIS_Raster\\integrated_viewer.py
```

## Flujo de trabajo

1. **Abrir ortofoto** de Metashape (GeoTIFF/BigTIFF).
2. **Abrir MDT** monobanda con elevaciones del terreno, sistema de referencia conocido.
3. **Importar red EPANET** desde un INP que contenga [COORDINATES] georreferenciadas; indicar el **EPSG de los nodos INP**, por ejemplo 5482 para GTM Guatemala. No asumir 5482 si la red utiliza coordenadas locales.
4. Los nodos de tipo [JUNCTIONS] se dibujan sobre la ortofoto. Con **Consultar cota** activado, hacer clic junto a un nodo rojo para consultar su elevación. La barra muestra cota original vs cota MDT.
5. **Revisar cotas de toda la red** muestra resultados para cada nodo y nodos sin datos.
6. Si se han verificado CRS, datum vertical y unidades de ambos proyectos, activar **Datum vertical y unidades revisados**, pulsar **Guardar nueva red (.inp)** y elegir un nombre nuevo.

La asignación no es automática sin confirmación: el INP original permanece intacto y solamente se actualiza el campo *Elevation* de [JUNCTIONS] con elevaciones válidas.

## Restricciones y pruebas pendientes
- El mapa usa Rasterio y lee la ventana raster visible, no toda la ortofoto; rendimiento con TIFF/BigTIFF >4 GB **pendiente de validación real**.
- El mapa es un prototipo para rasters north-up; ortofotos rotadas necesitan WarpedVRT.
- El muestreo MDT usa píxel más cercano; interpolación bilineal aún pendiente.
- El MDT y el INP deben compartir un datum vertical compatible y **elevaciones en metros**. EPSG:5482 identifica referencia horizontal, no datum vertical.
- No se distinguen automáticamente coordenadas GIS de coordenadas locales de dibujo de EPANET.
- Los nodos sin [COORDINATES], fuera del MDT o con NODATA no reciben nueva elevación.
- Tanques y reservorios NO se actualizan; requieren reglas específicas.
- Para redes EPANET con unidades imperiales, **no transferir** MDT expresado en metros sin convertir unidades.
- Archivos INP deben tener codificación UTF-8 para este prototipo.
- No hay compilación Windows, pruebas de UI o validación con archivos Metashape todavía.
- La UI Delphi y el motor de simulación permanecen sin modificaciones.

## Siguiente etapa
Pruebas automáticas de reproyección, soporte de rasters girados, guardado de proyecto GIS, interoperabilidad segura con Delphi y compilación de una versión Windows para usuarios.
