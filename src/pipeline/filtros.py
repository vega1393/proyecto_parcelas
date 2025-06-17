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
        
    Raises:
        ValueError: Si no quedan registros después de aplicar los filtros
    """
    registros_iniciales = len(gdf)
    logger.info(f"Registros iniciales: {registros_iniciales}")

    for campo, filtro in filtros_campos.items():
        if campo in gdf.columns:
            logger.info(f"Aplicando filtro para {campo}")
            
            # Log valores únicos antes del filtro para diagnóstico
            if not callable(filtro):
                valores_unicos = gdf[campo].dropna().unique()
                logger.info(f"Valores únicos en campo '{campo}': {list(valores_unicos)[:10]}{'...' if len(valores_unicos) > 10 else ''}")
                logger.info(f"Valores buscados en filtro: {filtro}")
                
                # Verificar si algún valor del filtro existe en los datos
                valores_encontrados = [v for v in filtro if v in valores_unicos]
                valores_no_encontrados = [v for v in filtro if v not in valores_unicos]
                
                if valores_encontrados:
                    logger.info(f"Valores del filtro encontrados en los datos: {valores_encontrados}")
                if valores_no_encontrados:
                    logger.warning(f"Valores del filtro NO encontrados en los datos: {valores_no_encontrados}")
            
            # Aplicar el filtro
            if callable(filtro):
                gdf = gdf[gdf[campo].apply(filtro)].copy()
            else:
                gdf = gdf[gdf[campo].isin(filtro)].copy()
            
            registros_despues = len(gdf)
            logger.info(f"Registros después de filtrar por {campo}: {registros_despues}")
            
            # Advertir si el filtro eliminó todos los registros
            if registros_despues == 0:
                logger.error(f"El filtro para campo '{campo}' eliminó todos los registros.")
                if not callable(filtro):
                    logger.error(f"Ninguno de los valores buscados {filtro} se encontró en el campo '{campo}'.")
                    logger.error(f"Considere revisar la configuración de filtros o usar el diálogo de selección de tipos de uso.")
                raise ValueError(f"No quedan registros después de filtrar por campo '{campo}'. "
                               f"Los valores del filtro {filtro if not callable(filtro) else 'función personalizada'} "
                               f"no coinciden con los datos reales.")
        else:
            logger.warning(f"Campo {campo} no encontrado en los datos, se omite el filtro")
    
    # Validación final
    if len(gdf) == 0:
        logger.error("No quedan registros después de aplicar todos los filtros.")
        logger.error("Revise la configuración de filtros y asegúrese de que los valores coincidan con los datos reales.")
        raise ValueError("No quedan registros después de aplicar los filtros iniciales. "
                        "Revise la configuración de tipos de uso y otros filtros.")
    
    logger.info(f"Filtros aplicados exitosamente. Registros finales: {len(gdf)}")
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