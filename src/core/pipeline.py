# src/core/pipeline.py

"""
Pipeline principal para generación de parcelas geoespaciales.

ARQUITECTURA DEL PIPELINE:
==========================

FLUJO PRINCIPAL (7 etapas configurables):
1. [ETAPA 1] Carga y Filtrado Inicial (líneas ~104-129)
2. [ETAPA 2] Cálculo GridCode + Guardado Robusto (líneas ~133-337) 
3. [ETAPA 3] Cálculo de Parcelas (3 modos) (líneas ~338-427)
4. [ETAPA 4] Exclusiones Geográficas (líneas ~430-441)
5. [ETAPA 5] Aplicación CSV Post-Exclusión (líneas ~445-584)
6. [ETAPA 6] Generación Parcelas + Polígonos (líneas ~585-605)
7. [ETAPA 7] Asignación PO + Análisis (líneas ~607-637)

MODOS DE OPERACIÓN:
==================
- NORMAL: Intensidad fija por tipo de uso
- CSV: Conteos desde archivo externo (post-exclusiones)
- TOTAL-BASED: Distribución proporcional de total fijo

VARIABLES DE ESTADO CRÍTICAS:
============================
- gdf: Datos iniciales filtrados
- gdf_para_generar: Post-cálculo de parcelas  
- gdf_post_exclusion: Post-exclusiones geográficas
- puntos_gdf: Parcelas generadas (puntos)
- poligonos_gdf: Parcelas como polígonos
- parcelas_con_po: Parcelas con atributos PO

PUNTOS DE MANTENIMIENTO FRECUENTE:
=================================
- Configuración de filtros (cfg["FILTROS_CAMPOS"])
- Parámetros de intensidad (cfg["INTENSIDAD_POR_CAMPO"]) 
- Rutas de capas de exclusión (cfg["CAPAS_EXCLUSION"])
- Configuración PO (cfg["PO_CONFIG"])

GUARDADO ROBUSTO (líneas ~244-337):
==================================
Sistema de 4 fallbacks para problemas de I/O:
1. pyogrio directo
2. geopandas fallback  
3. guardado por lotes
4. eliminación de registros problemáticos

MERGE CSV COMPLEJO (líneas ~445-584):
====================================
Lógica crítica para aplicación de conteos CSV:
- Harmonización de tipos de datos
- Análisis pre/post merge
- Identificación de grupos faltantes
- Limpieza de columnas extra

TODO - MEJORAS FUTURAS (cuando haya más tiempo):
===============================================
- [ ] Extraer función _robust_save_geodataframe()
- [ ] Extraer función _apply_csv_counts()  
- [ ] Extraer función _setup_grouping_columns()
- [ ] Añadir validación de inputs más robusta
- [ ] Crear tests de integración específicos
"""

import logging
import os
import geopandas as gpd
import pyogrio
import pandas as pd
from typing import Dict, Any, Optional, List, Callable

# --- Módulos del proyecto ---
from src.utils.logging_utils import setup_logging
from src.utils.geo_utils import verificar_y_transformar_crs
from src.config.config_base import get_config
from src.io.rutas import configurar_rutas
from src.pipeline.filtros import aplicar_filtros_iniciales, calcular_gridcode
from src.pipeline.calculo_parcelas import calcular_cantidad_de_parcelas
from src.pipeline.exclusiones import aplicar_exclusiones
from src.pipeline.generacion_parcelas import generar_parcelas, generar_poligonos_parcelas
from src.pipeline.atributos_po import asignar_atributos_po
from src.pipeline.analisis import analizar_perdidas_parcelas

logger = logging.getLogger(__name__)

