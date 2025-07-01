"""
Constantes del proyecto de generación de parcelas.

Este archivo centraliza todos los números mágicos y valores hardcodeados
para facilitar el mantenimiento y documentar su propósito.
"""

# =============================================================================
# CONSTANTES DE ÁREA Y GEOMETRÍA
# =============================================================================

# Área mínima de píxel en metros cuadrados
# Usado en: src/pipeline/calculo_parcelas.py línea 81
# Propósito: Filtrar píxeles muy pequeños que pueden ser ruido
# Impacto: Valores menores incluyen más píxeles pequeños
# NOTA: Ahora configurable desde la GUI (Pipeline Tab → Min pixel area)
AREA_MINIMA_PIXEL_M2 = 399

# Área de parcela por defecto en metros cuadrados
# Usado en: src/config/config_base.py línea 36
# Propósito: Tamaño objetivo de cada parcela generada
# Impacto: Afecta el número total de parcelas generadas
# NOTA: Ahora configurable desde la GUI (Pipeline Tab → Parcel area)
AREA_PARCELA_DEFAULT_M2 = 400

# Altura mínima p95 para filtrar píxeles de baja vegetación
# Usado en: src/pipeline/calculo_parcelas.py línea 96
# Propósito: Filtrar píxeles con vegetación muy baja
# Impacto: Valores menores incluyen más píxeles de baja altura
# NOTA: Ahora configurable desde la GUI (Pipeline Tab → Min p95 height)
MIN_P95_HEIGHT_DEFAULT = 2.0

# =============================================================================
# VALORES DE RELLENO Y DATOS FALTANTES
# =============================================================================

# Valor de relleno para datos NaN en cálculos
# Usado en: src/pipeline/calculo_parcelas.py línea 74
# Propósito: Reemplazar valores NaN en métricas para evitar errores
# Impacto: Debe ser un valor que no interfiera con los cálculos
VALOR_RELLENO_NAN = -9999

# =============================================================================
# CÓDIGOS EPSG POR DEFECTO
# =============================================================================

# Sistema de coordenadas por defecto para Chile (UTM 18S)
# Usado en: src/config/config_base.py línea 19
# Propósito: Proyección por defecto para cálculos geométricos
# Nota: La interfaz permite sobrescribir este valor
EPSG_DEFAULT_CHILE = 32718

# Sistema de coordenadas para Brasil (SIRGAS 2000 UTM 22S)
# Usado en: src/json_config/test_custom.json línea 22
# Propósito: Proyección para proyectos en Brasil
# Nota: La interfaz permite sobrescribir este valor
EPSG_BRASIL_SIRGAS = 31982

# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

# Formato de fecha para archivos de log
# Usado en: src/utils/logging_utils.py
# Propósito: Formato estándar para timestamps en logs
FORMATO_FECHA_LOG = "%Y%m%d_%H%M%S"

# Nivel de logging por defecto
# Usado en: múltiples archivos
# Propósito: Controlar verbosidad de los logs
NIVEL_LOG_DEFAULT = "INFO"

# =============================================================================
# CONSTANTES DE VALIDACIÓN
# =============================================================================

# Número mínimo de registros para procesar
# Propósito: Evitar procesamiento de datasets vacíos o muy pequeños
MIN_REGISTROS_VALIDOS = 1

# Número máximo de bins para GridCode
# Propósito: Limitar complejidad de clasificación
MAX_BINS_GRIDCODE = 10

# =============================================================================
# CONFIGURACIÓN DE ARCHIVOS
# =============================================================================

# Extensiones de archivo soportadas para datos geoespaciales
EXTENSIONES_GEO_SOPORTADAS = ['.gpkg', '.shp', '.gdb']

# Extensión por defecto para archivos de salida
EXTENSION_SALIDA_DEFAULT = '.gpkg'

# Nombre del archivo de configuración de GUI
ARCHIVO_CONFIG_GUI = "gui_settings.json"

# =============================================================================
# NOTAS DE MANTENIMIENTO
# =============================================================================

"""
IMPORTANTE PARA MANTENIMIENTO FUTURO:

1. **AREA_MINIMA_PIXEL_M2 (399)**: 
   - AHORA CONFIGURABLE desde GUI (Pipeline Tab → Min pixel area)
   - Valores menores: más píxeles incluidos, posibles falsos positivos
   - Valores mayores: menos píxeles, posibles falsos negativos

2. **VALOR_RELLENO_NAN (-9999)**:
   - NUNCA usar 0 o valores positivos que puedan confundirse con datos reales
   - Debe ser un valor claramente identificable como "sin dato"

3. **EPSG_DEFAULT_CHILE/BRASIL**:
   - Solo cambiar si hay cambios en estándares nacionales
   - Siempre verificar compatibilidad con datos de entrada

4. **AREA_PARCELA_DEFAULT_M2 (400)**:
   - AHORA CONFIGURABLE desde GUI (Pipeline Tab → Parcel area)
   - Afecta directamente el número de parcelas generadas
   
5. **MIN_P95_HEIGHT_DEFAULT (2.0)**:
   - AHORA CONFIGURABLE desde GUI (Pipeline Tab → Min p95 height)
   - Filtra píxeles con vegetación muy baja

CÓMO USAR ESTAS CONSTANTES:
```python
from src.config.constants import AREA_MINIMA_PIXEL_M2, VALOR_RELLENO_NAN

# En lugar de:
gdf_filtered = gdf[gdf.geometry.area >= 399]

# Usar:
gdf_filtered = gdf[gdf.geometry.area >= AREA_MINIMA_PIXEL_M2]
```
""" 