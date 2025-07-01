"""
Módulo para el cálculo de la cantidad de parcelas necesarias de forma robusta.
"""

import logging
import geopandas as gpd
import pandas as pd
import pyogrio
from typing import Dict, Any, Optional, List, Tuple
from .distribucion_total import calcular_distribucion_proporcional

logger = logging.getLogger(__name__)


def calcular_cantidad_de_parcelas(
    gdf: gpd.GeoDataFrame,
    fields: List[str],
    intensidad: int,
    use_intensidad_especifica: bool,
    intensidad_por_campo: Dict[str, Dict[str, int]],
    min_parcelas: Optional[int],
    max_parcelas: Optional[int],
    area_minima_ha: float,
    buffer_distance: int,
    output_csv: Optional[str] = None,
    output_gpkg: Optional[str] = None,
    output_gpkg_dissolved_initial: Optional[str] = None,
    # Nuevos parámetros para total-based
    use_total_based: bool = False,
    total_parcels: Optional[int] = None,
    minimum_config: Optional[Dict[str, Any]] = None,
    campos_metricas: Optional[Dict[str, str]] = None,
    use_original_area: bool = True  # DEPRECATED en la lógica, se mantiene por firma
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Calcula la cantidad de parcelas necesarias por grupo.
    REFACTORIZADO (v2): La lógica ahora aplica filtros y buffer ANTES de
    distribuir las parcelas para máxima precisión.
    
    Args:
        gdf: GeoDataFrame con los datos a procesar.
        fields: Lista de campos para agrupar.
        intensidad: Intensidad base (hectáreas por parcela).
        use_intensidad_especifica: Si usar intensidades específicas por campo.
        intensidad_por_campo: Diccionario con intensidades específicas.
        min_parcelas: Número mínimo de parcelas por grupo.
        max_parcelas: Número máximo de parcelas por grupo.
        area_minima_ha: Área mínima en hectáreas para incluir un grupo.
        buffer_distance: Distancia de buffer en metros.
        output_csv: Ruta para guardar CSV de resultados.
        output_gpkg: Ruta para guardar GPKG final.
        output_gpkg_dissolved_initial: Ruta para guardar GPKG de diagnóstico.
        use_total_based: Si usar distribución proporcional total.
        total_parcels: Número total de parcelas a distribuir (solo total-based).
        minimum_config: Configuración de mínimo por grupo (solo total-based).
        campos_metricas: Diccionario con nombres de campos para cálculos específicos.
        use_original_area: (Ignorado) Se mantiene por compatibilidad.
        
    Returns:
        Tuple con dos GeoDataFrames: el primero es el resultado final y el segundo es la copia inicial antes de aplicar los filtros.
    """
    logger.info("Iniciando cálculo de cantidad de parcelas (lógica V2: Filtros->Buffer->Distribución)...")

    # --- PASO 1: Validación y limpieza de columnas de agrupación ---
    available_cols = [col for col in fields if col in gdf.columns]
    if not available_cols:
        logger.error("No se especificaron columnas de agrupación válidas. No se puede continuar.")
        return gpd.GeoDataFrame(), gpd.GeoDataFrame()
    group_cols = available_cols
    
    gdf_processed = gdf.copy()
    logger.info(f"Limpiando columnas de agrupación: {group_cols}")
    for col in group_cols:
        if pd.api.types.is_numeric_dtype(gdf_processed[col]):
            gdf_processed[col] = gdf_processed[col].fillna(-9999)
        else:
            gdf_processed[col] = gdf_processed[col].fillna('N/A')

    # --- PASO 2: Filtrado de calidad de píxeles ---
    logger.info(f"Registros antes de filtrar por calidad de píxeles: {len(gdf_processed)}")
    gdf_processed['area_m2_pixel'] = gdf_processed.geometry.area
    gdf_filtered_pixels = gdf_processed[gdf_processed['area_m2_pixel'] >= 399].copy()
    logger.info(f"Registros después de filtrar <399 m2: {len(gdf_filtered_pixels)}")

    # [CORREGIDO] Usar el nombre del campo p95 desde la configuración
    p95_field = "p95" # Valor por defecto
    if campos_metricas:
        p95_field = campos_metricas.get("p95", "p95")

    if p95_field in gdf_filtered_pixels.columns:
        p95_before_count = len(gdf_filtered_pixels)
        gdf_filtered_pixels[p95_field] = pd.to_numeric(gdf_filtered_pixels[p95_field], errors='coerce').fillna(0)
        gdf_filtered_pixels = gdf_filtered_pixels[gdf_filtered_pixels[p95_field] >= 2].copy()
        logger.info(f"Registros antes de filtrar píxeles p95<2: {p95_before_count}")
        logger.info(f"Registros después de filtrar p95<2: {len(gdf_filtered_pixels)}")

    if gdf_filtered_pixels.empty:
        logger.warning("No hay registros después de los filtros de calidad de píxeles. El resultado estará vacío.")
        return gpd.GeoDataFrame(), gpd.GeoDataFrame()

    # --- PASO 3A: Agrupación inicial (Dissolve) SIN filtros de píxeles ---
    logger.info("Realizando dissolve inicial sobre TODOS los píxeles para crear grupos completos...")
    dissolved_gdf_initial = gdf_processed.dissolve(by=group_cols, as_index=False)
    dissolved_gdf_initial['area_m2_inicial'] = dissolved_gdf_initial.geometry.area
    dissolved_gdf_initial['area_ha_inicial'] = dissolved_gdf_initial['area_m2_inicial'] / 10_000
    logger.info(f"Dissolve inicial completado. Se crearon {len(dissolved_gdf_initial)} grupos COMPLETOS (sin filtros).")

    # --- PASO 3B: Agrupación sobre datos filtrados para procesamiento ---
    logger.info("Realizando dissolve sobre datos filtrados para procesamiento...")
    dissolved_gdf = gdf_filtered_pixels.dissolve(by=group_cols, as_index=False)
    dissolved_gdf['area_m2_pre_buffer'] = dissolved_gdf.geometry.area
    dissolved_gdf['area_ha_pre_buffer'] = dissolved_gdf['area_m2_pre_buffer'] / 10_000
    logger.info(f"Dissolve filtrado completado. Se crearon {len(dissolved_gdf)} grupos (post-filtros píxeles).")

    logger.info(f"Grupos antes de filtrar por área mínima ({area_minima_ha} ha): {len(dissolved_gdf)}")
    dissolved_gdf = dissolved_gdf[dissolved_gdf['area_ha_pre_buffer'] >= area_minima_ha].copy()
    logger.info(f"Grupos después de filtrar por área mínima: {len(dissolved_gdf)}")

    if dissolved_gdf.empty:
        logger.warning("Ningún grupo cumple el criterio de área mínima. El resultado estará vacío.")
        return gpd.GeoDataFrame(), dissolved_gdf_initial

    # --- PASO 4: Aplicación de buffer negativo y limpieza de geometrías ---
    logger.info(f"Aplicando buffer negativo de {buffer_distance}m a {len(dissolved_gdf)} grupos...")
    dissolved_gdf['geometry'] = dissolved_gdf.geometry.buffer(buffer_distance, resolution=16)
    
    # Filtrar geometrías vacías que resultan del buffer
    grupos_pre_buffer = len(dissolved_gdf)
    dissolved_gdf = dissolved_gdf[~dissolved_gdf.geometry.is_empty].copy()
    logger.info(f"{len(dissolved_gdf)} de {grupos_pre_buffer} grupos sobrevivieron al buffer.")

    if dissolved_gdf.empty:
        logger.warning("Todos los grupos fueron eliminados por el buffer. No hay áreas para generar parcelas.")
        return gpd.GeoDataFrame(), dissolved_gdf_initial
        
    dissolved_gdf['area_m2'] = dissolved_gdf.geometry.area
    dissolved_gdf['area_ha'] = dissolved_gdf['area_m2'] / 10_000
    
    # Guardar GPKG de diagnóstico (opcional) con las áreas INICIALES COMPLETAS
    if output_gpkg_dissolved_initial:
        logger.info(f"Guardando áreas agrupadas INICIALES COMPLETAS (todos los píxeles, sin filtros) en: {output_gpkg_dissolved_initial}")
        pyogrio.write_dataframe(dissolved_gdf_initial.reset_index(drop=True), output_gpkg_dissolved_initial, driver='GPKG', layer='areas_agrupadas_completas')

    # --- PASO 5: Distribución de parcelas sobre las áreas finales ---
    if use_total_based and total_parcels is not None:
        logger.info(f"🎯 Modo Total-based: distribuyendo {total_parcels} parcelas sobre los grupos sobrevivientes.")
        dissolved_gdf['intensidad'] = 0
        
        if minimum_config is None:
            minimum_config = {"type": "none", "value": 0.0}
        
        dissolved_gdf = calcular_distribucion_proporcional(
            dissolved_gdf,
            group_cols,
            total_parcels,
            minimum_config,
            use_original_area=False
        )
    elif intensidad == 0:
        logger.info("Modo CSV (intensidad=0): n_parcelas se asignará más tarde.")
        dissolved_gdf['intensidad'] = 0
        dissolved_gdf['n_parcelas'] = 0
    else: # Modo por intensidad
        logger.info("Modo Intensidad: calculando parcelas por hectárea sobre área post-buffer.")
        # Lógica de intensidad (se mantiene igual, pero opera sobre el área final)
        if use_intensidad_especifica:
            def get_intensidad_especifica(row):
                for campo, intensidades in intensidad_por_campo.items():
                    if campo in row and row[campo] in intensidades:
                        return intensidades[row[campo]]
                return intensidad
            dissolved_gdf['intensidad'] = dissolved_gdf.apply(get_intensidad_especifica, axis=1)
        else:
            dissolved_gdf['intensidad'] = intensidad
        
        dissolved_gdf['n_parcelas'] = (dissolved_gdf['area_ha'] / dissolved_gdf['intensidad']).round().astype(int)
        dissolved_gdf['n_parcelas'] = dissolved_gdf['n_parcelas'].apply(lambda x: max(x, 1) if x > 0 else 0)

        if min_parcelas is not None:
            dissolved_gdf['n_parcelas'] = dissolved_gdf['n_parcelas'].clip(lower=min_parcelas)
        if max_parcelas is not None:
            dissolved_gdf['n_parcelas'] = dissolved_gdf['n_parcelas'].clip(upper=max_parcelas)

    # --- PASO 6: Guardar CSV de resultados y devolver GDF listo para generación ---
    if output_csv:
        logger.info(f"Generando CSV con resultados finales en: {output_csv}")
        export_cols = [col for col in group_cols + ['area_ha', 'area_m2', 'n_parcelas', 'intensidad'] if col in dissolved_gdf.columns]
        dissolved_gdf[export_cols].to_csv(output_csv, index=False)

    if output_gpkg:
        logger.info(f"Guardando áreas FILTRADAS (post-área mínima y buffer) en: {output_gpkg}")
        # Estas son las áreas finales que sobrevivieron todos los filtros
        pyogrio.write_dataframe(dissolved_gdf.reset_index(drop=True), output_gpkg, driver='GPKG', layer=f'areas_filtradas_buffer_neg{abs(buffer_distance)}')
    
    return dissolved_gdf, dissolved_gdf_initial