def normalize_exclusion_layers(layers: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normaliza las claves de las capas de exclusión para compatibilidad interna."""
    if not layers:
        return []
    normalized = []
    for layer in layers:
        norm = {
            "ruta": layer.get("path") or layer.get("ruta"),
            "capa": layer.get("layer") or layer.get("capa"),
            "descripcion": layer.get("description") or layer.get("descripcion")
        }
        normalized.append(norm)
    return normalized

def ejecutar_proceso(
    input_path: str,
    output_dir: Optional[str] = None,
    entrega: Optional[str] = None,
    estilo: str = "calibracion",
    cfg_overrides: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    use_csv: bool = False,
    csv_path: Optional[str] = None,
    grouping_fields: Optional[List[str]] = None,
    delivery_config: Optional[Dict[str, Any]] = None,
    gridcode_column_csv: Optional[str] = None,
    # Nuevos parámetros para total-based
    use_total: bool = False,
    total_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Ejecuta todo el pipeline de generación de parcelas.
    
    PIPELINE FLOW:
    ==============
    1. Setup inicial y configuración
    2. Carga de datos y filtrado inicial  
    3. Cálculo de gridcode (con guardado robusto)
    4. Cálculo de cantidad de parcelas (3 modos)
    5. Aplicación de exclusiones geográficas
    6. Aplicación de conteos CSV (si aplica)
    7. Generación de parcelas (puntos)
    8. Generación de polígonos
    9. Asignación de atributos PO
    10. Análisis de pérdidas
    
    Args:
        input_path: Ruta al archivo de entrada (grilla de píxeles)
        output_dir: Directorio de salida 
        estilo: Estilo de configuración (calibration/control/custom)
        cfg_overrides: Sobrescribir parámetros de configuración
        progress_callback: Función para reportar progreso
        use_csv: Si usar conteos desde CSV
        csv_path: Ruta al archivo CSV de conteos
        grouping_fields: Campos de agrupación personalizados
        delivery_config: Configuración de entrega
        gridcode_column_csv: Mapeo de columna gridcode en CSV
        use_total: Si usar modo total-based
        total_config: Configuración para modo total-based
        
    Returns:
        Dict con resultados del pipeline y rutas de archivos generados
        
    Raises:
        FileNotFoundError: Si el archivo de entrada no existe
        ValueError: Si la configuración es inválida
        RuntimeError: Si falla alguna etapa crítica del pipeline
    """
    def report_progress(value, status):
        if progress_callback:
            progress_callback(value, status)
        logger.info(f"Progreso: {value}% - {status}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # ETAPA 0: SETUP INICIAL Y CONFIGURACIÓN
    # ═══════════════════════════════════════════════════════════════════════════════
    report_progress(0, "Inicializando...")
    cfg = get_config(estilo, cfg_overrides)

    if "CAPAS_EXCLUSION" in cfg and cfg["CAPAS_EXCLUSION"]:
        cfg["CAPAS_EXCLUSION"] = normalize_exclusion_layers(cfg["CAPAS_EXCLUSION"])

    if delivery_config is None:
        delivery_config = {}

    # Configuración de rutas de salida
    rutas = configurar_rutas(input_path, output_dir, delivery_config)
    
    setup_logging(rutas['log_file'])
    logger.info(f"=== Iniciando proceso con estilo '{estilo}' ===")
    logger.info(f"Logging configured. Log file: {rutas['log_file']}")
    if cfg_overrides:
        logger.debug(f"Overrides aplicados: {cfg_overrides}")
    
    # Log delivery configuration if provided
    if delivery_config:
        logger.debug(f"Delivery configuration: {delivery_config}")

    report_progress(5, "Configurando...")
    resultados = {'rutas': rutas, 'config': cfg}

    # Inicializar variables de DataFrames que se pasarán entre etapas
    areas_dissolved = None
    gdf_exclusiones = None
    puntos_parcelas = None
    poligonos_gdf = None
    parcelas_con_po = None
    
    # Log información sobre los filtros que se van a aplicar
    filtros_campos = cfg.get("FILTROS_CAMPOS", {})
    if filtros_campos:
        logger.info("=== FILTROS CONFIGURADOS ===")
        for campo, filtro in filtros_campos.items():
            if callable(filtro):
                logger.info(f"Campo '{campo}': Función personalizada")
            else:
                logger.info(f"Campo '{campo}': {filtro}")
        logger.info("=" * 30)

        # ═══════════════════════════════════════════════════════════════════════════════
        # ETAPA 1: CARGA DE DATOS Y FILTRADO INICIAL
        # ═══════════════════════════════════════════════════════════════════════════════
        report_progress(10, "Cargando datos de entrada...")
        gdf = pyogrio.read_dataframe(rutas['input'])
        gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
        gdf = verificar_y_transformar_crs(gdf, "entrada", cfg['PROJECTED_CRS'])
        gdf.columns = gdf.columns.str.lower()  # NORMALIZACIÓN CRÍTICA: todo a minúsculas
    
        report_progress(15, "Aplicando filtros iniciales...")
        try:
            gdf = aplicar_filtros_iniciales(gdf, cfg["FILTROS_CAMPOS"])
        except ValueError as e:
            logger.error(f"Error en filtros iniciales: {str(e)}")
            logger.error("SUGERENCIAS PARA SOLUCIONAR EL PROBLEMA:")
            logger.error("1. Verifique que los tipos de uso configurados coincidan con los datos reales")
            logger.error("2. Use el diálogo 'Load Types from Plan Operativo' para cargar tipos automáticamente")
            logger.error("3. Revise la configuración de filtros en el tab Pipeline")
            logger.error("4. Asegúrese de que el Plan Operativo esté correctamente configurado")
            raise ValueError(f"Error en filtros iniciales: {str(e)}\n\n"
                           f"SUGERENCIAS:\n"
                           f"• Verifique que los tipos de uso configurados coincidan con los datos reales\n"
                           f"• Use el diálogo 'Load Types from Plan Operativo' para cargar tipos automáticamente\n"
                           f"• Revise la configuración de filtros en el tab Pipeline\n"
                           f"• Asegúrese de que el Plan Operativo esté correctamente configurado")
        except Exception as e:
            logger.error(f"Error inesperado en filtros iniciales: {str(e)}")
            raise
        
        op = cfg["OPCIONES_ACTIVAS"]
        
        if 1 in op:
            # ═══════════════════════════════════════════════════════════════════════════════
            # ETAPA 2: CÁLCULO DE GRIDCODE + GUARDADO ROBUSTO
            # ═══════════════════════════════════════════════════════════════════════════════
            report_progress(20, "Calculando gridcode...")
            gridcode_params = cfg.get("GRIDCODE_PARAMS")
            gdf = calcular_gridcode(
                gdf, 
                cfg["USE_GRIDCODE"], 
                {k: v.lower() for k, v in cfg["CAMPOS_METRICAS"].items()},  # NORMALIZACIÓN
                gridcode_params
            )
            
            # Save grid with calculated gridcode (before dissolve)
            if cfg["USE_GRIDCODE"] and 'gridcode' in gdf.columns:
                logger.info(f"Guardando grilla con gridcode en: {rutas['gpkg_gridcode']}")
                
                # === DIAGNÓSTICO DETALLADO DEL PROBLEMA FID ===
                logger.info("=== INICIANDO DIAGNÓSTICO DETALLADO ===")
                
                # 1. Información del GeoDataFrame original
                logger.info(f"📊 GeoDataFrame original:")
                logger.info(f"   - Tamaño: {len(gdf)} registros")
                logger.info(f"   - Columnas: {list(gdf.columns)}")
                logger.info(f"   - Tipo de índice: {type(gdf.index)}")
                logger.info(f"   - Rango de índice: {gdf.index.min()} a {gdf.index.max()}")
                logger.info(f"   - ¿Índice único?: {gdf.index.is_unique}")
                
                # 2. Verificar si hay columnas problemáticas
                problematic_cols = []
                if 'fid' in gdf.columns:
                    problematic_cols.append('fid')
                    fid_unique = gdf['fid'].is_unique if gdf['fid'].notna().any() else True
                    logger.warning(f"⚠️  Columna 'fid' detectada: únicos={fid_unique}, nulos={gdf['fid'].isna().sum()}")
                
                for col in ['objectid', 'id', 'feature_id']:
                    if col in gdf.columns:
                        problematic_cols.append(col)
                        logger.warning(f"⚠️  Columna potencialmente problemática detectada: '{col}'")
                
                # 3. Análisis específico del registro problemático (10335)
                problematic_index = 10335
                if problematic_index < len(gdf):
                    logger.info(f"🔍 Analizando registro problemático (índice {problematic_index}):")
                    prob_record = gdf.iloc[problematic_index]
                    logger.info(f"   - Geometría válida: {prob_record.geometry.is_valid if prob_record.geometry else False}")
                    logger.info(f"   - Área: {prob_record.geometry.area if prob_record.geometry else 'N/A'}")
                    if 'fid' in prob_record:
                        logger.info(f"   - FID: {prob_record['fid']}")
                    if 'gridcode' in prob_record:
                        logger.info(f"   - GridCode: {prob_record['gridcode']}")
                else:
                    logger.info(f"🔍 Índice problemático {problematic_index} fuera de rango")
                
                # 4. Buscar duplicados potenciales
                if 'fid' in gdf.columns:
                    fid_duplicates = gdf['fid'].duplicated().sum()
                    if fid_duplicates > 0:
                        logger.error(f"❌ {fid_duplicates} FIDs duplicados encontrados!")
                        dup_fids = gdf[gdf['fid'].duplicated()]['fid'].head(5).tolist()
                        logger.error(f"   Ejemplos de FIDs duplicados: {dup_fids}")
                
                # === LIMPIEZA ROBUSTA DEL GEODATAFRAME ===
                logger.info("🧹 Iniciando limpieza robusta del GeoDataFrame...")
                
                try:
                    # 1. Crear copia limpia
                    gdf_clean = gdf.copy()
                    
                    # 2. Eliminar columnas problemáticas que pueden causar conflictos FID
                    columns_to_remove = ['fid', 'objectid', 'feature_id']
                    removed_cols = []
                    for col in columns_to_remove:
                        if col in gdf_clean.columns:
                            gdf_clean = gdf_clean.drop(columns=[col])
                            removed_cols.append(col)
                    
                    if removed_cols:
                        logger.info(f"✅ Columnas problemáticas eliminadas: {removed_cols}")
                    
                    # 3. Resetear índice completamente
                    gdf_clean = gdf_clean.reset_index(drop=True)
                    logger.info(f"✅ Índice reseteado: nuevo rango 0 a {len(gdf_clean)-1}")
                    
                    # 4. Validar geometrías
                    invalid_geoms = ~gdf_clean.geometry.is_valid
                    if invalid_geoms.any():
                        invalid_count = invalid_geoms.sum()
                        logger.warning(f"⚠️  {invalid_count} geometrías inválidas detectadas, reparando...")
                        gdf_clean.geometry = gdf_clean.geometry.buffer(0)  # Reparar geometrías
                        
                        # Verificar reparación
                        still_invalid = ~gdf_clean.geometry.is_valid
                        if still_invalid.any():
                            logger.warning(f"⚠️  {still_invalid.sum()} geometrías siguen inválidas después de reparar")
                            # Filtrar geometrías que no se pudieron reparar
                            gdf_clean = gdf_clean[gdf_clean.geometry.is_valid].copy()
                            logger.info(f"✅ Filtrado a {len(gdf_clean)} registros con geometrías válidas")
                    
                    # 5. Eliminar registros con geometrías nulas o vacías
                    null_geoms = gdf_clean.geometry.isna() | gdf_clean.geometry.is_empty
                    if null_geoms.any():
                        null_count = null_geoms.sum()
                        logger.warning(f"⚠️  {null_count} geometrías nulas/vacías eliminadas")
                        gdf_clean = gdf_clean[~null_geoms].copy()
                    
                    # 6. Verificar que el registro problemático ya no esté
                    logger.info(f"📊 GeoDataFrame limpio:")
                    logger.info(f"   - Tamaño final: {len(gdf_clean)} registros")
                    logger.info(f"   - Columnas finales: {list(gdf_clean.columns)}")
                    logger.info(f"   - Reducción: {len(gdf) - len(gdf_clean)} registros eliminados")
                    
                    # === GUARDADO ROBUSTO ===
                    logger.info("💾 Iniciando guardado robusto...")
                    
                    # Eliminar archivo existente de forma robusta
                    if os.path.exists(rutas['gpkg_gridcode']):
                        try:
                            os.remove(rutas['gpkg_gridcode'])
                            logger.debug(f"✅ Archivo GPKG existente eliminado: {rutas['gpkg_gridcode']}")
                        except Exception as e:
                            logger.warning(f"⚠️  No se pudo eliminar archivo existente: {e}")
                            # Intentar con nombre alternativo
                            import time
                            timestamp = int(time.time())
                            alt_path = rutas['gpkg_gridcode'].replace('.gpkg', f'_backup_{timestamp}.gpkg')
                            try:
                                os.rename(rutas['gpkg_gridcode'], alt_path)
                                logger.info(f"✅ Archivo existente renombrado a: {alt_path}")
                            except Exception as e2:
                                logger.error(f"❌ No se pudo renombrar archivo: {e2}")
                    
                    # Método 1: Intentar con pyogrio (método preferido)
                    success = False
                    try:
                        pyogrio.write_dataframe(gdf_clean, rutas['gpkg_gridcode'], layer='grilla_gridcode')
                        logger.info(f"✅ Grilla con gridcode guardada (pyogrio): {len(gdf_clean)} registros")
                        success = True
                    except Exception as e:
                        logger.warning(f"⚠️  Error con pyogrio: {e}")
                        logger.warning(f"  - Fallback 1: Guardando con geopandas...")
                    
                    # Método 2: Fallback con geopandas si pyogrio falla
                    if not success:
                        try:
                            gdf_clean.to_file(rutas['gpkg_gridcode'], layer='grilla_gridcode', driver='GPKG')
                            logger.info(f"✅ Grilla con gridcode guardada (geopandas): {len(gdf_clean)} registros")
                            success = True
                        except Exception as e:
                            logger.warning(f"⚠️  Error con geopandas: {e}")
                    
                    # Método 3: Guardado por lotes si los anteriores fallan
                    if not success:
                        logger.info("🔄 Intentando guardado por lotes...")
                        batch_size = 1000
                        total_batches = (len(gdf_clean) + batch_size - 1) // batch_size
                        
                        for i in range(0, len(gdf_clean), batch_size):
                            batch = gdf_clean.iloc[i:i+batch_size].copy()
                            batch_num = (i // batch_size) + 1
                            
                            try:
                                if i == 0:  # Primera batch, crear archivo
                                    pyogrio.write_dataframe(batch, rutas['gpkg_gridcode'], layer='grilla_gridcode')
                                else:  # Batches siguientes, append (si pyogrio lo soporta)
                                    # Usar geopandas para append
                                    batch.to_file(rutas['gpkg_gridcode'], layer='grilla_gridcode', driver='GPKG', mode='a')
                                
                                logger.debug(f"📦 Batch {batch_num}/{total_batches} guardada ({len(batch)} registros)")
                            except Exception as e:
                                logger.error(f"❌ Error en batch {batch_num}: {e}")
                                # Si falla una batch, abortar el método por lotes
                                break
                        else:
                            # Si todas las batches se guardaron exitosamente
                            logger.info(f"✅ Grilla guardada por lotes: {len(gdf_clean)} registros en {total_batches} batches")
                            success = True
                    
                    # Método 4: Último recurso - guardar sin la fila problemática
                    if not success:
                        logger.warning("🚨 Último recurso: eliminando registros problemáticos...")
                        # Eliminar el registro que estaba causando problemas
                        safe_gdf = gdf_clean.copy()
                        if len(safe_gdf) > problematic_index:
                            safe_gdf = safe_gdf.drop(safe_gdf.index[problematic_index:problematic_index+100])  # Eliminar rango problemático
                            logger.info(f"⚠️  Eliminados registros del rango problemático. Registros restantes: {len(safe_gdf)}")
                            
                            try:
                                pyogrio.write_dataframe(safe_gdf, rutas['gpkg_gridcode'], layer='grilla_gridcode')
                                logger.info(f"✅ Grilla guardada (modo seguro): {len(safe_gdf)} registros")
                                success = True
                            except Exception as e:
                                logger.error(f"❌ Fallback 3 fallido. No se pudo guardar la grilla: {e}")
                    
                    if not success:
                        logger.error("❌ TODOS los métodos de guardado fallaron")
                        logger.info("ℹ️  Continuando pipeline sin guardar grilla intermedia...")
                        # No hacer raise, continuar con el pipeline
                    
                    logger.info("=== DIAGNÓSTICO COMPLETADO ===")
                    
                except Exception as e:
                    logger.error(f"❌ Error en diagnóstico/limpieza: {e}")
                    logger.info("ℹ️  Continuando pipeline sin guardar grilla intermedia...")
                    # No hacer raise, continuar con el pipeline

        # ═══════════════════════════════════════════════════════════════════════════════
        # CONFIGURACIÓN DE CAMPOS DE AGRUPACIÓN
        # ═══════════════════════════════════════════════════════════════════════════════
        grouping_cols = []
        # NORMALIZACIÓN CRÍTICA: Forzar a minúsculas para consistencia
        if grouping_fields:
            grouping_cols = [col.lower() for col in grouping_fields]
            logger.info(f"Usando campos de agrupación personalizados desde la GUI: {grouping_cols}")
        else:
            default_fields = [col.lower() for col in cfg["FIELDS"]]
            logger.info(f"Usando campos de agrupación por defecto del estilo '{estilo}': {default_fields}")
            grouping_cols = default_fields

        # Añadir gridcode si está habilitado y disponible
        if cfg["USE_GRIDCODE"] and 'gridcode' in gdf.columns:
            if 'gridcode' not in grouping_cols:
                grouping_cols.append('gridcode')

        if use_csv:
            # ═══════════════════════════════════════════════════════════════════════════════
            # ETAPA 3A: CÁLCULO DE PARCELAS - MODO CSV (PREPARACIÓN)
            # ═══════════════════════════════════════════════════════════════════════════════
            report_progress(22, "Generando áreas agrupadas (modo CSV)...")
            logger.info(f"Usando modo CSV. Generando áreas intermedias antes de aplicar CSV...")
            
            # PASO 1: Generar áreas agrupadas (SIN intensidad porque el CSV define las parcelas)
            logger.info("Modo CSV: Deshabilitando intensidad - las parcelas se definen por CSV")
            gdf_areas_agrupadas, _ = calcular_cantidad_de_parcelas(
                gdf=gdf, fields=grouping_cols, intensidad=0,  # Intensidad = 0 cuando hay CSV
                use_intensidad_especifica=False,  # No usar intensidad específica
                intensidad_por_campo={},  # Vacío
                min_parcelas=cfg["MIN_PARCELAS"], max_parcelas=cfg["MAX_PARCELAS"],
                area_minima_ha=cfg["AREA_MINIMA_HA"], buffer_distance=cfg["BUFFER_DISTANCE"],
                output_csv=rutas['csv_resumen'], output_gpkg=rutas['gpkg_areas'],
                output_gpkg_dissolved_initial=rutas['gpkg_inicial'],
                # Parámetros total-based (no aplicables en modo CSV)
                use_total_based=False,
                total_parcels=None,
                minimum_config=None,
                use_original_area=True,
                cfg=cfg  # Pasar configuración para constantes
            )
            
            # Cargar las áreas generadas
            resultados['gdf_inicial'] = gpd.read_file(rutas['gpkg_inicial'], engine='pyogrio')
            resultados['gdf_post_filtros'] = gpd.read_file(rutas['gpkg_areas'], engine='pyogrio')
            
            # CONTINUAR con el flujo normal (sin aplicar CSV aún)
            gdf_para_generar = gdf_areas_agrupadas
            
        else:
            if 2 in op:
                if use_total:
                    # ═══════════════════════════════════════════════════════════════════════════════
                    # ETAPA 3B: CÁLCULO DE PARCELAS - MODO TOTAL-BASED
                    # ═══════════════════════════════════════════════════════════════════════════════
                    report_progress(25, "Calculando distribución proporcional de parcelas...")
                    # Configurar parámetros total-based
                    total_parcels = total_config.get("total_parcels", 800) if total_config else 800
                    minimum_config = {
                        "type": total_config.get("minimum_type", "none") if total_config else "none",
                        "value": total_config.get("minimum_value", 0.0) if total_config else 0.0
                    }
                    use_original_area = total_config.get("use_original_area", True) if total_config else True
                    
                    gdf_para_generar, areas_dissolved = calcular_cantidad_de_parcelas(
                        gdf=gdf, fields=grouping_cols, intensidad=cfg["INTENSIDAD"],
                        use_intensidad_especifica=cfg["USE_INTENSIDAD_ESPECIFICA"],
                        intensidad_por_campo=cfg["INTENSIDAD_POR_CAMPO"],
                        min_parcelas=cfg["MIN_PARCELAS"], max_parcelas=cfg["MAX_PARCELAS"],
                        area_minima_ha=cfg["AREA_MINIMA_HA"], buffer_distance=cfg["BUFFER_DISTANCE"],
                        output_csv=rutas['csv_resumen'], output_gpkg=rutas['gpkg_areas'],
                        output_gpkg_dissolved_initial=rutas['gpkg_inicial'],
                        # Parámetros total-based
                        use_total_based=True,
                        total_parcels=total_parcels,
                        minimum_config=minimum_config,
                        use_original_area=use_original_area,
                        campos_metricas=cfg.get("CAMPOS_METRICAS"),
                        cfg=cfg  # Pasar configuración para constantes
                    )
                else:
                    # ═══════════════════════════════════════════════════════════════════════════════
                    # ETAPA 3C: CÁLCULO DE PARCELAS - MODO NORMAL (INTENSIDAD)
                    # ═══════════════════════════════════════════════════════════════════════════════
                    report_progress(25, "Calculando cantidad de parcelas por intensidad...")
                    gdf_para_generar = calcular_cantidad_de_parcelas(
                        gdf=gdf, fields=grouping_cols, intensidad=cfg["INTENSIDAD"],
                        use_intensidad_especifica=cfg["USE_INTENSIDAD_ESPECIFICA"],
                        intensidad_por_campo=cfg["INTENSIDAD_POR_CAMPO"],
                        min_parcelas=cfg["MIN_PARCELAS"], max_parcelas=cfg["MAX_PARCELAS"],
                        area_minima_ha=cfg["AREA_MINIMA_HA"], buffer_distance=cfg["BUFFER_DISTANCE"],
                        output_csv=rutas['csv_resumen'], output_gpkg=rutas['gpkg_areas'],
                        output_gpkg_dissolved_initial=rutas['gpkg_inicial'],
                        # Parámetros total-based (no aplicables en modo normal)
                        use_total_based=False,
                        total_parcels=None,
                        minimum_config=None,
                        use_original_area=True,
                        cfg=cfg  # Pasar configuración para constantes
                    )
                resultados['gdf_inicial'] = gpd.read_file(rutas['gpkg_inicial'], engine='pyogrio')
                resultados['gdf_post_filtros'] = gpd.read_file(rutas['gpkg_areas'], engine='pyogrio')
            else:
                gdf_para_generar = gdf.copy()
                gdf_para_generar['n_parcelas'] = 0

        # ═══════════════════════════════════════════════════════════════════════════════
        # ETAPA 4: EXCLUSIONES GEOGRÁFICAS
        # ═══════════════════════════════════════════════════════════════════════════════
        gdf_post_exclusion = gdf_para_generar
        if 3 in op and cfg["CAPAS_EXCLUSION"]:
            report_progress(40, "Aplicando exclusiones geográficas...")
            gdf_post_exclusion = aplicar_exclusiones(
                gdf=gdf_para_generar,
                capas_exclusion=cfg["CAPAS_EXCLUSION"],
                fields=grouping_cols,
                crs_target=cfg["PROJECTED_CRS"],
                output_gpkg=rutas['gpkg_exclusion']
            )
            resultados['gdf_post_exclusion'] = gdf_post_exclusion
        else:
            logger.debug("Paso de exclusiones deshabilitado en la configuración.")
            gdf_post_exclusion = gdf_para_generar
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # ETAPA 5: APLICACIÓN DE CONTEOS CSV (POST-EXCLUSIÓN)
        # ═══════════════════════════════════════════════════════════════════════════════
        # NOTA: Esta etapa incluye lógica compleja de merge con análisis detallado
        if use_csv:
            report_progress(45, "Aplicando conteos desde CSV post-exclusión...")
            logger.info(f"Aplicando conteos desde CSV: {csv_path}")
            
            # Validar y leer CSV
            if not csv_path or not os.path.exists(csv_path):
                raise FileNotFoundError(f"Archivo CSV de entrada no encontrado en: {csv_path}")

            df_csv = pd.read_csv(csv_path)
            df_csv.columns = [c.lower() for c in df_csv.columns]
            logger.debug(f"CSV leído exitosamente. Columnas: {list(df_csv.columns)}")
            
            count_col = 'n_parcelas' if 'n_parcelas' in df_csv.columns else ('n' if 'n' in df_csv.columns else None)
            if count_col is None:
                raise ValueError(f"El CSV debe contener una columna llamada 'n' o 'n_parcelas'. Columnas encontradas: {list(df_csv.columns)}")
            
            # NUEVO: Manejar mapeo de gridcode del CSV si está especificado ANTES de verificar columnas
            if gridcode_column_csv and gridcode_column_csv in df_csv.columns and 'gridcode' in grouping_cols:
                logger.info(f"Usando columna '{gridcode_column_csv}' del CSV como gridcode")
                # Renombrar la columna del CSV para que coincida con 'gridcode'
                if gridcode_column_csv != 'gridcode':
                    df_csv = df_csv.rename(columns={gridcode_column_csv: 'gridcode'})
                    logger.debug(f"Columna '{gridcode_column_csv}' renombrada a 'gridcode' en el CSV")
            
            # Verificar que todas las columnas de agrupación existan después del mapeo
            for col in grouping_cols:
                if col not in df_csv.columns: 
                    raise ValueError(f"Columna de agrupación '{col}' no encontrada en el CSV. Columnas disponibles: {list(df_csv.columns)}")
                if col not in gdf_post_exclusion.columns: 
                    raise ValueError(f"Columna de agrupación '{col}' no encontrada en las áreas post-exclusión.")

            df_csv[count_col] = pd.to_numeric(df_csv[count_col], errors='coerce').fillna(0).astype(int)
            
            # Harmonizar tipos de datos para el merge
            for col in grouping_cols:
                if col in gdf_post_exclusion.columns and col in df_csv.columns:
                    # Si gridcode o cualquier columna numérica, convertir ambas a string para merge consistente
                    if col == 'gridcode' or gdf_post_exclusion[col].dtype in ['int64', 'float64'] or df_csv[col].dtype in ['int64', 'float64']:
                        gdf_post_exclusion[col] = gdf_post_exclusion[col].astype(str)
                        df_csv[col] = df_csv[col].astype(str)
                        logger.debug(f"Harmonizando tipos para columna '{col}': convertido a string para merge")
            
            # Merge con CSV (reemplaza n_parcelas con el del CSV)
            logger.debug(f"Intentando merge entre {len(gdf_post_exclusion)} grupos post-exclusión y {len(df_csv)} filas del CSV")
            logger.debug(f"Columnas de agrupación para merge: {grouping_cols}")
            
            # Debug: mostrar algunos ejemplos de cada DataFrame
            logger.debug(f"Primeras 3 filas post-exclusión: {gdf_post_exclusion[grouping_cols].head(3).to_dict('records')}")
            logger.debug(f"Primeras 3 filas del CSV: {df_csv[grouping_cols].head(3).to_dict('records')}")
            
            # MEJORADO: Análisis antes del merge
            grupos_gdf = len(gdf_post_exclusion)
            grupos_csv = len(df_csv)
            logger.info(f"MERGE ANALYSIS:")
            logger.info(f"   - Grupos en GDF post-exclusion: {grupos_gdf}")
            logger.info(f"   - Grupos en CSV: {grupos_csv}")
            logger.info(f"   - Total parcelas en CSV: {df_csv[count_col].sum()}")
            
            # NUEVO: Análisis detallado de valores únicos antes del merge
            logger.info(f"MERGE DEBUG - Valores únicos en GDF:")
            for col in grouping_cols:
                if col in gdf_post_exclusion.columns:
                    unique_vals = sorted(gdf_post_exclusion[col].unique())
                    logger.info(f"   - {col}: {unique_vals[:10]}{'...' if len(unique_vals) > 10 else ''}")
            
            logger.info(f"MERGE DEBUG - Valores únicos en CSV:")
            for col in grouping_cols:
                if col in df_csv.columns:
                    unique_vals = sorted(df_csv[col].unique())
                    logger.info(f"   - {col}: {unique_vals[:10]}{'...' if len(unique_vals) > 10 else ''}")
            
            gdf_post_exclusion = gdf_post_exclusion.merge(df_csv, on=grouping_cols, how="left")
            logger.debug(f"Resultado del merge: {len(gdf_post_exclusion)} filas")
            
            # NUEVO: Análisis post-merge
            grupos_con_csv = gdf_post_exclusion[count_col].notna().sum() if count_col in gdf_post_exclusion.columns else 0
            grupos_sin_csv = grupos_gdf - grupos_con_csv
            logger.info(f"MERGE RESULTS:")
            logger.info(f"   - Grupos que coincidieron con CSV: {grupos_con_csv}")
            logger.info(f"   - Grupos sin datos del CSV: {grupos_sin_csv}")
            
            # NUEVO: Identificar grupos faltantes del CSV
            csv_groups = set()
            gdf_groups = set()
            
            for _, row in df_csv.iterrows():
                group_tuple = tuple(str(row[col]) for col in grouping_cols)
                csv_groups.add(group_tuple)
            
            for _, row in gdf_post_exclusion.iterrows():
                group_tuple = tuple(str(row[col]) for col in grouping_cols if col in gdf_post_exclusion.columns)
                gdf_groups.add(group_tuple)
            
            missing_from_gdf = csv_groups - gdf_groups
            if missing_from_gdf:
                logger.warning(f"GRUPOS DEL CSV NO ENCONTRADOS EN GDF ({len(missing_from_gdf)}):")
                for group in missing_from_gdf:
                    group_str = " | ".join([f"{grouping_cols[i]}:{group[i]}" for i in range(len(group))])
                    logger.warning(f"   - {group_str}")
            
            if grupos_sin_csv > 0:
                logger.warning(f"ADVERTENCIA: {grupos_sin_csv} grupos del GDF no tienen correspondencia en el CSV")
                logger.warning(f"ADVERTENCIA: Estos grupos se procesaran con n_parcelas=0 (no se generaran parcelas)")
            
            # Verificar si el merge fue exitoso y manejar columnas
            if f"{count_col}_y" in gdf_post_exclusion.columns:
                # Merge exitoso con sufijos automáticos
                logger.debug("Merge exitoso detectado (con sufijos _x, _y)")
                gdf_post_exclusion['n_parcelas'] = gdf_post_exclusion[f"{count_col}_y"].fillna(0).astype(int)
                gdf_post_exclusion = gdf_post_exclusion.drop(columns=[f"{count_col}_x", f"{count_col}_y"], errors='ignore')
            elif count_col in gdf_post_exclusion.columns and count_col != 'n_parcelas':
                # El CSV tenía una columna diferente a n_parcelas
                logger.debug(f"Usando columna '{count_col}' del CSV como n_parcelas")
                gdf_post_exclusion['n_parcelas'] = gdf_post_exclusion[count_col].fillna(0).astype(int)
            elif 'n_parcelas' in gdf_post_exclusion.columns:
                # Ya existe n_parcelas
                logger.debug("Columna 'n_parcelas' actualizada desde CSV")
            else:
                # Si no existe la columna, crear con valores por defecto
                logger.warning(f"No se pudo aplicar CSV. Creando n_parcelas con valor 1 por defecto.")
                gdf_post_exclusion['n_parcelas'] = 1
            
            # NUEVO: Reporte final del merge
            total_parcelas_finales = gdf_post_exclusion['n_parcelas'].sum()
            grupos_activos = (gdf_post_exclusion['n_parcelas'] > 0).sum()
            logger.info(f"FINAL CSV APPLICATION:")
            logger.info(f"   - Total parcelas a generar: {total_parcelas_finales}")
            logger.info(f"   - Grupos activos (n_parcelas>0): {grupos_activos}")
            logger.info(f"   - Diferencia con CSV original: {df_csv[count_col].sum() - total_parcelas_finales}")
            
            # Limpiar columnas extra del CSV que no necesitamos
            csv_extra_cols = [col for col in gdf_post_exclusion.columns if col.endswith('_y') or col in ['area_ha_y', 'area_m2_y', 'intensidad_y']]
            if csv_extra_cols:
                gdf_post_exclusion = gdf_post_exclusion.drop(columns=csv_extra_cols, errors='ignore')
                logger.debug(f"Columnas extra del CSV eliminadas: {csv_extra_cols}")
            
            logger.info(f"CSV aplicado exitosamente. {len(gdf_post_exclusion)} grupos con n_parcelas desde CSV.")
            resultados['gdf_post_exclusion'] = gdf_post_exclusion
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # ETAPA 6: GENERACIÓN DE PARCELAS (PUNTOS)
        # ═══════════════════════════════════════════════════════════════════════════════
        puntos_gdf = None
        if 4 in op:
            report_progress(55, "Generando parcelas (puntos)...")
            puntos_gdf = generar_parcelas(
                gdf=gdf_post_exclusion, group_cols=grouping_cols,
                min_distance=cfg["MIN_DISTANCE"], output_path=rutas['gpkg_parcelas']
            )
            resultados['puntos_gdf'] = puntos_gdf
            
        # ═══════════════════════════════════════════════════════════════════════════════
        # ETAPA 7: GENERACIÓN DE POLÍGONOS
        # ═══════════════════════════════════════════════════════════════════════════════
        poligonos_gdf = None
        if 5 in op and puntos_gdf is not None and not puntos_gdf.empty:
            report_progress(70, "Generando polígonos...")
            poligonos_gdf = generar_poligonos_parcelas(
                points_gdf=puntos_gdf, area_parcela=cfg["AREA_PARCELA"],
                id_parcela_inicio=cfg["ID_PARCELA_INICIO"],
                version_parcela=cfg["VERSION_PARCELA"], fields=grouping_cols,
                output_path=rutas['gpkg_poligonos']
            )
            resultados['poligonos_gdf'] = poligonos_gdf
        else:
            resultados['poligonos_gdf'] = poligonos_gdf # Mantener como None si no se generaron
            
        # ═══════════════════════════════════════════════════════════════════════════════
        # ETAPA 8: ASIGNACIÓN DE ATRIBUTOS DEL PLAN OPERATIVO
        # ═══════════════════════════════════════════════════════════════════════════════
        parcelas_con_po = None  # INICIALIZACIÓN CLAVE para análisis posterior
        if 6 in op and poligonos_gdf is not None and not poligonos_gdf.empty:
            report_progress(85, "Asignando atributos PO...")
            # Recuperar configuración de entrega para el nombre de archivo
            delivery_code = delivery_config.get('code', 'D01') if delivery_config else 'D01'
            parcel_suffix = delivery_config.get('suffix', 'control') if delivery_config else 'control'
            
            # CORREGIDO: Usar polígonos en lugar de puntos para atributos PO
            parcelas_con_po = asignar_atributos_po(
                parcelas_gdf=poligonos_gdf,  # ✅ Usar polígonos para mejor intersección espacial
                po_config=cfg['PO_CONFIG'],
                crs_target=cfg['PROJECTED_CRS'],
                output_path=rutas['gpkg_po'],
                entrega=delivery_code
            )
        else:
            if 6 in op:
                logger.warning("No se generaron polígonos de parcelas, saltando asignación de atributos PO.")
            
            # ═══════════════════════════════════════════════════════════════════════════════
            # ETAPA 9: ANÁLISIS DE PÉRDIDAS
            # ═══════════════════════════════════════════════════════════════════════════════
            if 7 in op:
                report_progress(95, "Analizando pérdidas...")
                # IMPORTANTE: Usa 'gdf_para_generar' que contiene la columna 'n_parcelas'
                if gdf_para_generar is not None and not gdf_para_generar.empty and parcelas_con_po is not None and not parcelas_con_po.empty:
                    analizar_perdidas_parcelas(
                        gdf_calculado=gdf_para_generar,
                        fields=grouping_cols,
                        gdf_generado=parcelas_con_po,
                        output_csv=rutas['csv_analisis']
                    )
                else:
                    logger.warning("No se generaron parcelas o falta el GDF de cálculo, saltando análisis de pérdidas.")

        report_progress(100, "Proceso completado con éxito!")
        logger.info("✓ Proceso completado exitosamente")

    return resultados