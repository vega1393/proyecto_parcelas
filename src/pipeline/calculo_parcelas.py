"""
Módulo para el cálculo de la cantidad de parcelas necesarias de forma robusta.
"""

import logging
import geopandas as gpd
import pandas as pd
import pyogrio
from typing import Dict, Any, Optional, List

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
    output_gpkg_dissolved_initial: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    Calcula la cantidad de parcelas necesarias por grupo, manejando de forma
    robusta los datos de entrada antes de agrupar.
    
    Args:
        gdf: GeoDataFrame con los datos a procesar.
        fields: Lista de campos para agrupar.
        ... (resto de los argumentos) ...
        
    Returns:
        GeoDataFrame con la cantidad de parcelas calculada.
    """
    logger.info("Iniciando cálculo de cantidad de parcelas...")

    # 1) Validar y preparar columnas de agrupación
    available_cols = [col for col in fields if col in gdf.columns]
    missing_cols = set(fields) - set(available_cols)
    if missing_cols:
        logger.warning(f"Las siguientes columnas de agrupación no se encontraron y serán ignoradas: {list(missing_cols)}")

    if not available_cols:
        logger.error("No se especificaron columnas de agrupación válidas. No se puede continuar con el cálculo.")
        return gpd.GeoDataFrame() # Devolver GDF vacío si no hay por qué agrupar

    group_cols = available_cols

    # Copia de seguridad para no modificar el GeoDataFrame original que se usa en otros pasos
    gdf_cleaned = gdf.copy()

    # 2) [CORRECCIÓN CLAVE] Limpiar los datos ANTES de agrupar.
    #    Esto previene errores en `dissolve` si hay valores nulos (NaN).
    logger.info(f"Limpiando y preparando columnas de agrupación para dissolve: {group_cols}")
    for col in group_cols:
        # La forma más segura es convertir toda la columna a string para asegurar un tipo de dato
        # consistente y luego rellenar los nulos. Así, `NaN` se convierte en un grupo más.
        if pd.api.types.is_numeric_dtype(gdf_cleaned[col]):
            # Para numéricos, rellenar con un valor que no interfiera.
            gdf_cleaned[col] = gdf_cleaned[col].fillna(-9999)
        else:
            # Para texto u otros, rellenar con 'N/A'.
            gdf_cleaned[col] = gdf_cleaned[col].fillna('N/A')

    # 3) Primer `dissolve` con los datos ya limpios
    logger.info("Realizando primer dissolve para cálculo de n_parcelas...")
    dissolved_initial = gdf_cleaned.dissolve(by=group_cols, as_index=False)
    dissolved_initial['area_m2'] = dissolved_initial.geometry.area
    dissolved_initial['area_ha'] = dissolved_initial['area_m2'] / 10_000

    logger.info(f"Dissolve inicial completado. Se crearon {len(dissolved_initial)} grupos.")
    if dissolved_initial.empty:
        logger.error("El dissolve inicial no produjo ningún grupo, incluso después de limpiar los datos. Revisa la lógica de agrupación y los filtros previos.")
        return gpd.GeoDataFrame()

    # 4) Calcular n_parcelas (lógica sin cambios)
    if use_intensidad_especifica:
        def get_intensidad_especifica(row):
            for campo, intensidades in intensidad_por_campo.items():
                if campo in row and row[campo] in intensidades:
                    return intensidades[row[campo]]
            return intensidad
        dissolved_initial['intensidad'] = dissolved_initial.apply(get_intensidad_especifica, axis=1)
    else:
        dissolved_initial['intensidad'] = intensidad
    
    dissolved_initial['n_parcelas'] = (dissolved_initial['area_ha'] / dissolved_initial['intensidad']).round().astype(int)
    dissolved_initial['n_parcelas'] = dissolved_initial['n_parcelas'].apply(lambda x: max(x, 1) if x > 0 else 0)

    if min_parcelas is not None:
        dissolved_initial['n_parcelas'] = dissolved_initial['n_parcelas'].clip(lower=min_parcelas)
    if max_parcelas is not None:
        dissolved_initial['n_parcelas'] = dissolved_initial['n_parcelas'].clip(upper=max_parcelas)

    keep_cols = [col for col in group_cols + ['area_ha', 'area_m2', 'n_parcelas', 'intensidad', 'geometry'] if col in dissolved_initial.columns]
    dissolved_initial = dissolved_initial[keep_cols]

    # 5) Guardar resultados intermedios
    if output_gpkg_dissolved_initial:
        logger.info(f"Generando GPKG con el disuelto inicial en: {output_gpkg_dissolved_initial}")
        pyogrio.write_dataframe(dissolved_initial, output_gpkg_dissolved_initial, driver='GPKG', layer='dissolved_inicial')

    if output_csv:
        logger.info(f"Generando CSV con resultados iniciales en: {output_csv}")
        export_cols = [col for col in group_cols + ['area_ha', 'area_m2', 'n_parcelas', 'intensidad'] if col in dissolved_initial.columns]
        dissolved_initial[export_cols].to_csv(output_csv, index=False)

    # 6) Aplicar filtros de píxeles y segundo dissolve
    logger.info(f"Registros antes de filtrar píxeles incompletos: {len(gdf_cleaned)}")
    gdf_filtered = gdf_cleaned.copy()
    gdf_filtered['area_m2'] = gdf_filtered.geometry.area
    gdf_filtered = gdf_filtered[gdf_filtered['area_m2'] >= 399].copy()
    logger.info(f"Registros después de filtrar <399 m2: {len(gdf_filtered)}")

    p95_field = "p95"
    if p95_field in gdf_filtered.columns:
        logger.info(f"Registros antes de filtrar píxeles p95<{2}: {len(gdf_filtered)}")
        gdf_filtered[p95_field] = pd.to_numeric(gdf_filtered[p95_field], errors='coerce').fillna(0)
        gdf_filtered = gdf_filtered[gdf_filtered[p95_field] >= 2].copy()
        logger.info(f"Registros después de filtrar p95<{2}: {len(gdf_filtered)}")

    if gdf_filtered.empty:
        logger.warning("No hay registros después de los filtros de píxeles. El resultado final estará vacío.")
        return gpd.GeoDataFrame()

    dissolved_final = gdf_filtered.dissolve(by=group_cols, as_index=False)
    dissolved_final['area_m2'] = dissolved_final.geometry.area
    dissolved_final['area_ha'] = dissolved_final['area_m2'] / 10_000
    
    # Unir para obtener n_parcelas y otros datos del dissolve inicial
    merge_cols = [col for col in group_cols + ['area_ha', 'intensidad', 'n_parcelas'] if col in dissolved_initial.columns]
    dissolved_initial_for_merge = dissolved_initial[merge_cols].rename(columns={'area_ha': 'area_ha_original'})
    
    dissolved_final = dissolved_final.merge(dissolved_initial_for_merge, on=group_cols, how='left')
    dissolved_final.rename(columns={'area_ha': 'area_ha_post_filtros'}, inplace=True)
    
    # Asegurar que n_parcelas no sea nulo después del merge
    dissolved_final['n_parcelas'] = dissolved_final['n_parcelas'].fillna(0).astype(int)

    # 7) Filtrar por área mínima y aplicar buffer
    logger.info(f"Registros antes de filtrar por área mínima de {area_minima_ha} ha: {len(dissolved_final)}")
    dissolved_final = dissolved_final[dissolved_final['area_ha_post_filtros'] >= area_minima_ha].copy()
    logger.info(f"Registros después de filtrar por área mínima: {len(dissolved_final)}")

    if dissolved_final.empty:
        logger.warning("Ningún grupo cumple el criterio de área mínima. El resultado final estará vacío.")
        if output_gpkg:
             # Guardar un archivo vacío para consistencia en el pipeline
             gpd.GeoDataFrame([], geometry=[]).to_file(output_gpkg, driver='GPKG')
        return gpd.GeoDataFrame()

    if output_gpkg:
        logger.info(f"Aplicando buffer negativo de {buffer_distance}m...")
        dissolved_final_buffer = dissolved_final.copy()
        dissolved_final_buffer.geometry = dissolved_final_buffer.geometry.buffer(buffer_distance, resolution=16)
        dissolved_final_buffer = dissolved_final_buffer[~dissolved_final_buffer.geometry.is_empty].copy()
        dissolved_final_buffer['area_m2'] = dissolved_final_buffer.geometry.area
        dissolved_final_buffer['area_ha_descuento_buff'] = dissolved_final_buffer['area_m2'] / 10000

        logger.info(f"Guardando capa con buffer en: {output_gpkg}")
        pyogrio.write_dataframe(dissolved_final_buffer, output_gpkg, driver='GPKG', layer=f'dissolved_final_neg{abs(buffer_distance)}')
        return dissolved_final_buffer

    return dissolved_final