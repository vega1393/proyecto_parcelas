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
    Aplica filtros iniciales a los datos basándose en campos específicos.
    
    Args:
        gdf: GeoDataFrame con los datos de entrada
        filtros_campos: Diccionario con los filtros a aplicar por campo
        
    Returns:
        GeoDataFrame filtrado
        
    Raises:
        ValueError: Si no quedan registros después de aplicar los filtros
    """
    logger.info(f"Registros iniciales: {len(gdf)}")
    
    if not filtros_campos:
        logger.info("No hay filtros configurados. Manteniendo todos los registros.")
        return gdf

    for campo, filtro in filtros_campos.items():
        if campo in gdf.columns:
            logger.info(f"Aplicando filtro para {campo}")
            
            # Log valores únicos antes del filtro para diagnóstico
            if not callable(filtro):
                valores_unicos = gdf[campo].dropna().unique()
                logger.debug(f"Valores únicos en campo '{campo}': {list(valores_unicos)[:10]}{'...' if len(valores_unicos) > 10 else ''}")
                logger.debug(f"Valores buscados en filtro: {filtro}")
                
                # Verificar si algún valor del filtro existe en los datos
                valores_encontrados = [v for v in filtro if v in valores_unicos]
                valores_no_encontrados = [v for v in filtro if v not in valores_unicos]
                
                if valores_encontrados:
                    logger.debug(f"Valores del filtro encontrados en los datos: {valores_encontrados}")
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
    campos_metricas: Dict[str, str],
    gridcode_params: Optional[Dict[str, Any]] = None
) -> gpd.GeoDataFrame:
    """
    Calcula un campo 'gridcode' usando valores de cobertura y altura configurables.
    El gridcode es un código de dos dígitos que representa la combinación de categorías
    de cobertura y altura, útil para estratificar el muestreo.

    Se activa solo si use_gridcode=True. Si está desactivado,
    el campo 'gridcode' se establece como None.

    Args:
        gdf: GeoDataFrame con los datos a procesar
        use_gridcode: Indica si calcular el gridcode
        campos_metricas: Dict con las claves 'cov' y 'p95' que mapean
          a los nombres de columnas en gdf (usado como fallback)
        gridcode_params: Configuración dinámica de bins desde GRIDCODE_PARAMS

    Returns:
        GeoDataFrame con la nueva columna 'gridcode'
    """
    logger.info("Iniciando cálculo de gridcode...")
    
    if not use_gridcode:
        gdf['gridcode'] = None
        logger.info("GridCode deshabilitado. Campo 'gridcode' establecido como None.")
        return gdf

    # Usar configuración dinámica si está disponible, sino usar fallback
    if gridcode_params and "field1" in gridcode_params and "field2" in gridcode_params:
        logger.info("Usando configuración dinámica de GRIDCODE_PARAMS")
        field1_config = gridcode_params["field1"]
        field2_config = gridcode_params["field2"]
        
        field1_name = field1_config.get("field", "cov")
        field2_name = field2_config.get("field", "p95")
        field1_bins = field1_config.get("bins", [])
        field2_bins = field2_config.get("bins", [])
        
        logger.info(f"Campo 1: {field1_name} con {len(field1_bins)} bins")
        logger.info(f"Campo 2: {field2_name} con {len(field2_bins)} bins")
        
        # Log de configuración de bins para debugging
        for i, bin_def in enumerate(field1_bins):
            min_val = bin_def.get("min", "-∞")
            max_val = bin_def.get("max", "+∞")
            bin_id = bin_def.get("id", "?")
            logger.debug(f"  {field1_name} Bin {i+1}: {min_val} to {max_val} → ID {bin_id}")
            
        for i, bin_def in enumerate(field2_bins):
            min_val = bin_def.get("min", "-∞")
            max_val = bin_def.get("max", "+∞")
            bin_id = bin_def.get("id", "?")
            logger.debug(f"  {field2_name} Bin {i+1}: {min_val} to {max_val} → ID {bin_id}")
        
        def _calc_code_dynamic(row):
            """Calcula gridcode usando configuración dinámica de bins."""
            field1_val = row.get(field1_name, 0)
            field2_val = row.get(field2_name, 0)
            
            # Determinar field1_id usando bins configurados
            field1_id = None
            for bin_def in field1_bins:
                min_val = bin_def.get("min")
                max_val = bin_def.get("max")
                bin_id = bin_def.get("id")
                
                # Verificar si el valor está en este bin
                in_range = True
                if min_val is not None and field1_val < min_val:
                    in_range = False
                if max_val is not None and field1_val > max_val:
                    in_range = False
                    
                if in_range:
                    field1_id = bin_id
                    break
            
            # Determinar field2_id usando bins configurados
            field2_id = None
            for bin_def in field2_bins:
                min_val = bin_def.get("min")
                max_val = bin_def.get("max")
                bin_id = bin_def.get("id")
                
                # Verificar si el valor está en este bin
                in_range = True
                if min_val is not None and field2_val < min_val:
                    in_range = False
                if max_val is not None and field2_val > max_val:
                    in_range = False
                    
                if in_range:
                    field2_id = bin_id
                    break
            
            # Combinar IDs para formar gridcode
            if field1_id is not None and field2_id is not None:
                return f"{field1_id}{field2_id}"
            else:
                return None
        
        gdf['gridcode'] = gdf.apply(_calc_code_dynamic, axis=1)
        
    else:
        # Fallback: usar configuración hardcodeada (LEGACY)
        logger.warning("GRIDCODE_PARAMS no disponible. Usando configuración hardcodeada (LEGACY)")
        logger.warning("ADVERTENCIA: Esta configuración puede no coincidir con gui_settings.json")
        
        cov_field = campos_metricas.get("cov", "cov")
        p95_field = campos_metricas.get("p95", "p95")
        
        logger.info(f"Usando campos legacy: cov='{cov_field}', p95='{p95_field}'")

        def _calc_code_legacy(row):
            """Función legacy con valores hardcodeados."""
            cov = row.get(cov_field, 0)
            p95 = row.get(p95_field, 0)
            
            # Determinar cov_id (VALORES HARDCODEADOS - LEGACY)
            if 0 <= cov <= 30:
                cov_id = 1
            elif 30 < cov <= 60:
                cov_id = 2
            elif 60 < cov:
                cov_id = 3
            else:
                cov_id = None
                
            # Determinar p95_id (VALORES HARDCODEADOS - LEGACY)
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
                
            return f"{cov_id}{p95_id}" if cov_id is not None and p95_id is not None else None

        gdf['gridcode'] = gdf.apply(_calc_code_legacy, axis=1)

    # Estadísticas del gridcode calculado
    if 'gridcode' in gdf.columns:
        gridcode_counts = gdf['gridcode'].value_counts().sort_index()
        logger.info(f"GridCode calculado. Distribución:")
        for gridcode, count in gridcode_counts.head(10).items():
            logger.info(f"  GridCode {gridcode}: {count} registros")
        if len(gridcode_counts) > 10:
            logger.info(f"  ... y {len(gridcode_counts) - 10} códigos adicionales")
        
        # Contar valores nulos
        null_count = gdf['gridcode'].isna().sum()
        if null_count > 0:
            logger.warning(f"  {null_count} registros con gridcode = None (fuera de rangos)")

    logger.info("Cálculo de gridcode finalizado.")
    return gdf 