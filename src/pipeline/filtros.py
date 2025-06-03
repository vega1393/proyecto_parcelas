"""
Módulo para los filtros iniciales y el cálculo de gridcode.
"""

import logging
import geopandas as gpd
from typing import Dict, Any, Optional, List, Callable, Union

logger = logging.getLogger(__name__)


def aplicar_filtros_iniciales(
    gdf: gpd.GeoDataFrame,
    filtros_campos: Dict[str, Union[List[str], Callable]]
) -> gpd.GeoDataFrame:
    """
    Aplica filtros iniciales a los datos basados en la configuración.

    Args:
        gdf: GeoDataFrame a filtrar
        filtros_campos: Diccionario con filtros por campo (lista de valores o función)

    Returns:
        GeoDataFrame filtrado
    """
    registros_iniciales = len(gdf)
    logger.info(f"Registros iniciales: {registros_iniciales}")

    for campo, filtro in filtros_campos.items():
        if campo in gdf.columns:
            logger.info(f"Aplicando filtro para {campo}")
            if callable(filtro):
                gdf = gdf[gdf[campo].apply(filtro)].copy()
            else:
                gdf = gdf[gdf[campo].isin(filtro)].copy()
            logger.info(f"Registros después de filtrar por {campo}: {len(gdf)}")
        else:
            logger.warning(f"Campo {campo} no encontrado en los datos, se omite el filtro")
    
    return gdf


def calcular_gridcode(
    gdf: gpd.GeoDataFrame,
    use_gridcode: bool,
    campos_metricas: Dict[str, str]
) -> gpd.GeoDataFrame:
    """
    Calcula un campo 'gridcode' usando valores de cobertura (cov) y altura (p95).
    El gridcode es un código de dos dígitos que representa la combinación de categorías
    de cobertura y altura, útil para estratificar el muestreo.

    Se activa solo si use_gridcode=True. Si está desactivado,
    el campo 'gridcode' se establece como None.

    Args:
        gdf: GeoDataFrame con los datos a procesar
        use_gridcode: Indica si calcular el gridcode
        campos_metricas: Dict con las claves 'cov' y 'p95' que mapean
          a los nombres de columnas en gdf

    Returns:
        GeoDataFrame con la nueva columna 'gridcode'
    """
    logger.info("Iniciando cálculo de gridcode...")
    cov_field = campos_metricas["cov"]
    p95_field = campos_metricas["p95"]

    def _calc_code(row):
        cov = row.get(cov_field, 0)
        p95 = row.get(p95_field, 0)
        
        # Determinar cov_id
        if 0 <= cov <= 30:
            cov_id = 1
        elif 30 < cov <= 60:
            cov_id = 2
        elif 60 < cov:
            cov_id = 3
        else:
            cov_id = None
            
        # Determinar p95_id
        if 0 <= p95 <= 15:
            p95_id = 1
        elif 15 < p95 <= 20:
            p95_id = 2
        elif 20 < p95 <= 25:
            p95_id = 3
        elif 25 < p95 <= 30:
            p95_id = 4
        elif 30 < p95:
            p95_id = 5
        else:
            p95_id = None
            
        return f"{cov_id}{p95_id}"

    if use_gridcode:
        gdf['gridcode'] = gdf.apply(_calc_code, axis=1)
    else:
        gdf['gridcode'] = None

    logger.info("Cálculo de gridcode finalizado.")
    return gdf 