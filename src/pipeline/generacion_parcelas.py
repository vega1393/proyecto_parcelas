# src/pipeline/generacion_parcelas.py

import logging
import math
import random
import geopandas as gpd
import pandas as pd
import numpy as np
import pyogrio
from typing import List, Dict, Any, Optional
from multiprocessing import Pool, cpu_count
from functools import partial
from shapely.geometry import Point, Polygon

from src.utils.geo_utils import generar_grid_puntos
from src.utils.logging_utils import setup_worker_logging

logger = logging.getLogger(__name__)

def seleccionar_puntos_distantes(points: List[Point], n_parcels: int, min_distance: float, max_attempts: int = 15) -> List[Point]:
    """Improved random point selection to ensure minimum distance."""
    if not points or n_parcels == 0:
        return []
    if len(points) < n_parcels:
        logger.warning(f"Not enough candidate points ({len(points)}) to select {n_parcels}. Trying to select as many as possible.")
        n_parcels = len(points)

    best_solution = []
    for _ in range(max_attempts):
        candidates = random.sample(points, len(points))
        selected_points = []
        if not candidates: continue
        
        selected_points.append(candidates.pop(0))

        for p_candidate in candidates:
            if len(selected_points) >= n_parcels:
                break
            if all(p_candidate.distance(p_selected) >= min_distance for p_selected in selected_points):
                selected_points.append(p_candidate)

        if len(selected_points) > len(best_solution):
            best_solution = selected_points
        if len(best_solution) == n_parcels:
            return best_solution
            
    if len(best_solution) < n_parcels:
        logger.warning(f"Could not find all required parcels. Found {len(best_solution)} of {n_parcels}.")
    return best_solution

def procesar_grupo_worker(group_data: tuple, gdf: gpd.GeoDataFrame, group_cols: list, min_distance: float, grid_spacing: float) -> dict:
    """Worker function to process a single group for parcel generation."""
    setup_worker_logging()
    _, group_row = group_data
    n_parcels_req = int(group_row.get('n_parcelas', 0))
    
    group_id_vals = [str(group_row.get(col, '')) for col in group_cols]
    group_id = "_".join(filter(None, group_id_vals))

    result = {'group_id': group_id, 'parcels_requested': n_parcels_req, 'parcels_generated': 0, 'points': []}
    if n_parcels_req == 0: return result

    try:
        mask = pd.Series(True, index=gdf.index)
        for col in group_cols:
            if col in gdf.columns:
                mask &= (gdf[col] == group_row[col])
        
        group_geoms_gdf = gdf[mask]
        if group_geoms_gdf.empty: return result

        unified_geom = group_geoms_gdf.unary_union
        geoms_to_process = unified_geom.geoms if hasattr(unified_geom, 'geoms') else [unified_geom]
        
        candidate_points = [p for poly in geoms_to_process if isinstance(poly, Polygon) for p in generar_grid_puntos(poly, grid_spacing)]
        if not candidate_points: return result
            
        selected_points = seleccionar_puntos_distantes(candidate_points, n_parcels_req, min_distance)
        
        for point in selected_points:
            point_attrs = {col: group_row.get(col) for col in group_cols}
            point_attrs['geometry'] = point
            point_attrs['group_id'] = group_id
            result['points'].append(point_attrs)
        
        result['parcels_generated'] = len(selected_points)
        return result

    except Exception as e:
        logger.error(f"Error processing group {group_id}: {e}", exc_info=True)
        return result

