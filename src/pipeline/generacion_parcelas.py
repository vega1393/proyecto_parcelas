"""
Módulo para la generación de parcelas (puntos y polígonos).
"""

import logging
import math
import random
import geopandas as gpd
import pyogrio
from typing import Dict, Any, Optional, List, Tuple
from multiprocessing import Pool, cpu_count
from functools import partial
from shapely.geometry import Point, Polygon

from src.utils.geo_utils import generar_grid_puntos, filtrar_puntos_por_poligono
from src.utils.logging_utils import setup_worker_logging

logger = logging.getLogger(__name__)


def seleccionar_puntos_aleatorios(
    points: List[Point],
    n_parcelas: int,
    min_distance: float,
    max_intentos: int = 30
) -> List[Point]:
    """
    Selecciona puntos aleatorios manteniendo una distancia mínima entre ellos.
    
    Args:
        points: Lista de puntos candidatos
        n_parcelas: Número de parcelas a seleccionar
        min_distance: Distancia mínima entre parcelas
        max_intentos: Número máximo de intentos
        
    Returns:
        Lista de puntos seleccionados
    """
    if len(points) < n_parcelas:
        logger.warning(
            f"No hay suficientes puntos candidatos ({len(points)}) para {n_parcelas} parcelas")
        # En lugar de devolver todos los puntos, intentamos seleccionar los que cumplan la distancia
        puntos_validos = []
        for p in points:
            if not puntos_validos:
                puntos_validos.append(p)
                continue
            
            cumple_distancia = True
            for pv in puntos_validos:
                if p.distance(pv) < min_distance:
                    cumple_distancia = False
                    break
            
            if cumple_distancia:
                puntos_validos.append(p)
        
        logger.warning(f"Se encontraron {len(puntos_validos)} puntos que cumplen la distancia mínima")
        return puntos_validos

    mejor_solucion = []
    mejor_cantidad = 0
    
    for intento in range(max_intentos):
        puntos_seleccionados = []
        candidatos = points.copy()
        
        while len(puntos_seleccionados) < n_parcelas and candidatos:
            if not puntos_seleccionados:
                # Para el primer punto, seleccionar uno aleatorio
                punto = random.choice(candidatos)
                puntos_seleccionados.append(punto)
                candidatos.remove(punto)
                continue
            
            # Calcular distancias mínimas para cada candidato
            candidatos_validos = []
            for p in candidatos:
                min_dist = float('inf')
                for ps in puntos_seleccionados:
                    dist = p.distance(ps)
                    if dist < min_distance:  # Si no cumple la distancia mínima, descartamos el punto
                        break
                    min_dist = min(min_dist, dist)
                else:  # Solo si cumple con todas las distancias mínimas
                    candidatos_validos.append((p, min_dist))
            
            if not candidatos_validos:
                break
            
            # Ordenar por distancia y seleccionar entre los mejores candidatos
            candidatos_validos.sort(key=lambda x: x[1], reverse=True)
            punto_seleccionado = candidatos_validos[0][0]  # Seleccionar el punto más alejado
            puntos_seleccionados.append(punto_seleccionado)
            candidatos.remove(punto_seleccionado)

        if len(puntos_seleccionados) == n_parcelas:
            logger.info(f"Solución completa en intento {intento+1}")
            return puntos_seleccionados

        if len(puntos_seleccionados) > mejor_cantidad:
            mejor_cantidad = len(puntos_seleccionados)
            mejor_solucion = puntos_seleccionados.copy()

    if mejor_cantidad < n_parcelas:
        logger.warning(
            f"No se logró ubicar todas las parcelas. Mejor: {mejor_cantidad}/{n_parcelas}")
    
    return mejor_solucion


