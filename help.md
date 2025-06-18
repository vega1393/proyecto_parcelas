# [📋] Manual de Usuario - Parcel Generator Enhanced

## [🚀] Introducción

Bienvenido al **Parcel Generator Enhanced**, una herramienta avanzada para la generación automatizada de parcelas de muestreo. Esta interfaz te permite configurar y ejecutar pipelines de procesamiento geoespacial de manera intuitiva.

### [🆕] **Nueva Funcionalidad: Soporte para Geodatabases**
La aplicación ahora incluye **soporte nativo para Geodatabases de Esri (.gdb)**, permitiendo seleccionar y trabajar con estos archivos de manera profesional. Las geodatabases se pueden seleccionar como cualquier otro archivo geoespacial.

---

## [🎯] Controles Principales de Ejecución

### Botones Centrales
- **[▶] Run Pipeline**: Ejecuta el pipeline con la configuración actual
- **[⏹] Stop**: Detiene la ejecución en curso
- **Barra de Progreso**: Muestra el avance en tiempo real

> **[💡] Tip**: Los controles están siempre visibles en la parte superior, no importa en qué tab te encuentres.

---

## [📁] **Selección de Archivos Mejorada**

### [🗂️] **Formatos de Archivo Soportados**
La aplicación soporta una amplia gama de formatos geoespaciales:

- **[📦] GeoPackage** (*.gpkg) - Formato recomendado
- **[📄] Shapefile** (*.shp) - Formato clásico
- **[🏛️] Geodatabase** (*.gdb) - **¡NUEVO!** Soporte completo para Esri Geodatabase
- **[🌐] GeoJSON** (*.geojson) - Formato web estándar
- **[🗺️] KML/KMZ** (*.kml) - Google Earth
- **[📋] GML** (*.gml) - Geography Markup Language

### [🎯] **Cómo Seleccionar Geodatabases (.gdb)**

#### **Método 1: Selección Directa**
1. Haz clic en cualquier botón **"Browse"** o **"Buscar"**
2. En el diálogo de archivos, busca las carpetas que terminan en `.gdb`
3. Si no ves la geodatabase que necesitas, **cancela el diálogo**

#### **Método 2: Selección Asistida** (Recomendado para .gdb)
1. Si cancelas el diálogo de archivos, aparecerá un mensaje:
   > **"¿Quiere seleccionar una Geodatabase (.gdb)?"**
2. Haz clic en **"Sí"**
3. Se abrirá un diálogo de carpetas especial para geodatabases
4. Navega y selecciona la carpeta `.gdb` que necesitas
5. La aplicación validará automáticamente que sea una geodatabase válida

#### **Validación Automática**
- ✅ La aplicación verifica que la carpeta seleccionada termine en `.gdb`
- ✅ Muestra mensaje de error si seleccionas una carpeta que no es geodatabase
- ✅ Compatible con todas las herramientas GDAL/OGR estándar

---

## [📑] Tabs de Configuración

### 1. [⚙] **Pipeline**
**Propósito**: Configuración básica del procesamiento

**Campos principales**:
- **Input File**: Archivo geoespacial de entrada
  - **Formatos soportados**: .gpkg, .shp, **.gdb**, .geojson, .kml, .gml
  - **Recomendado**: GeoPackage (.gpkg) para mejor rendimiento
  - **Geodatabases**: Usa el método de selección asistida para archivos .gdb
- **Output Directory**: Directorio donde se guardarán los resultados
- **Processing Style**: Estilo de procesamiento (calibration, control, custom)
- **Grouping Fields**: Campos por los cuales agrupar las parcelas

**Parámetros avanzados**:
- **Projected CRS (EPSG)**: Sistema de coordenadas proyectado (ej: 31982)
- **Min area (ha)**: Área mínima de parcelas en hectáreas
- **Buffer distance (m)**: Distancia de buffer (generalmente negativa)
- **Min distance between parcels (m)**: Distancia mínima entre parcelas

**Límites de parcelas**:
- **Minimum parcels**: Habilitar/configurar número mínimo de parcelas
- **Maximum parcels**: Habilitar/configurar número máximo de parcelas

**Identificación**:
- **Starting Parcel ID**: ID inicial para numeración de parcelas
- **Parcel Version**: Versión de las parcelas (ej: A, B, v1)

### 2. [📊] **Sampling Method**
**Propósito**: Configuración del método de muestreo

**Opciones disponibles**:

#### Método basado en CSV:
- **Use CSV**: Activa el uso de archivo CSV para definir cantidad de parcelas
- **CSV File**: Archivo con especificaciones de muestreo
- **Count Column**: Columna que contiene el número de parcelas
- **GridCode Column**: Columna con códigos de grid (opcional)
- **Field Mappings**: Mapeo de campos entre CSV y datos geoespaciales

