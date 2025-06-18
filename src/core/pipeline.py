# src/core/pipeline.py

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
    gridcode_column_csv: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ejecuta todo el pipeline de generación de parcelas.
    """
    def report_progress(value, status):
        if progress_callback:
            progress_callback(value, status)
        logger.info(f"Progreso: {value}% - {status}")

    report_progress(0, "Inicializando...")
    cfg = get_config(estilo, cfg_overrides)

    if "CAPAS_EXCLUSION" in cfg and cfg["CAPAS_EXCLUSION"]:
        cfg["CAPAS_EXCLUSION"] = normalize_exclusion_layers(cfg["CAPAS_EXCLUSION"])

    rutas = configurar_rutas(input_path, output_dir, delivery_config)
    setup_logging(rutas['log_file'])
    logger.info(f"=== Iniciando proceso con estilo '{estilo}' ===")
    if cfg_overrides:
        logger.debug(f"Overrides aplicados: {cfg_overrides}")
    
    # Log delivery configuration if provided
    if delivery_config:
        logger.debug(f"Delivery configuration: {delivery_config}")

    report_progress(5, "Configurando...")
    resultados = {'rutas': rutas, 'config': cfg}

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

    report_progress(10, "Cargando datos de entrada...")
    gdf = pyogrio.read_dataframe(rutas['input'])
    gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
    gdf = verificar_y_transformar_crs(gdf, "entrada", cfg['PROJECTED_CRS'])
    gdf.columns = gdf.columns.str.lower()
    
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
        report_progress(20, "Calculando gridcode...")
        # Asegurarse que el nombre de la columna de gridcode también esté en minúsculas si se crea
        gridcode_params = cfg.get("GRIDCODE_PARAMS")
        gdf = calcular_gridcode(
            gdf, 
            cfg["USE_GRIDCODE"], 
            {k: v.lower() for k, v in cfg["CAMPOS_METRICAS"].items()},
            gridcode_params
        )
        
        # NUEVO: Guardar grilla con gridcode calculado (antes del dissolve)
        if cfg["USE_GRIDCODE"] and 'gridcode' in gdf.columns:
            logger.info(f"Guardando grilla con gridcode en: {rutas['gpkg_gridcode']}")
            pyogrio.write_dataframe(gdf, rutas['gpkg_gridcode'], layer='grilla_gridcode')
            logger.info(f"Grilla con gridcode guardada: {len(gdf)} registros")

    # --- Determinar las columnas de agrupación ---
    grouping_cols = []
    # [CORRECCIÓN CLAVE] Forzar a minúsculas aquí para asegurar consistencia
    if grouping_fields:
        grouping_cols = [col.lower() for col in grouping_fields]
        logger.info(f"Usando campos de agrupación personalizados desde la GUI: {grouping_cols}")
    else:
        default_fields = [col.lower() for col in cfg["FIELDS"]]
        logger.info(f"Usando campos de agrupación por defecto del estilo '{estilo}': {default_fields}")
        grouping_cols = default_fields

    if cfg["USE_GRIDCODE"] and 'gridcode' in gdf.columns:
        if 'gridcode' not in grouping_cols:
            grouping_cols.append('gridcode')

    if use_csv:
        report_progress(22, "Generando áreas agrupadas (modo CSV)...")
        logger.info(f"Usando modo CSV. Generando áreas intermedias antes de aplicar CSV...")
        
        # PASO 1: Generar áreas agrupadas (SIN intensidad porque el CSV define las parcelas)
        logger.info("Modo CSV: Deshabilitando intensidad - las parcelas se definen por CSV")
        gdf_areas_agrupadas = calcular_cantidad_de_parcelas(
            gdf=gdf, fields=grouping_cols, intensidad=0,  # Intensidad = 0 cuando hay CSV
            use_intensidad_especifica=False,  # No usar intensidad específica
            intensidad_por_campo={},  # Vacío
            min_parcelas=cfg["MIN_PARCELAS"], max_parcelas=cfg["MAX_PARCELAS"],
            area_minima_ha=cfg["AREA_MINIMA_HA"], buffer_distance=cfg["BUFFER_DISTANCE"],
            output_csv=rutas['csv_resumen'], output_gpkg=rutas['gpkg_areas'],
            output_gpkg_dissolved_initial=rutas['gpkg_inicial']
        )
        
        # Cargar las áreas generadas
        resultados['gdf_inicial'] = gpd.read_file(rutas['gpkg_inicial'], engine='pyogrio')
        resultados['gdf_post_filtros'] = gpd.read_file(rutas['gpkg_areas'], engine='pyogrio')
        
        # CONTINUAR con el flujo normal (sin aplicar CSV aún)
        gdf_para_generar = gdf_areas_agrupadas
        
    else:
        if 2 in op:
            report_progress(25, "Calculando cantidad de parcelas por intensidad...")
            gdf_para_generar = calcular_cantidad_de_parcelas(
                gdf=gdf, fields=grouping_cols, intensidad=cfg["INTENSIDAD"],
                use_intensidad_especifica=cfg["USE_INTENSIDAD_ESPECIFICA"],
                intensidad_por_campo=cfg["INTENSIDAD_POR_CAMPO"],
                min_parcelas=cfg["MIN_PARCELAS"], max_parcelas=cfg["MAX_PARCELAS"],
                area_minima_ha=cfg["AREA_MINIMA_HA"], buffer_distance=cfg["BUFFER_DISTANCE"],
                output_csv=rutas['csv_resumen'], output_gpkg=rutas['gpkg_areas'],
                output_gpkg_dissolved_initial=rutas['gpkg_inicial']
            )
            resultados['gdf_inicial'] = gpd.read_file(rutas['gpkg_inicial'], engine='pyogrio')
            resultados['gdf_post_filtros'] = gpd.read_file(rutas['gpkg_areas'], engine='pyogrio')
        else:

            gdf_para_generar = gdf.copy()
            gdf_para_generar['n_parcelas'] = 0

    gdf_post_exclusion = gdf_para_generar
    if 3 in op:
        # Verificar si hay capas de exclusión configuradas
        capas_exclusion = cfg.get("CAPAS_EXCLUSION", [])
        
        if not capas_exclusion or len(capas_exclusion) == 0:
            logger.info("No hay capas de exclusión configuradas. Saltando paso de exclusiones.")
            report_progress(40, "Saltando exclusiones (no configuradas)...")
            gdf_post_exclusion = gdf_para_generar.copy()
            
            # Agregar columna de área para consistencia con el flujo normal
            if 'area_m2' not in gdf_post_exclusion.columns:
                gdf_post_exclusion['area_m2'] = gdf_post_exclusion.geometry.area
            if 'area_ha_post_exclusion' not in gdf_post_exclusion.columns:
                gdf_post_exclusion['area_ha_post_exclusion'] = gdf_post_exclusion['area_m2'] / 10000
            
            # Guardar archivo para mantener consistencia del pipeline
            if rutas.get('gpkg_exclusion'):
                logger.debug(f"Guardando datos sin exclusiones en: {rutas['gpkg_exclusion']}")
                pyogrio.write_dataframe(gdf_post_exclusion, rutas['gpkg_exclusion'], layer='areas_post_exclusion')
            
            resultados['gdf_post_exclusion'] = gdf_post_exclusion
        else:
            # Verificar que las capas tienen rutas válidas
            capas_validas = [c for c in capas_exclusion if c.get('ruta') and c.get('ruta').strip()]
            
            if not capas_validas:
                logger.info("Las capas de exclusión configuradas no tienen rutas válidas. Saltando paso.")
                report_progress(40, "Saltando exclusiones (rutas inválidas)...")
                gdf_post_exclusion = gdf_para_generar.copy()
                
                # Agregar columna de área para consistencia
                if 'area_m2' not in gdf_post_exclusion.columns:
                    gdf_post_exclusion['area_m2'] = gdf_post_exclusion.geometry.area
                if 'area_ha_post_exclusion' not in gdf_post_exclusion.columns:
                    gdf_post_exclusion['area_ha_post_exclusion'] = gdf_post_exclusion['area_m2'] / 10000
                
                # Guardar archivo para mantener consistencia
                if rutas.get('gpkg_exclusion'):
                    pyogrio.write_dataframe(gdf_post_exclusion, rutas['gpkg_exclusion'], layer='areas_post_exclusion')
                
                resultados['gdf_post_exclusion'] = gdf_post_exclusion
            else:
                logger.info(f"Aplicando {len(capas_validas)} capas de exclusión válidas...")
                report_progress(40, "Aplicando exclusiones...")
                
                try:
                    gdf_post_exclusion = aplicar_exclusiones(
                        gdf=gdf_para_generar, capas_exclusion=capas_exclusion,
                        fields=grouping_cols, crs_target=cfg["PROJECTED_CRS"],
                        output_gpkg=rutas['gpkg_exclusion']
                    )
                    resultados['gdf_post_exclusion'] = gdf_post_exclusion
                    logger.info("Exclusiones aplicadas exitosamente.")
                except Exception as e:
                    logger.error(f"Error aplicando exclusiones: {e}")
                    logger.warning("Continuando sin aplicar exclusiones...")
                    gdf_post_exclusion = gdf_para_generar.copy()
                    
                    # Agregar columnas para consistencia
                    if 'area_m2' not in gdf_post_exclusion.columns:
                        gdf_post_exclusion['area_m2'] = gdf_post_exclusion.geometry.area
                    if 'area_ha_post_exclusion' not in gdf_post_exclusion.columns:
                        gdf_post_exclusion['area_ha_post_exclusion'] = gdf_post_exclusion['area_m2'] / 10000
                    
                    resultados['gdf_post_exclusion'] = gdf_post_exclusion
    else:
        logger.debug("Paso de exclusiones deshabilitado en la configuración.")
        gdf_post_exclusion = gdf_para_generar
    
    # [NUEVO] APLICAR CSV DESPUÉS DE EXCLUSIONES
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
        
        for col in grouping_cols:
            if col not in df_csv.columns: 
                raise ValueError(f"Columna de agrupación '{col}' no encontrada en el CSV. Columnas disponibles: {list(df_csv.columns)}")
            if col not in gdf_post_exclusion.columns: 
                raise ValueError(f"Columna de agrupación '{col}' no encontrada en las áreas post-exclusión.")

        df_csv[count_col] = pd.to_numeric(df_csv[count_col], errors='coerce').fillna(0).astype(int)
        
        # NUEVO: Manejar mapeo de gridcode del CSV si está especificado
        if gridcode_column_csv and gridcode_column_csv in df_csv.columns and 'gridcode' in grouping_cols:
            logger.info(f"Usando columna '{gridcode_column_csv}' del CSV como gridcode")
            # Renombrar la columna del CSV para que coincida con 'gridcode'
            if gridcode_column_csv != 'gridcode':
                df_csv = df_csv.rename(columns={gridcode_column_csv: 'gridcode'})
                logger.debug(f"Columna '{gridcode_column_csv}' renombrada a 'gridcode' en el CSV")
        
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
    
    puntos_gdf = None
    if 4 in op:
        report_progress(55, "Generando parcelas (puntos)...")
        puntos_gdf = generar_parcelas(
            gdf=gdf_post_exclusion, group_cols=grouping_cols,
            min_distance=cfg["MIN_DISTANCE"], output_path=rutas['gpkg_parcelas']
        )
        resultados['puntos_gdf'] = puntos_gdf
        
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
        
    if 6 in op and poligonos_gdf is not None and not poligonos_gdf.empty:
        report_progress(85, "Asignando atributos PO...")
        poligonos_gdf_final = asignar_atributos_po(
            parcelas_gdf=poligonos_gdf, po_config=cfg.get("PO_CONFIG", {}),
            crs_target=cfg["PROJECTED_CRS"], output_path=rutas['gpkg_final'], # Guardar directamente el final
            entrega=entrega
        )
        resultados['gdf_final'] = poligonos_gdf_final
    else:
        resultados['gdf_final'] = poligonos_gdf

    # [CORRECCIÓN 2] El paso 7 se elimina completamente.
    # La lógica de reordenar y guardar el archivo final ahora está
    # dentro de la nueva función 'asignar_atributos_po'.

    if resultados.get('gdf_inicial') is not None:
        report_progress(95, "Analizando pérdidas...")
        analisis_df = analizar_perdidas_parcelas(
            gdf_inicial=resultados['gdf_inicial'], fields=grouping_cols,
            gdf_post_filtros=resultados.get('gdf_post_filtros'),
            gdf_post_exclusion=resultados.get('gdf_post_exclusion'),
            gdf_final=resultados.get('gdf_final'),
            output_csv=rutas['csv_analisis']
        )
        resultados['analisis'] = analisis_df

    report_progress(100, "Proceso completado con éxito!")
    logging.info("=== Proceso completado con éxito ===")

    return resultados