def procesar_grupo(
    group_data,
    gdf_exploded,
    fields,
    spacing,
    min_distance,
    max_intentos
):
    setup_worker_logging()  # Asegura logging multiproceso
    """
    Procesa un grupo para generar parcelas.
    
    Args:
        group_data: Tupla (idx, group) con los datos del grupo
        gdf_exploded: GeoDataFrame con geometrías explotadas
        fields: Lista de campos para identificar el grupo
        spacing: Espaciado entre puntos
        min_distance: Distancia mínima entre parcelas
        max_intentos: Número máximo de intentos
        
    Returns:
        Diccionario con puntos generados y estadísticas
    """
    idx, group = group_data
    n_parcelas = int(group.get('n_parcelas', 0))

    grupo_components = []
    campos_info = {}
    for field in fields:
        if field in group:
            grupo_components.append(str(group[field]))
            campos_info[field] = group[field]
    if 'gridcode' in group:
        grupo_components.append(str(group['gridcode']))
        campos_info['gridcode'] = group['gridcode']
    grupo_id = '_'.join(grupo_components)

    stats_base = {
        'grupo_id': grupo_id,
        'requeridas': n_parcelas,
        'generadas': 0
    }

    if n_parcelas < 1:
        logger.info(f"Grupo {grupo_id}: no requiere parcelas.")
        return {'points': [], 'stats': stats_base}

    logger.info(
        f"Procesando grupo {grupo_id} - Parcelas requeridas: {n_parcelas}")

    # Extraer subpolígonos
    mask = True
    for col in fields + ['gridcode']:
        if col in gdf_exploded.columns and col in group:
            mask = mask & (gdf_exploded[col] == group[col])

    subpoligonos = gdf_exploded[mask]
    if len(subpoligonos) == 0:
        logger.warning(f"No se encontraron subpolígonos para {grupo_id}")
        return {'points': [], 'stats': stats_base}

    geometria_grupo = subpoligonos.geometry.unary_union

    # Generar puntos
    puntos_candidatos = []
    for _, subpoly in subpoligonos.iterrows():
        pts = generar_grid_puntos(subpoly.geometry, spacing)
        pts_filtrados = filtrar_puntos_por_poligono(pts, subpoly.geometry)
        puntos_candidatos.extend(pts_filtrados)

    if not puntos_candidatos:
        logger.warning(f"No se encontraron puntos válidos para {grupo_id}")
        return {'points': [], 'stats': stats_base}

    logger.info(
        f"Puntos candidatos para {grupo_id}: {len(puntos_candidatos)}")

    # Seleccionar
    puntos_seleccionados = seleccionar_puntos_aleatorios(
        puntos_candidatos, n_parcelas, min_distance, max_intentos)
    puntos_validos = []
    
    for pt in puntos_seleccionados:
        if geometria_grupo.contains(
            pt) and not geometria_grupo.boundary.contains(pt):
            atributos = {f: group.get(f) for f in fields if f in group}
            if 'gridcode' in group:
                atributos['gridcode'] = group.get('gridcode')
            atributos.update({
                'geometry': pt,
                'grupo_id': grupo_id
            })
            puntos_validos.append(atributos)

    stats_base['generadas'] = len(puntos_validos)
    return {'points': puntos_validos, 'stats': stats_base}


def generar_parcelas(
    gdf: gpd.GeoDataFrame,
    fields: List[str],
    min_distance: float,
    output_path: str,
    spacing: float = 5.0,
    max_intentos: int = 30,
    spacing_retry_factor: float = 0.5
) -> gpd.GeoDataFrame:
    """
    Genera parcelas (puntos) a partir de un GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame con áreas para generar parcelas
        fields: Lista de campos para agrupar
        min_distance: Distancia mínima entre parcelas
        output_path: Ruta para guardar el resultado
        spacing: Espaciado entre puntos candidatos
        max_intentos: Número máximo de intentos
        spacing_retry_factor: Factor para reducir el espaciado en reintentos
        
    Returns:
        GeoDataFrame con las parcelas generadas
    """
    logger.info("Iniciando generación de parcelas (puntos)...")

    # Explode
    gdf_exploded = gdf.explode(index_parts=True).reset_index(drop=True)

    n_workers = cpu_count()
    logger.info(f"Procesando en paralelo con {n_workers} workers")
    process_func = partial(
        procesar_grupo,
        gdf_exploded=gdf_exploded,
        fields=fields,
        spacing=spacing,
        min_distance=min_distance,
        max_intentos=max_intentos
    )

    results = []
    with Pool(n_workers) as pool:
        results = pool.map(process_func, gdf.iterrows())

    all_points = []
    stats = []
    total_req = 0
    total_gen = 0
    for r in results:
        all_points.extend(r['points'])
        stats.append(r['stats'])
        total_req += r['stats']['requeridas']
        total_gen += r['stats']['generadas']

    # Reintento para grupos fallidos
    grupos_fallidos = [s for s in stats if s['generadas']
        < s['requeridas'] and s['requeridas'] > 0]
    if grupos_fallidos:
        logger.info("=== REINTENTO PARA GRUPOS FALLIDOS ===")
        new_spacing = spacing * spacing_retry_factor
        logger.info(f"Spacing reducido: {new_spacing}")

        retry_func = partial(
            procesar_grupo,
            gdf_exploded=gdf_exploded,
            fields=fields,
            spacing=new_spacing,
            min_distance=min_distance,
            max_intentos=max_intentos
        )

        with Pool(n_workers) as pool:
            retry_results = pool.map(
                retry_func,
                [(None, gf) for gf in grupos_fallidos]
            )
        for rr in retry_results:
            all_points.extend(rr['points'])
            total_gen += rr['stats']['generadas']
            for i, st in enumerate(stats):
                if st['grupo_id'] == rr['stats']['grupo_id']:
                    stats[i]['generadas'] = rr['stats']['generadas']

    logger.info("=== RESUMEN FINAL DE GENERACIÓN DE PARCELAS ===")
    logger.info(f"Total grupos procesados: {len(stats)}")
    logger.info(f"Parcelas requeridas: {total_req}, generadas: {total_gen}")
    if total_req > 0:
        logger.info(f"Porcentaje de éxito: {100*total_gen/total_req:.2f}%")

    if all_points:
        points_gdf = gpd.GeoDataFrame(
            all_points, geometry='geometry', crs=gdf.crs)
        logger.info(f"Guardando {len(points_gdf)} puntos en {output_path}")
        pyogrio.write_dataframe(points_gdf, output_path)
        return points_gdf
    else:
        logger.warning("No se generaron puntos")
        return gpd.GeoDataFrame(
            [],
            columns=['geometry'],
            geometry='geometry',
            crs=gdf.crs)


