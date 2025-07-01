# 🔧 GUÍA DE MANTENIMIENTO DEL PIPELINE

## 📋 RESUMEN EJECUTIVO

Esta guía está diseñada para desarrolladores que necesiten **modificar o debuggear** el pipeline de generación de parcelas (`src/core/pipeline.py`). El archivo contiene ~600 líneas de lógica compleja pero bien estructurada.

## 🎯 MODIFICACIONES FRECUENTES

### 1. **Añadir Nuevos Filtros** (Frecuencia: Mensual)
```python
# Ubicación: src/config/config_base.py o src/config/estilos.py
"FILTROS_CAMPOS": {
    "tipouso": ["EUGR", "EUUG", "EUUR"],  # ← Modificar aquí
    "apl": filtrar_apl,                   # ← O añadir nuevos filtros
    "nuevo_campo": ["valor1", "valor2"]   # ← Ejemplo de nuevo filtro
}
```

### 2. **Configurar Nuevas Capas de Exclusión** (Frecuencia: Ocasional)
```python
# Ubicación: src/config/config_base.py
"CAPAS_EXCLUSION": [
    {
        "ruta": r"C:\path\to\nueva_capa.shp",
        "capa": None,  # Para SHP, usar None
        "descripcion": "Descripción de la nueva capa"
    },
    {
        "ruta": r"C:\path\to\geodatabase.gdb", 
        "capa": "nombre_capa",  # Para GDB, especificar capa
        "descripcion": "Capa desde geodatabase"
    }
]
```

### 3. **Modificar Parámetros de Intensidad** (Frecuencia: Ocasional)
```python
# Ubicación: src/config/estilos.py
"INTENSIDAD_POR_CAMPO": {
    "tipouso": {
        "EUGR": 0.5,  # ← Modificar intensidades
        "EUUG": 0.3,
        "EUUR": 0.2
    }
}
```

## 🗺️ MAPA DE NAVEGACIÓN DEL CÓDIGO

### Estructura del Pipeline (`src/core/pipeline.py`)

| Líneas | Etapa | Descripción | Modificaciones Comunes |
|--------|-------|-------------|----------------------|
| 104-129 | **Carga y Filtrado** | Carga datos, aplica filtros | Nuevos tipos de filtros |
| 133-337 | **GridCode + Guardado** | Calcula códigos, guardado robusto | Parámetros de gridcode |
| 338-427 | **Cálculo Parcelas** | 3 modos: Normal/CSV/Total | Lógica de distribución |
| **ARCHIVOS GENERADOS** | **gpkg_inicial** = Áreas agrupadas COMPLETAS (todos los píxeles) | **gpkg_areas** = Áreas DESPUÉS de filtros píxeles + área + buffer |
| 430-441 | **Exclusiones** | Aplica capas de exclusión | Nuevas capas exclusión |
| 445-584 | **Aplicación CSV** | Merge complejo con CSV | Mapeo de columnas |
| 585-605 | **Generación** | Puntos y polígonos | Parámetros geométricos |
| 607-637 | **PO + Análisis** | Atributos y pérdidas | Configuración PO |
| **CORRECCIÓN CRÍTICA** | **gpkg_po** usa POLÍGONOS (no puntos) | Mejor intersección espacial con PO |

### Archivos de Configuración Relacionados

| Archivo | Propósito | Modificaciones Típicas |
|---------|-----------|----------------------|
| `src/config/config_base.py` | Configuración base | Rutas, filtros, exclusiones |
| `src/config/estilos.py` | Estilos específicos | Intensidades, parámetros |
| `gui_settings.json` | Configuración UI | GridCode, campos métricos |

## 🚨 PUNTOS CRÍTICOS DE MANTENIMIENTO

### 1. **Normalización de Campos** (CRÍTICO)
```python
# SIEMPRE mantener esta línea en la carga de datos:
gdf.columns = gdf.columns.str.lower()

# Y en configuración de campos:
{k: v.lower() for k, v in cfg["CAMPOS_METRICAS"].items()}
```

### 2. **Guardado Robusto** (líneas 244-337)
- **NO MODIFICAR** sin entender completamente
- Sistema de 4 fallbacks para problemas de I/O
- Crítico para estabilidad del pipeline

### 3. **Merge CSV** (líneas 445-584)
- Lógica compleja de harmonización de tipos
- Análisis pre/post merge
- **Testear exhaustivamente** cualquier cambio

### 4. **Variables de Estado** 
```python
# Variables que se pasan entre etapas - MANEJAR CON CUIDADO:
gdf                  # Datos iniciales filtrados
gdf_para_generar     # Post-cálculo de parcelas
gdf_post_exclusion   # Post-exclusiones
puntos_gdf          # Parcelas como puntos
poligonos_gdf       # Parcelas como polígonos
parcelas_con_po     # Con atributos PO
```

## 🧪 PROTOCOLO DE TESTING

