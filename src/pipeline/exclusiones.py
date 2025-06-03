"""
Módulo para la aplicación de exclusiones geométricas.
"""

import logging
import gc
import geopandas as gpd
import pyogrio
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple

from src.utils.geo_utils import verificar_y_transformar_crs, reparar_geometrias
from src.config.config_base import filtrar_apl
from src.io.lectura import leer_capa

logger = logging.getLogger(__name__)


def aplicar_exclusiones(
    gdf: gpd.GeoDataFrame,
    capas_exclusion: List[Dict[str, Any]],
    fields: List[str],
    crs_target: int,
    output_gpkg: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    Aplica exclusiones geométricas a las áreas de parcelas utilizando capas externas.

    Realiza operaciones de diferencia geométrica entre el GeoDataFrame de entrada
    y cada una de las capas de exclusión definidas en la configuración. Las áreas
    que intersecan con alguna capa de exclusión son eliminadas del resultado final.

    Args:
        gdf: GeoDataFrame con áreas candidatas para parcelas
        capas_exclusion: Lista de diccionarios con 'ruta', 'capa' y 'descripcion'
          para cada capa de exclusión
        fields: Lista de campos para la agrupación en el dissolve final
        crs_target: CRS objetivo (código EPSG)
        output_gpkg: Ruta donde guardar el resultado (opcional)

    Returns:
        GeoDataFrame con las áreas después de aplicar todas las exclusiones
    """
    logger.info("Iniciando proceso de exclusión de áreas...")
    result_gdf = gdf.copy()

    for capa in capas_exclusion:
        desc = capa.get('descripcion', 'unknown')
        logger.info(f"Procesando capa de exclusión: {desc}")
        try:
            # Importar la función leer_capa
            from src.io.lectura import leer_capa
            
            # Cargar la capa usando la función leer_capa
            exclusion_gdf = leer_capa(capa['ruta'], capa.get('capa'))

            # CRS
            exclusion_gdf = verificar_y_transformar_crs(
                exclusion_gdf, desc, crs_target)

            # Reparar
            exclusion_gdf = reparar_geometrias(
                exclusion_gdf, desc)

            # Aplicar filtros específicos si es necesario
            if capa.get('filtro_apl') or capa.get('filtro_uso'):
                logger.info(
                    "Aplicando filtros específicos a la capa de exclusión")
                exclusion_original_count = len(exclusion_gdf)

                # Convertir columnas a minúsculas
                exclusion_gdf.columns = exclusion_gdf.columns.str.lower()

                # Si es la capa PO (detectado por la descripción), invertimos la lógica:
                # Queremos EXCLUIR lo que NO cumple con el filtro
                is_po_layer = "Plan Operativo (PO)" in desc

                if is_po_layer:
                    logger.info(
                        "Detectado PO como capa de exclusión. IMPORTANTE: Invirtiendo lógica de filtros")
                    logger.info(
                        "Solo se excluirán las áreas del PO que NO cumplen con los criterios de filtrado")
                    logger.info(
                        "Es decir, se conservarán las áreas que sí cumplen con los filtros")

                    # Obtener nombres de campos
                    campo_tipo_uso = capa.get(
                        'campo_tipo_uso', 'tipouso').lower()
                    campo_apl = capa.get('campo_apl', 'apl').lower()

                    logger.info(
                        f"Usando campo '{campo_tipo_uso}' para tipo de uso")
                    logger.info(f"Usando campo '{campo_apl}' para APL")

                    # Convertir campos a string si no existen
                    for campo in [campo_tipo_uso, campo_apl]:
                        if campo not in exclusion_gdf.columns:
                            logger.warning(
                                f"Campo '{campo}' no encontrado en la capa de exclusión")

                    # Filtrar solo si los campos existen
                    to_exclude_gdf = None
                    temp_exclusion_gdf = exclusion_gdf.copy()

                    # Convertir la columna tipo_uso a string para evitar
                    # errores
                    try:
                        if campo_tipo_uso in temp_exclusion_gdf.columns:
                            # Crear copia segura de la columna tipo_uso
                            # convertida a string
                            temp_exclusion_gdf['tipo_uso_str'] = temp_exclusion_gdf[campo_tipo_uso].astype(
                                str).str.upper()
                    except Exception as e:
                        logger.error(
                            f"Error al convertir campo '{campo_tipo_uso}' a string: {str(e)}")
                        # Valor por defecto que no coincidirá con nada
                        temp_exclusion_gdf['tipo_uso_str'] = 'ERROR'

                # Filtrar por tipo de uso (lógica similar)
                if capa.get(
                    'filtro_uso') and 'tipouso' in exclusion_gdf.columns:
                    logger.info("Aplicando filtro de tipo de uso (invertido)")

                    # Definir los tipos de uso válidos (personalizados o por
                    # defecto)
                    tipos_uso_validos = capa.get(
                        'tipos_uso_validos', [
                            'EHNG', 'PIRA', 'EUNI', 'EUGL', 'EGRN'])

                    # Si no hay lista, usar lista vacía
                    if tipos_uso_validos is None:
                        tipos_uso_validos = []

                    logger.info(
                        f"Tipos de uso considerados válidos: {tipos_uso_validos}")

                    # Si ya hay registros filtrados por APL, usamos esos como
                    # base
                    if to_exclude_gdf is not None:
                        # Agregar registros donde tipo_uso NO está en la lista
                        # de válidos
                        tipo_uso_invalidos = to_exclude_gdf[~to_exclude_gdf['tipouso'].str.upper().isin(
                            tipos_uso_validos)]

                        # Agregar registros donde tipo_uso es válido pero APL
                        # no pasó el filtro
                        apl_invalidos = to_exclude_gdf[to_exclude_gdf['tipouso'].str.upper().isin(
                            tipos_uso_validos)]

                        # Unificar ambos conjuntos de datos
                        to_exclude_gdf = pd.concat(
                            [tipo_uso_invalidos, apl_invalidos])
                    else:
                        # Si no hay filtro previo, comenzamos con este
                        to_exclude_gdf = exclusion_gdf[~exclusion_gdf['tipouso'].str.upper().isin(
                            tipos_uso_validos)]

                # Usamos los registros que NO cumplen con los filtros como capa
                # de exclusión
                if to_exclude_gdf is not None and len(to_exclude_gdf) > 0:
                    exclusion_gdf = to_exclude_gdf
                    logger.info(
                        f"Se utilizará una capa de exclusión con {len(exclusion_gdf)} registros que NO cumplen los criterios")
                else:
                    # Si todos los registros pasan los filtros, no hay nada que
                    # excluir
                    logger.info(
                        "No hay registros que excluir según los filtros - se omitirá esta exclusión")
                    continue
            else:
                # Para capas que NO son PO, mantenemos la lógica original
                # Filtrar por APL
                if capa.get('filtro_apl') and 'apl' in exclusion_gdf.columns:
                    logger.info("Aplicando filtro de APL...")
                    exclusion_gdf = exclusion_gdf[exclusion_gdf['apl'].apply(
                        filtrar_apl)]
                    logger.info(
                        f"Después de filtro APL: {len(exclusion_gdf)} de {exclusion_original_count}")

                # Filtrar por tipo de uso
                if capa.get(
                    'filtro_uso') and 'tipouso' in exclusion_gdf.columns:
                    logger.info("Aplicando filtro de tipo de uso...")
                    # Se pueden agregar filtros específicos para tipo_uso si es
                    # necesario
                    logger.info(
                        f"Después de filtro de tipo de uso: {len(exclusion_gdf)} de {exclusion_original_count}")

            # Diferencia
            logger.info(f"Registros antes de exclusión: {len(result_gdf)}")
            result_gdf = gpd.overlay(
                result_gdf,
                exclusion_gdf,
                how='difference',
                keep_geom_type=True)
            logger.info(f"Registros después de exclusión: {len(result_gdf)}")

            del exclusion_gdf
            gc.collect()

        except Exception as e:
            logger.error(f"Error al procesar {desc}: {str(e)}")
            continue

    result_gdf = reparar_geometrias(result_gdf, "resultado post-exclusiones")
    logger.info("Convirtiendo a single part...")
    result_gdf = result_gdf.explode(index_parts=False).reset_index(drop=True)
    logger.info("Recalculando áreas...")
    result_gdf['area_m2'] = result_gdf.geometry.area
    result_gdf['area_ha'] = result_gdf['area_m2'] / 10000
    logger.info(f"Registros antes de filtrar <0.005 ha: {len(result_gdf)}")
    result_gdf = result_gdf[result_gdf['area_ha'] >= 0.005].copy()
    logger.info(f"Registros después de filtrar <0.005 ha: {len(result_gdf)}")

    keep_cols = [col for col in fields +
     ['gridcode', 'n_parcelas'] if col in result_gdf.columns]
    result_gdf = result_gdf.dissolve(
        by=keep_cols,
        as_index=False,
        aggfunc={
            'area_ha': 'sum',
            'area_ha_original': 'first',
            'area_ha_post_filtros': 'first',
            'area_ha_descuento_buff': 'first'
        }
    )
    result_gdf['area_m2'] = result_gdf.geometry.area
    result_gdf['area_ha'] = result_gdf['area_m2'] / 10000

    if output_gpkg:
        logger.info(f"Guardando resultado de exclusiones en: {output_gpkg}")
        try:
            pyogrio.write_dataframe(
                result_gdf,
                output_gpkg,
                driver='GPKG',
                layer='areas_post_exclusion'
            )
        except Exception as e:
            logger.error(f"Error al guardar GPKG: {str(e)}")
            shp_path = output_gpkg.replace('.gpkg', '.shp')
            logger.info(f"Intentando guardar como shapefile: {shp_path}")
            pyogrio.write_dataframe(result_gdf, shp_path)

    return result_gdf 