def generar_parcelas(gdf: gpd.GeoDataFrame, group_cols: list, min_distance: float, output_path: str, grid_spacing: float = 20.0, retry_attempts: int = 3, retry_spacing_factor: float = 0.5) -> gpd.GeoDataFrame:
    """Orchestrates parcel generation with retry logic for failed groups."""
    logger.info("Starting flexible parcel generation...")
    # [CORRECCIÓN] Manejar el caso de un GDF de entrada vacío desde el principio
    if gdf.empty or 'n_parcelas' not in gdf.columns:
        logger.warning("'n_parcelas' column not found or input GeoDataFrame is empty. No parcels will be generated.")
        return gpd.GeoDataFrame([], geometry=[], crs=gdf.crs)

    gdf_to_process = gdf[gdf['n_parcelas'] > 0].copy()
    all_points_data = []

    # ... (el resto de la función, el bucle for, no cambia) ...
    for i in range(retry_attempts + 1):
        if gdf_to_process.empty:
            logger.info("All groups processed.")
            break

        current_spacing = grid_spacing * (retry_spacing_factor ** i)
        pass_type = "Initial Pass" if i == 0 else f"Retry Pass {i}"
        logger.info(f"--- {pass_type} on {len(gdf_to_process)} groups | Grid Spacing: {current_spacing:.2f}m ---")
        
        tasks = gdf_to_process.iterrows()
        worker_func = partial(procesar_grupo_worker, gdf=gdf, group_cols=group_cols, min_distance=min_distance, grid_spacing=current_spacing)
        
        with Pool(processes=max(1, cpu_count() - 1)) as pool:
            results = pool.map(worker_func, tasks)
        
        gdf_to_process['parcels_generated'] = 0
        
        successful_groups = []
        for res in results:
            if res['parcels_generated'] > 0:
                all_points_data.extend(res['points'])
            if res['parcels_generated'] >= res['parcels_requested']:
                successful_groups.append(res['group_id'])
        
        # Prepare for next retry: filter out groups that are now complete
        gdf_to_process = gdf_to_process[~gdf_to_process.apply(lambda row: "_".join([str(row.get(col, '')) for col in group_cols if col in row]), axis=1).isin(successful_groups)]


    if all_points_data:
        points_gdf = gpd.GeoDataFrame(all_points_data, crs=gdf.crs)
        logger.info(f"Total parcels generated: {len(points_gdf)}. Saving to {output_path}")
        pyogrio.write_dataframe(points_gdf, output_path)
        return points_gdf
    
    logger.warning("No parcels were generated.")
    # [CORRECCIÓN] Crear un GDF vacío de forma segura, especificando la columna de geometría.
    return gpd.GeoDataFrame([], geometry=[], crs=gdf.crs)

def generar_poligonos_parcelas(points_gdf: gpd.GeoDataFrame, area_parcela: float, id_parcela_inicio: int, version_parcela: str, fields: List[str], output_path: str) -> gpd.GeoDataFrame:
    """Generates circular polygons from points. (This function can remain mostly the same)."""
    # ... (El código de esta función de tu archivo original puede ser mantenido o adaptado ligeramente)
    logger.info("Generating circular polygons from points...")
    if points_gdf.empty:
        logger.warning("Input points GeoDataFrame is empty. No polygons will be generated.")
        return points_gdf
        
    radio = math.sqrt(area_parcela / math.pi)
    
    polygons_data = []
    points_gdf['id_parcela'] = range(id_parcela_inicio, id_parcela_inicio + len(points_gdf))
    
    for _, row in points_gdf.iterrows():
        polygon_attrs = row.to_dict()
        polygon_attrs['geometry'] = row.geometry.buffer(radio)
        polygon_attrs['area_m2'] = area_parcela
        polygon_attrs['punto_x'] = row.geometry.x
        polygon_attrs['punto_y'] = row.geometry.y
        polygons_data.append(polygon_attrs)

    if polygons_data:
        parcelas_gdf = gpd.GeoDataFrame(polygons_data, crs=points_gdf.crs)
        logger.info(f"Saving {len(parcelas_gdf)} polygons to {output_path}")
        pyogrio.write_dataframe(parcelas_gdf, output_path)
        return parcelas_gdf
        
    return gpd.GeoDataFrame([], crs=points_gdf.crs)