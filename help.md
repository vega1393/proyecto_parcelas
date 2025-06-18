# [📋] Manual de Usuario - Parcel Generator Enhanced

## [🚀] Introducción

Bienvenido al **Parcel Generator Enhanced**, una herramienta avanzada para la generación automatizada de parcelas de muestreo. Esta interfaz te permite configurar y ejecutar pipelines de procesamiento geoespacial de manera intuitiva.

---

## [🎯] Controles Principales de Ejecución

### Botones Centrales
- **[▶] Run Pipeline**: Ejecuta el pipeline con la configuración actual
- **[⏹] Stop**: Detiene la ejecución en curso
- **Barra de Progreso**: Muestra el avance en tiempo real

> **[💡] Tip**: Los controles están siempre visibles en la parte superior, no importa en qué tab te encuentres.

---

## [📑] Tabs de Configuración

### 1. [⚙] **Pipeline**
**Propósito**: Configuración básica del procesamiento

**Campos principales**:
- **Input File**: Archivo GeoPackage (.gpkg) o Shapefile (.shp) de entrada
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

### 4. [📋] **Plan Operative (PO)**
**Propósito**: Configuración del Plan Operativo

**Configuración**:
- **PO File**: Archivo GeoPackage con el plan operativo
- **Layer**: Capa específica dentro del archivo
- **Fields**: Campos a incluir en el procesamiento
- **ID Mappings**: Mapeo de campos identificadores

### 5. [🚫] **Exclusion Layers**
**Propósito**: Definir capas de exclusión

**Opciones**:
- **Add Layer**: Agregar nueva capa de exclusión
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
- **Drag & Drop**: Reordenar columnas arrastrando
- **Geometry Position**: Controlar posición de columna geométrica
- **Apply Changes**: Aplicar nuevo orden de columnas

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
2. Selecciona el **Input File** (archivo .gpkg o .shp)
3. Define el **Output Directory**
4. Selecciona el **Processing Style** apropiado

### Paso 2: Método de Muestreo
1. Ve al tab **Sampling Method**
2. Elige entre método CSV o por intensidad
3. Configura los parámetros según tu método elegido

### Paso 3: Configuraciones Adicionales
1. **GridCode**: Si necesitas códigos automáticos
2. **Plan Operative**: Si tienes un PO específico
3. **Exclusion Layers**: Si hay áreas a excluir
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
- **Revisar configuración**: Usa el resumen de configuración para verificar parámetros
- **Guardar configuración**: Exporta tu configuración antes de ejecutar para futuras referencias

### [⚡] Durante la Ejecución
- **Monitorear logs**: Observa los mensajes para detectar problemas temprano
- **No cerrar aplicación**: Evita cerrar mientras el pipeline está ejecutándose
- **Usar Stop si necesario**: El botón Stop permite cancelar de forma segura

### [🎯] Optimización
- **Grouping Fields**: Selecciona campos apropiados para optimizar agrupación
- **Buffer distances**: Ajusta según la resolución de tus datos
- **Intensidad de muestreo**: Balancea entre precisión y tiempo de procesamiento

### [🔧] Solución de Problemas
- **Errores de archivo**: Verifica rutas y permisos de archivos
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
    └── YYYYMMDD_CODIGO_pipeline_config.json
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

*Última actualización: Junio 2025*
*Versión: Enhanced v1.0* 