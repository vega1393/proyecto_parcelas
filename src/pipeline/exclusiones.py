"""
Módulo para la aplicación de exclusiones geométricas.
"""

import logging
import gc
import geopandas as gpd
import pyogrio
from typing import Dict, Any, Optional, List

from src.utils.geo_utils import verificar_y_transformar_crs, reparar_geometrias
from src.io.lectura import leer_capa

logger = logging.getLogger(__name__)


def aplicar_exclusiones(
    gdf: gpd.GeoDataFrame,
    capas_exclusion: List[Dict[str, Any]],
    fields: List[str],  # Se mantiene por si se usa en el futuro, pero no para dissolve
    crs_target: int,
    output_gpkg: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    Aplica exclusiones geométricas a las áreas de parcelas. Esta versión
    simplificada se enfoca en la operación de diferencia y no vuelve a
    disolver los datos, preservando las columnas existentes como 'n_parcelas'.
    """
    if gdf.empty:
        logger.warning("El GeoDataFrame de entrada para exclusiones está vacío. Saltando el paso.")
        if output_gpkg:
            # Guardar un archivo vacío para mantener la consistencia del pipeline
            gpd.GeoDataFrame([], geometry=[]).to_file(output_gpkg, driver='GPKG', layer='areas_post_exclusion')
        return gdf

    logger.info("Iniciando proceso de exclusión de áreas...")
    result_gdf = gdf.copy()

    for capa_info in capas_exclusion:
        desc = capa_info.get('descripcion', 'unknown')
        logger.info(f"Procesando capa de exclusión: {desc}")
        
        try:
            exclusion_gdf = leer_capa(capa_info['ruta'], capa_info.get('capa'))
            exclusion_gdf = verificar_y_transformar_crs(exclusion_gdf, desc, crs_target)
            exclusion_gdf = reparar_geometrias(exclusion_gdf, desc)

            # Unificar la capa de exclusión para una operación más eficiente
            exclusion_geom = exclusion_gdf.unary_union
            
            logger.info(f"Registros antes de la exclusión con '{desc}': {len(result_gdf)}")
            # Realizar la operación de diferencia
            result_gdf['geometry'] = result_gdf.geometry.difference(exclusion_geom)
            logger.info(f"Registros después de la exclusión: {len(result_gdf)}")
            
            # Limpiar memoria
            del exclusion_gdf, exclusion_geom
            gc.collect()

        except Exception as e:
            logger.error(f"Error procesando la capa de exclusión {desc}: {e}", exc_info=True)
            continue

    # Limpieza final de geometrías
    result_gdf = result_gdf[~result_gdf.geometry.is_empty]
    if result_gdf.empty:
        logger.warning("Todas las áreas fueron eliminadas por las capas de exclusión.")
        if output_gpkg:
            gpd.GeoDataFrame([], geometry=[]).to_file(output_gpkg, driver='GPKG', layer='areas_post_exclusion')
        return result_gdf
        
    logger.info("Convirtiendo a single part y reparando geometrías post-exclusión...")
    result_gdf = result_gdf.explode(index_parts=False).reset_index(drop=True)
    result_gdf = reparar_geometrias(result_gdf, "resultado post-exclusiones")

    # [CORRECCIÓN CLAVE] No se hace `dissolve` aquí.
    # Simplemente recalculamos el área y devolvemos el resultado.
    # Esto preserva la columna 'n_parcelas' y las demás.
    result_gdf['area_m2'] = result_gdf.geometry.area
    result_gdf['area_ha_post_exclusion'] = result_gdf['area_m2'] / 10000
    
    # Filtrar polígonos extremadamente pequeños que pueden ser resultado de la diferencia
    area_pre_filter = len(result_gdf)
    result_gdf = result_gdf[result_gdf['area_m2'] > 1.0].copy() # Filtra slivers de menos de 1 m²
    logger.info(f"Filtrados {area_pre_filter - len(result_gdf)} polígonos 'sliver' muy pequeños.")

    if output_gpkg:
        logger.info(f"Guardando resultado de exclusiones en: {output_gpkg}")
        pyogrio.write_dataframe(result_gdf, output_gpkg, layer='areas_post_exclusion')

    return result_gdf