def generar_poligonos_parcelas(
    points_gdf: gpd.GeoDataFrame,
    area_parcela: float,
    id_parcela_inicio: int,
    version_parcela: str,
    fields: List[str],
    output_path: str
) -> gpd.GeoDataFrame:
    """
    Genera polígonos circulares a partir de puntos.
    
    Args:
        points_gdf: GeoDataFrame con puntos
        area_parcela: Área de la parcela en m²
        id_parcela_inicio: ID inicial para las parcelas
        version_parcela: Versión para el ID de parcela
        fields: Lista de campos a conservar
        output_path: Ruta para guardar el resultado
        
    Returns:
        GeoDataFrame con los polígonos generados
    """
    logger.info("Generando polígonos circulares...")
    radio = math.sqrt(area_parcela / math.pi)
    
    # Verificar y mostrar las columnas disponibles
    logger.info(f"Columnas disponibles en points_gdf: {points_gdf.columns.tolist()}")

    # Asegurar que tenemos las coordenadas
    points_gdf['x'] = points_gdf.geometry.x
    points_gdf['y'] = points_gdf.geometry.y
    
    # Crear lista de polígonos
    polygons = []
    current_id = id_parcela_inicio

    # Determinar columnas de agrupación disponibles
    group_cols = []
    if 'tipouso' in points_gdf.columns:
        group_cols.append('tipouso')
    if 'gridcode' in points_gdf.columns:
        group_cols.append('gridcode')

    # Si no hay columnas para agrupar, procesar todos los puntos juntos
    if not group_cols:
        logger.warning("No se encontraron columnas de agrupación (tipouso/gridcode). Procesando todos los puntos juntos.")
        points_gdf = points_gdf.sort_values(by=['x', 'y'])
        
        for idx, row in points_gdf.iterrows():
            circle = row.geometry.buffer(radio)
            id_parcela = f"default_{str(current_id+1).zfill(4)}"
            if version_parcela:
                id_parcela = f"default_{version_parcela}_{str(current_id+1).zfill(4)}"
            
            poligono = {
                'geometry': circle,
                'tipouso': 'default',
                'gridcode': None,
                'grupo_id': row.get('grupo_id', None),
                'id_parcela': id_parcela,
                'area_m2': area_parcela,
                'punto_x': row.x,
                'punto_y': row.y
            }
            # Copiar campos adicionales si existen
            for f in fields:
                if f in row:
                    poligono[f] = row[f]
            
            polygons.append(poligono)
            current_id += 1
    else:
        # Procesar por grupos si hay columnas de agrupación
        grouped = points_gdf.groupby(group_cols)
        for gkeys, group in grouped:
            group = group.sort_values(by=['x', 'y'])
            
            # Manejar tanto tuplas como valores únicos en las claves de grupo
            if isinstance(gkeys, tuple):
                values = gkeys
            else:
                values = (gkeys,)
            
            # Construir el ID de parcela
            id_base = "_".join(str(v) for v in values if v is not None)
            
            for _, row in group.iterrows():
                circle = row.geometry.buffer(radio)
                id_parcela = id_base
                if version_parcela:
                    id_parcela += f"_{version_parcela}"
                id_parcela += f"_{str(current_id+1).zfill(4)}"
                
                poligono = {
                    'geometry': circle,
                    'id_parcela': id_parcela,
                    'area_m2': area_parcela,
                    'punto_x': row.x,
                    'punto_y': row.y,
                    'grupo_id': row.get('grupo_id', None)
                }
                
                # Agregar valores de las columnas de agrupación
                for col, val in zip(group_cols, values):
                    poligono[col] = val
                
                # Copiar campos adicionales si existen
                for f in fields:
                    if f in row:
                        poligono[f] = row[f]
                
                polygons.append(poligono)
                current_id += 1

    # Crear GeoDataFrame con los polígonos
    if polygons:
        parcelas_gdf = gpd.GeoDataFrame(polygons, crs=points_gdf.crs)
        logger.info(f"Guardando {len(parcelas_gdf)} polígonos en {output_path}")
        pyogrio.write_dataframe(parcelas_gdf, output_path)
        return parcelas_gdf
    else:
        logger.warning("No se generaron polígonos")
        empty_gdf = gpd.GeoDataFrame([], columns=['geometry'], geometry='geometry', crs=points_gdf.crs)
        return empty_gdf 