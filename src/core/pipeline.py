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
    grouping_fields: Optional[List[str]] = None
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

    rutas = configurar_rutas(input_path, output_dir)
    setup_logging(rutas['log_file'])
    logger.info(f"=== Iniciando proceso con estilo '{estilo}' ===")
    if cfg_overrides:
        logger.info(f"Overrides aplicados: {cfg_overrides}")

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

    try:
        report_progress(10, "Cargando datos de entrada...")
        gdf = pyogrio.read_dataframe(rutas['input'])
        gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
        gdf = verificar_y_transformar_crs(gdf, "capa inicial", cfg['PROJECTED_CRS'])
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
            gdf = calcular_gridcode(gdf, cfg["USE_GRIDCODE"], {k: v.lower() for k, v in cfg["CAMPOS_METRICAS"].items()})

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
            report_progress(25, "Procesando con CSV de entrada...")
            logger.info(f"Usando modo CSV. Leyendo conteo de parcelas desde: {csv_path}")
            if not csv_path or not os.path.exists(csv_path):
                raise FileNotFoundError(f"Archivo CSV de entrada no encontrado en: {csv_path}")

            df_csv = pd.read_csv(csv_path)
            df_csv.columns = [c.lower() for c in df_csv.columns]
            count_col = 'n' if 'n' in df_csv.columns else 'n_parcelas'
            if count_col not in df_csv.columns:
                raise ValueError(f"El CSV debe contener una columna llamada 'n' o 'n_parcelas'.")
            
            for col in grouping_cols:
                if col not in df_csv.columns: raise ValueError(f"Columna de agrupación '{col}' no encontrada en el CSV.")
                if col not in gdf.columns: raise ValueError(f"Columna de agrupación '{col}' no encontrada en el GPKG de entrada.")

            df_csv[count_col] = pd.to_numeric(df_csv[count_col], errors='coerce').fillna(0).astype(int)
            gdf_para_generar = gdf.merge(df_csv, on=grouping_cols, how="left")
            gdf_para_generar.rename(columns={count_col: 'n_parcelas'}, inplace=True)
            gdf_para_generar['n_parcelas'] = gdf_para_generar['n_parcelas'].fillna(0).astype(int)
            resultados['gdf_inicial'] = gdf_para_generar
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
                    logger.info(f"Guardando datos sin exclusiones en: {rutas['gpkg_exclusion']}")
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
            logger.info("Paso de exclusiones deshabilitado en la configuración.")
            gdf_post_exclusion = gdf_para_generar
        
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

    except Exception as e:
        logging.error(f"ERROR EN PIPELINE: {str(e)}", exc_info=True)
        raise

    return resultados