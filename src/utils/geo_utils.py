"""
Geospatial utilities for the Parcel Generator project.
"""

import logging
import gc
import geopandas as gpd
import shapely
from typing import Dict, Any, Optional, List, Tuple
from shapely.geometry import Point, Polygon, MultiPolygon

logger = logging.getLogger(__name__)


def verificar_y_transformar_crs(
    gdf: gpd.GeoDataFrame,
    desc: str,
    crs_target: int
) -> gpd.GeoDataFrame:
    """
    Verifica y transforma el CRS de un GeoDataFrame si es necesario.
    
    Args:
        gdf: GeoDataFrame a verificar/transformar
        desc: Descripción para los mensajes de log
        crs_target: CRS objetivo (código EPSG)
        
    Returns:
        GeoDataFrame con el CRS correcto
    """
    if gdf.crs is None:
        logger.warning(f"CRS no definido en {desc}. Asumiendo EPSG:{crs_target}")
        gdf.set_crs(epsg=crs_target, inplace=True)
    else:
        epsg_actual = gdf.crs.to_epsg() if gdf.crs.to_epsg() else None
        if epsg_actual != crs_target:
            logger.info(f"Transformando CRS de {desc} a EPSG:{crs_target}")
            gdf = gdf.to_crs(epsg=crs_target)
    return gdf


def reparar_geometrias(gdf: gpd.GeoDataFrame, desc: str) -> gpd.GeoDataFrame:
    """
    Repara geometrías inválidas en un GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame con geometrías a reparar
        desc: Descripción para los mensajes de log
        
    Returns:
        GeoDataFrame con geometrías reparadas
    """
    logger.info(f"Iniciando reparación de geometrías para {desc}...")
    initial_count = len(gdf)
    
    # Forzar 2D y reparar geometrías
    gdf['geometry'] = gdf.geometry.map(lambda geom:
        shapely.force_2d(
            shapely.make_valid(
                shapely.force_2d(geom)
            )
        )
    )
    
    # Filtrar por tipos válidos
    valid_types = ['Polygon', 'MultiPolygon']
    gdf = gdf[gdf.geometry.geom_type.isin(valid_types)].copy()
    
    # Aplicar buffer 0 para corregir auto-intersecciones
    gdf['geometry'] = gdf.geometry.buffer(0)
    
    # Filtrar geometrías válidas
    gdf = gdf[gdf.geometry.is_valid].copy()
    
    final_count = len(gdf)
    if initial_count != final_count:
        logger.warning(f"Se eliminaron {initial_count - final_count} geometrías durante la reparación")
    
    logger.info(f"Reparación de geometrías completada. Geometrías finales: {final_count}")
    return gdf


def generar_grid_puntos(polygon: Polygon, spacing: float = 10.0) -> List[Point]:
    """
    Genera una cuadrícula de puntos dentro de un polígono.
    
    Args:
        polygon: Polígono donde generar los puntos
        spacing: Espaciado entre puntos en metros
        
    Returns:
        Lista de puntos dentro del polígono
    """
    minx, miny, maxx, maxy = polygon.bounds
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    center_x = round(center_x / spacing) * spacing
    center_y = round(center_y / spacing) * spacing
    
    initial_point = Point(center_x, center_y)
    if not polygon.contains(initial_point):
        # Si no contiene, usar un punto representativo
        initial_point = polygon.representative_point()

    nx = int((maxx - minx) / spacing) + 1
    ny = int((maxy - miny) / spacing) + 1

    points = []
    for i in range(-(nx // 2), nx // 2 + 1):
        for j in range(-(ny // 2), ny // 2 + 1):
            x = initial_point.x + (i * spacing)
            y = initial_point.y + (j * spacing)
            point = Point(x, y)
            if polygon.contains(point):
                points.append(point)
    return points


def filtrar_puntos_por_poligono(points: List[Point], polygon: Polygon) -> List[Point]:
    """
    Filtra puntos para mantener solo los que están dentro del polígono.
    
    Args:
        points: Lista de puntos a filtrar
        polygon: Polígono para el filtrado
        
    Returns:
        Lista de puntos filtrados
    """
    puntos_filtrados = []
    for point in points:
        if polygon.contains(point) and not polygon.boundary.contains(point):
            puntos_filtrados.append(point)
    return puntos_filtrados 