#### Método basado en Intensidad:
- **Base Intensity**: Intensidad base de muestreo (%)
- **Use Specific Intensity**: Activar intensidades específicas por campo
- **Specific Intensities**: Configurar intensidades por tipo de uso

### 3. [#] **GridCode**
**Propósito**: Configuración de códigos de grid automáticos

**Funcionalidades**:
- **Enable GridCode**: Activa la generación automática de códigos
- **Field Configuration**: Configurar hasta 2 campos con bins personalizados
- **Bin Ranges**: Definir rangos de valores para cada código
- **Import/Export**: Guardar y cargar configuraciones de GridCode

### 4. [📋] **Plan Operative (PO)**
**Propósito**: Configuración del Plan Operativo

**Configuración**:
- **PO File**: Archivo geoespacial con el plan operativo
  - **Formatos soportados**: .gpkg, .shp, **.gdb**, .geojson
  - **Geodatabases**: Soporte completo para archivos .gdb con múltiples capas
- **Layer**: Capa específica dentro del archivo (para .gpkg y .gdb)
- **Fields**: Campos a incluir en el procesamiento
- **ID Mappings**: Mapeo de campos identificadores

### 5. [🚫] **Exclusion Layers**
**Propósito**: Definir capas de exclusión

**Opciones**:
- **Add Layer**: Agregar nueva capa de exclusión
  - **Formatos soportados**: .gpkg, .shp, **.gdb**, .geojson
  - **Geodatabases**: Selección de capas específicas dentro de .gdb
- **Buffer Distance**: Distancia de buffer para exclusión
- **Layer Management**: Editar, eliminar y reordenar capas

### 6. [📦] **Delivery**
**Propósito**: Configuración de entrega y nomenclatura

**Configuración**:
- **Delivery Code**: Código de entrega (ej: E01, E02)
- **Date**: Fecha de generación
- **Base Prefix**: Prefijo base para archivos
- **Custom Suffix**: Sufijo personalizado
- **Metadata**: Información adicional de la entrega

### 7. [⚏] **Column Order**
**Propósito**: Reordenar columnas del archivo final

**Funcionalidades**:
- **Load File**: Cargar archivo para reordenar
  - **Formatos soportados**: .gpkg, .shp, **.gdb**
  - **Geodatabases**: Selección automática de la primera capa disponible
- **Drag & Drop**: Reordenar columnas arrastrando
- **💾 Save Schema**: Guardar esquema de orden de columnas
  - Guarda orden, selección y configuraciones
  - Incluye metadatos del archivo fuente
  - Formato JSON reutilizable
- **📂 Load Schema**: Cargar esquema previamente guardado
  - Validación inteligente de compatibilidad
  - Mantiene solo columnas existentes
  - Agrega nuevas columnas al final
- **Geometry Position**: Controlar posición de columna geométrica
- **Apply Changes**: Aplicar nuevo orden de columnas

**💡 Uso de Esquemas**:
1. **Crear esquema**: Configura orden ideal y guarda con "Save Schema"
2. **Reutilizar**: En proyectos similares, usa "Load Schema" 
3. **Validación automática**: Solo aplica columnas que existen en el archivo actual
4. **Flexibilidad**: Nuevas columnas se agregan automáticamente al final

### 8. [⚙] **Configuration**
**Propósito**: Gestión de configuraciones y logs

**Opciones**:
- **Export Config**: Exportar configuración actual a JSON
- **Import Config**: Importar configuración desde JSON
- **Save Settings**: Guardar configuración de interfaz
- **Load Settings**: Cargar configuración guardada
- **Log Level**: Controlar nivel de detalle de logs

---

## [🔄] Flujo de Trabajo Recomendado

### Paso 1: Configuración Básica
1. Ve al tab **Pipeline**
2. Selecciona el **Input File**:
   - Para archivos .gpkg/.shp: Selección directa
   - **Para archivos .gdb**: Usa el método de selección asistida
3. Define el **Output Directory**
4. Selecciona el **Processing Style** apropiado

### Paso 2: Método de Muestreo
1. Ve al tab **Sampling Method**
2. Elige entre método CSV o por intensidad
3. Configura los parámetros según tu método elegido

### Paso 3: Configuraciones Adicionales
1. **GridCode**: Si necesitas códigos automáticos
2. **Plan Operative**: Si tienes un PO específico (soporta .gdb)
3. **Exclusion Layers**: Si hay áreas a excluir (soporta .gdb)
4. **Delivery**: Para nomenclatura de archivos

### Paso 4: Ejecución
1. Revisa la configuración en el tab **Pipeline**
2. Usa **"Show Complete Configuration Summary"** para verificar
3. Click en **[▶] Run Pipeline**
4. Monitorea el progreso en la barra y logs

### Paso 5: Post-procesamiento (Opcional)
1. Ve al tab **Column Order** si necesitas reordenar columnas
2. Usa **Configuration** para exportar tu configuración