### Antes de Modificar
1. **Backup del código actual**
2. **Ejecutar pipeline completo** con datos de prueba
3. **Documentar resultados esperados**

### Después de Modificar
1. **Testing con datos pequeños** primero
2. **Verificar logs** para errores/warnings
3. **Comparar resultados** con versión anterior
4. **Testing con datos reales** solo si paso anterior exitoso

### Casos de Prueba Críticos
- **Modo Normal**: Intensidad estándar
- **Modo CSV**: Con archivo CSV válido
- **Modo Total-Based**: Distribución proporcional
- **Con Exclusiones**: Múltiples capas de exclusión
- **GridCode**: Habilitado y deshabilitado

## 🔍 DEBUGGING COMÚN

### 1. **Error: "Campo no encontrado"**
```bash
# Verificar normalización de campos
# Problema: Campos en mayúsculas vs minúsculas
# Solución: Verificar que gdf.columns.str.lower() se ejecute
```

### 5. **Confusión: "Áreas inicial y filtradas iguales"**
```bash
# CORREGIDO: Había error conceptual en el flujo
# gpkg_inicial = Áreas agrupadas COMPLETAS (dissolve sobre TODOS los píxeles)
# gpkg_areas = Áreas después de filtros píxeles + área mínima + buffer
# Problema: Se hacía dissolve sobre píxeles ya filtrados
# Solución: Hacer dissolve inicial sobre gdf_processed (todos los píxeles)
```

### 6. **Error: "Archivo PO contiene puntos en lugar de polígonos"**
```bash
# CORREGIDO: Error crítico en asignación de atributos PO
# Problema: Se usaba puntos_gdf en lugar de poligonos_gdf
# gpkg_po = Polígonos con atributos PO (mejor intersección espacial)
# Solución: Cambiar parcelas_gdf=puntos_gdf por parcelas_gdf=poligonos_gdf
```

### 7. **Actualización: Constantes ahora configurables desde GUI**
```bash
# MEJORADO: Números mágicos ahora son configurables
# Pipeline Tab → Area and Distance Parameters:
#   • Min pixel area (m²): 399 → Filtro de píxeles pequeños
#   • Min p95 height: 2.0 → Filtro de vegetación baja  
#   • Parcel area (m²): 400 → Tamaño objetivo de parcelas
# Archivo: src/config/constants.py (documentación)
# Beneficio: Usuarios pueden ajustar sin modificar código
```

### 8. **Limpieza: Eliminados campos de metadata no utilizados**
```bash
# LIMPIADO: Eliminados campos de metadata del Delivery Tab
# Campos removidos: description, version, operator, timestamp
# Motivo: Solo se almacenaban, no se usaban en el pipeline
# Beneficio: Interfaz más limpia y enfocada en funcionalidad real
```

### 2. **Error: "No quedan registros después de filtros"**
```bash
# Verificar filtros en configuración
# Problema: Valores de filtro no coinciden con datos
# Solución: Usar diálogo "Load Types from Plan Operativo"
```

### 3. **Error: "Merge CSV fallido"**
```bash
# Verificar columnas de agrupación
# Problema: Tipos de datos inconsistentes
# Solución: Revisar harmonización en líneas 445-584
```

### 4. **Error: "Guardado GPKG fallido"**
```bash
# El sistema de fallbacks debería manejarlo
# Si falla completamente: problema de permisos o espacio
# Verificar logs para detalles específicos
```

## 📈 MEJORAS FUTURAS PLANIFICADAS

### Prioridad Alta (Próximas modificaciones)
- [ ] Extraer `_robust_save_geodataframe()` como función helper
- [ ] Extraer `_apply_csv_counts()` para simplificar merge
- [ ] Añadir validación de inputs más robusta

### Prioridad Media (Cuando haya más tiempo)
- [ ] Extraer `_setup_grouping_columns()` 
- [ ] Crear tests de integración específicos
- [ ] Documentar casos edge conocidos

### Prioridad Baja (Mejoras arquitectónicas)
- [ ] Considerar refactorización por etapas (si hay 1+ mes disponible)
- [ ] Implementar sistema de plugins para nuevos filtros
- [ ] Cache inteligente para re-ejecuciones

## 🆘 CONTACTOS Y RECURSOS

### Cuando Necesites Ayuda
1. **Logs del pipeline**: Revisar `output/logs/pipeline.log`
2. **Configuración actual**: Exportar desde UI antes de modificar
3. **Datos de prueba**: Usar datasets pequeños para debugging
4. **Rollback**: Mantener backup del código funcionando

### Archivos de Referencia
- `CHANGELOG.md`: Historial de cambios
- `README.md`: Documentación general
- `help.md`: Guía de usuario
- Este archivo: Guía de mantenimiento técnico

---

**RECUERDA**: El pipeline actual funciona correctamente. Cualquier modificación debe preservar esta estabilidad mientras mejora la funcionalidad específica requerida. 