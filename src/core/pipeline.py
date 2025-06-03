"""
Main pipeline module for the Parcel Generator project.
Executes the full workflow for parcel generation.
"""

import logging
import os
import geopandas as gpd
import pyogrio
from typing import Dict, Any, Optional, List, Tuple, Callable

from src.utils.logging_utils import setup_logging
from src.utils.geo_utils import verificar_y_transformar_crs
from src.config.config_base import get_config
from src.io.rutas import configurar_rutas
from src.pipeline.filtros import aplicar_filtros_iniciales, calcular_gridcode
from src.pipeline.calculo_parcelas import calcular_cantidad_de_parcelas
from src.pipeline.exclusiones import aplicar_exclusiones
from src.pipeline.generacion_parcelas import generar_parcelas, generar_poligonos_parcelas
from src.pipeline.atributos_po import asignar_atributos_po, reordenar_columnas
from src.pipeline.analisis import analizar_perdidas_parcelas


def ejecutar_proceso(
    input_path: str,
    output_dir: Optional[str] = None,
    entrega: Optional[str] = None,
    estilo: str = "calibracion",
    cfg_overrides: Optional[Dict[str, Any]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Ejecuta todo el pipeline de generación de parcelas.
    
    Args:
        input_path: Ruta al archivo de entrada
        output_dir: Directorio de salida (opcional)
        entrega: Código de entrega (opcional)
        estilo: Estilo de procesamiento ("calibracion", "control", "especial")
        cfg_overrides: Sobrescrituras de configuración (opcional)
        progress_callback: Función para reportar progreso (value, status)
        
    Returns:
        Diccionario con los resultados del proceso
    """
    # Función para reportar progreso
    def report_progress(value, status):
        if progress_callback:
            progress_callback(value, status)
        logging.info(f"Progreso: {value}% - {status}")

    # Reportamos inicio
    report_progress(0, "Inicializando...")

    # 1) Obtener configuración según estilo
    cfg = get_config(estilo, cfg_overrides)

    # 2) Configurar rutas, logging
    rutas = configurar_rutas(input_path, output_dir)
    setup_logging(rutas['log_file'])
    logging.info(f"=== Iniciando proceso con estilo '{estilo}' ===")
    if cfg_overrides:
        logging.info(f"Overrides aplicados: {cfg_overrides}")

    report_progress(5, "Configurando...")

    # 3) Pipeline
    resultados = {
        'rutas': rutas,
        'config': cfg,
        'gdf_inicial': None,
        'gdf_post_filtros': None,
        'gdf_post_exclusion': None,
        'puntos_gdf': None,
        'poligonos_gdf': None,
        'gdf_final': None,
        'analisis': None
    }

    try:
        # a) Cargar capa inicial
        report_progress(10, "Cargando datos de entrada...")
        if not os.path.exists(rutas['input']):
            raise FileNotFoundError(
                f"No existe archivo de entrada: {rutas['input']}")
        gdf = pyogrio.read_dataframe(rutas['input'])
        gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
        gdf = verificar_y_transformar_crs(gdf, "capa inicial", cfg['PROJECTED_CRS'])
        gdf.columns = gdf.columns.str.lower()

        # b) Filtros iniciales
        report_progress(15, "Aplicando filtros iniciales...")
        gdf = aplicar_filtros_iniciales(gdf, cfg["FILTROS_CAMPOS"])

        # c) Opciones pipeline
        op = cfg["OPCIONES_ACTIVAS"]
        
        # Paso 1 - Calcular gridcode
        if 1 in op:
            report_progress(20, "Calculando gridcode...")
            gdf = calcular_gridcode(gdf, cfg["USE_GRIDCODE"], cfg["CAMPOS_METRICAS"])
            
        # Paso 2 - Calcular cantidad de parcelas
        if 2 in op:
            report_progress(25, "Calculando cantidad de parcelas...")
            gdf = calcular_cantidad_de_parcelas(
                gdf=gdf,
                fields=cfg["FIELDS"],
                intensidad=cfg["INTENSIDAD"],
                use_intensidad_especifica=cfg["USE_INTENSIDAD_ESPECIFICA"],
                intensidad_por_campo=cfg["INTENSIDAD_POR_CAMPO"],
                min_parcelas=cfg["MIN_PARCELAS"],
                max_parcelas=cfg["MAX_PARCELAS"],
                area_minima_ha=cfg["AREA_MINIMA_HA"],
                buffer_distance=cfg["BUFFER_DISTANCE"],
                output_csv=rutas['csv_resumen'],
                output_gpkg=rutas['gpkg_areas'],
                output_gpkg_dissolved_initial=rutas['gpkg_inicial']
            )
            resultados['gdf_inicial'] = gpd.read_file(
                rutas['gpkg_inicial'], engine='pyogrio')
            resultados['gdf_post_filtros'] = gpd.read_file(
                rutas['gpkg_areas'], engine='pyogrio')

        # Paso 3 - Aplicar exclusiones
        if 3 in op:
            report_progress(40, "Aplicando exclusiones...")
            gdf_exclusion = aplicar_exclusiones(
                gdf=gdf,
                capas_exclusion=cfg["CAPAS_EXCLUSION"],
                fields=cfg["FIELDS"],
                crs_target=cfg["PROJECTED_CRS"],
                output_gpkg=rutas['gpkg_exclusion']
            )
            resultados['gdf_post_exclusion'] = gdf_exclusion
        else:
            gdf_exclusion = gdf
            
        # Paso 4 - Generar parcelas (puntos)
        if 4 in op:
            report_progress(55, "Generando parcelas (puntos)...")
            puntos_gdf = generar_parcelas(
                gdf=gdf_exclusion,
                fields=cfg["FIELDS"],
                min_distance=cfg["MIN_DISTANCE"],
                output_path=rutas['gpkg_parcelas']
            )
            resultados['puntos_gdf'] = puntos_gdf
        else:
            if os.path.exists(rutas['gpkg_parcelas']):
                puntos_gdf = gpd.read_file(
                    rutas['gpkg_parcelas'], engine='pyogrio')
                resultados['puntos_gdf'] = puntos_gdf
            else:
                puntos_gdf = None
                
        # Paso 5 - Generar polígonos
        if 5 in op and puntos_gdf is not None:
            report_progress(70, "Generando polígonos...")
            poligonos_gdf = generar_poligonos_parcelas(
                points_gdf=puntos_gdf,
                area_parcela=cfg["AREA_PARCELA"],
                id_parcela_inicio=cfg["ID_PARCELA_INICIO"],
                version_parcela=cfg["VERSION_PARCELA"],
                fields=cfg["FIELDS"],
                output_path=rutas['gpkg_poligonos']
            )
            resultados['poligonos_gdf'] = poligonos_gdf
        else:
            poligonos_gdf = None
            if os.path.exists(rutas['gpkg_poligonos']):
                poligonos_gdf = gpd.read_file(
                    rutas['gpkg_poligonos'], engine='pyogrio')
                resultados['poligonos_gdf'] = poligonos_gdf
                
        # Paso 6 - Asignar atributos PO
        if 6 in op and poligonos_gdf is not None:
            report_progress(85, "Asignando atributos PO...")
            poligonos_gdf = asignar_atributos_po(
                parcelas_gdf=poligonos_gdf,
                po_config=cfg["PO_CONFIG"],
                crs_target=cfg["PROJECTED_CRS"],
                output_path=rutas['gpkg_po'],
                entrega=entrega
            )
            resultados['gdf_final'] = poligonos_gdf
        else:
            resultados['gdf_final'] = poligonos_gdf

        # Resumen final
        report_progress(95, "Analizando pérdidas...")
        if resultados['gdf_inicial'] is not None:
            analisis_df = analizar_perdidas_parcelas(
                gdf_inicial=resultados['gdf_inicial'],
                fields=cfg["FIELDS"],
                gdf_post_filtros=resultados['gdf_post_filtros'],
                gdf_post_exclusion=resultados['gdf_post_exclusion'],
                gdf_final=resultados['gdf_final'],
                output_csv=rutas['csv_analisis']
            )
            resultados['analisis'] = analisis_df

        # Paso 7 - Reordenamiento de columnas
        if 7 in op and resultados['gdf_final'] is not None:
            report_progress(98, "Reordenando columnas...")
            gdf_final = reordenar_columnas(
                gdf=resultados['gdf_final'],
                output_path=rutas['gpkg_final'],
                output_layer='parcelas_final'
            )
            resultados['gdf_final'] = gdf_final
            logging.info(f"Columnas reordenadas y guardadas en: {rutas['gpkg_final']}")

        # Proceso completado
        report_progress(100, "Proceso completado con éxito!")
        logging.info("=== Proceso completado con éxito ===")

    except Exception as e:
        logging.error(f"ERROR EN PIPELINE: {str(e)}")
        import traceback
        traceback.print_exc(file=open(rutas['log_file'], 'a'))
        raise  # Re-throw para manejo en nivel superior

    return resultados 