---

## [💡] Tips y Mejores Prácticas

### [✓] Antes de Ejecutar
- **Verificar archivos**: Asegúrate de que todos los archivos de entrada existen y son accesibles
- **Geodatabases**: Para archivos .gdb, verifica que tengan las capas necesarias
- **Revisar configuración**: Usa el resumen de configuración para verificar parámetros
- **Guardar configuración**: Exporta tu configuración antes de ejecutar para futuras referencias

### [⚡] Durante la Ejecución
- **Monitorear logs**: Observa los mensajes para detectar problemas temprano
- **No cerrar aplicación**: Evita cerrar mientras el pipeline está ejecutándose
- **Usar Stop si necesario**: El botón Stop permite cancelar de forma segura

### [🎯] Optimización
- **Formato de archivos**: 
  - **GeoPackage (.gpkg)**: Mejor rendimiento general
  - **Geodatabase (.gdb)**: Ideal para datos complejos de Esri
  - **Shapefile (.shp)**: Para compatibilidad legacy
- **Grouping Fields**: Selecciona campos apropiados para optimizar agrupación
- **Buffer distances**: Ajusta según la resolución de tus datos
- **Intensidad de muestreo**: Balancea entre precisión y tiempo de procesamiento

### [🗂️] Trabajando con Geodatabases (.gdb)
- **Selección**: Usa el método de selección asistida para mejor experiencia
- **Capas múltiples**: La aplicación detecta automáticamente las capas disponibles
- **Compatibilidad**: Funciona con todas las versiones de ArcGIS geodatabases
- **Rendimiento**: Puede ser más lento que GeoPackage para datasets grandes

### [🔧] Solución de Problemas
- **Errores de archivo**: Verifica rutas y permisos de archivos
- **Geodatabases corruptas**: Verifica la integridad con ArcGIS o usa `ogrinfo` para diagnosticar
- **Memoria insuficiente**: Reduce área de procesamiento o aumenta RAM
- **Errores de CRS**: Asegúrate de usar el EPSG correcto para tu región

---

## [📁] Estructura de Archivos de Salida

```
output_directory/
├── results/
│   ├── YYYYMMDD_CODIGO_PARCELAS_FINALES.gpkg
│   └── YYYYMMDD_CODIGO_PARCELAS_FINALES_ordenada.gpkg (si se reordenó)
├── logs/
│   └── pipeline_TIMESTAMP.log
├── summary/
│   └── execution_summary.json
└── config/
    └── YYYYMMDD_CODIGO_pipeline_config_executed.json
```

---

## [🆘] Soporte y Resolución de Problemas

### Errores Comunes

#### "No quedan registros después de filtrar"
- **Causa**: Los filtros son muy restrictivos
- **Solución**: Revisa configuración de PO y tipos de uso de suelo

#### "DataSourceError" o "No such file or directory"
- **Causa**: Archivos no encontrados o sin permisos
- **Solución**: Verifica rutas de archivos y permisos de directorio

#### "ImportError" o "ModuleNotFoundError"
- **Causa**: Dependencias faltantes
- **Solución**: Instala requirements: `pip install -r requirements.txt`

#### **Errores específicos de Geodatabase (.gdb)**
- **"Cannot open .gdb file"**:
  - **Causa**: Geodatabase corrupta o versión incompatible
  - **Solución**: Verifica con ArcGIS o usa `ogrinfo` para diagnosticar

- **"No layers found in .gdb"**:
  - **Causa**: Geodatabase vacía o sin permisos de lectura
  - **Solución**: Verifica contenido con herramientas GIS

- **"Selected folder is not a Geodatabase"**:
  - **Causa**: Carpeta seleccionada no termina en .gdb
  - **Solución**: Selecciona una carpeta que termine en .gdb

### Información de Debug
- **Log Level**: Cambia a "DEBUG" en el tab Configuration para más detalles
- **Export Config**: Guarda configuración problemática para análisis
- **Clear Logs**: Limpia logs antes de nueva ejecución para claridad

---

## [📞] Contacto y Ayuda

Para soporte adicional:
- Revisa los logs detallados en modo DEBUG
- Exporta tu configuración para compartir problemas
- Consulta la documentación técnica del proyecto

---

## [📝] Registro de Cambios

### **Versión Enhanced v1.1** (Actual)
- ✅ **Soporte completo para Geodatabases (.gdb)**
- ✅ Selección asistida de archivos .gdb
- ✅ Validación automática de geodatabases
- ✅ Integración en todos los diálogos de selección de archivos
- ✅ Compatibilidad con herramientas GDAL/OGR
- ✅ Conservación de archivos de configuración temporal
- ✅ Mejoras en el manejo de procesos y logs

---

*Última actualización: Diciembre 2024*
*Versión: Enhanced v1.1* 