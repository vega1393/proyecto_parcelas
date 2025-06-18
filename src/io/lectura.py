import logging
from typing import Optional

import geopandas as gpd

logger = logging.getLogger(__name__)

def leer_capa(ruta: str, capa: Optional[str] = None) -> gpd.GeoDataFrame:
    """
    Lee una capa geográfica desde un archivo o geodatabase.
    
    Args:
        ruta: Ruta al archivo o geodatabase
        capa: Nombre de la capa (solo para geodatabases o geopackages)
        
    Returns:
        GeoDataFrame con los datos de la capa
    """
    try:
        # Opciones de lectura para manejar polígonos complejos
        read_options = {
            'engine': 'pyogrio',
            'use_arrow': False,  # Evitar problemas con Arrow
            'ignore_geometry': False,
            'skip_features': False,
            'decimal_precision': None,
            'allow_complex_parts': True  # Importante para polígonos con muchas partes
        }
        
        if ruta.lower().endswith('.gdb') or ruta.lower().endswith('.gpkg'):
            if capa is None:
                # Si no se especifica capa, intentar leer la primera
                import fiona
                capas = fiona.listlayers(ruta)
                if not capas:
                    raise ValueError(f"No se encontraron capas en {ruta}")
                capa = capas[0]
                logger.info(f"Usando primera capa disponible: {capa}")
            
            # Usar el parámetro layer en lugar de construir la ruta con |layername=
            logger.info(f"Leyendo capa {capa} desde {ruta}")
            return gpd.read_file(ruta, layer=capa, **read_options)
        else:
            logger.info(f"Leyendo archivo {ruta}")
            return gpd.read_file(ruta, **read_options)
    except Exception as e:
        logger.error(f"Error al leer capa {ruta}: {str(e)}")
        raise 