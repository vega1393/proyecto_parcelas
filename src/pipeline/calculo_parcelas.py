"""
Módulo para el cálculo de la cantidad de parcelas necesarias.
"""

import logging
import geopandas as gpd
import pyogrio
from typing import Dict, Any, Optional, List, Tuple

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
    Calcula la cantidad de parcelas necesarias por grupo.
    
    Args:
        gdf: GeoDataFrame con los datos a procesar
        fields: Lista de campos para agrupar
        intensidad: Intensidad base (ha por parcela)
        use_intensidad_especifica: Si usar intensidades específicas por campo
        intensidad_por_campo: Diccionario con intensidades específicas
        min_parcelas: Mínimo de parcelas por grupo (opcional)
        max_parcelas: Máximo de parcelas por grupo (opcional)
        area_minima_ha: Área mínima en hectáreas
        buffer_distance: Distancia de buffer en metros
        output_csv: Ruta para guardar CSV (opcional)
        output_gpkg: Ruta para guardar GPKG (opcional)
        output_gpkg_dissolved_initial: Ruta para guardar GPKG inicial (opcional)
        
    Returns:
        GeoDataFrame con la cantidad de parcelas calculada
    """
    logger.info("Calculando cantidad de parcelas...")

    # 1) Determinar columnas de agrupación
    group_cols = fields.copy()
    if 'gridcode' in gdf.columns:
        group_cols.append('gridcode')

    # 2) Primer dissolve
    dissolved_initial = gdf.dissolve(by=group_cols, as_index=False)
    dissolved_initial['area_m2'] = dissolved_initial.geometry.area
    dissolved_initial['area_ha'] = dissolved_initial['area_m2'] / 10_000

    # 3) Calcular n_parcelas
    if use_intensidad_especifica:
        def get_intensidad_especifica(row):
            for campo, intensidades in intensidad_por_campo.items():
                if campo in row and row[campo] in intensidades:
                    return intensidades[row[campo]]
            return intensidad
        
        dissolved_initial['intensidad'] = dissolved_initial.apply(
            get_intensidad_especifica, axis=1)
        dissolved_initial['n_parcelas'] = (
            dissolved_initial['area_ha'] / 
            dissolved_initial['intensidad']).round().astype(int)
    else:
        dissolved_initial['intensidad'] = intensidad
        dissolved_initial['n_parcelas'] = (
            dissolved_initial['area_ha'] / 
            intensidad).round().astype(int)

    # Forzar mínimo 1 si no es cero
    dissolved_initial['n_parcelas'] = dissolved_initial['n_parcelas'].apply(
        lambda x: max(x, 1) if x > 0 else 0
    )

    if min_parcelas is not None:
        dissolved_initial['n_parcelas'] = dissolved_initial['n_parcelas'].apply(
            lambda x: max(x, min_parcelas)
        )
    if max_parcelas is not None:
        dissolved_initial['n_parcelas'] = dissolved_initial['n_parcelas'].apply(
            lambda x: min(x, max_parcelas)
        )

    keep_cols = group_cols + ['area_ha', 'area_m2',
        'n_parcelas', 'intensidad', 'geometry']
    dissolved_initial = dissolved_initial[keep_cols].copy()

    # Guardar disuelto inicial
    if output_gpkg_dissolved_initial:
        logger.info(
            f"Generando GPKG con el disuelto inicial en: {output_gpkg_dissolved_initial}")
        pyogrio.write_dataframe(
            dissolved_initial,
            output_gpkg_dissolved_initial,
            driver='GPKG',
            layer='dissolved_inicial'
        )

    # Guardar CSV
    if output_csv:
        logger.info(
            f"Generando CSV con resultados iniciales en: {output_csv}")
        export_cols = group_cols + ['area_ha',
            'area_m2', 'n_parcelas', 'intensidad']
        dissolved_initial[export_cols].to_csv(output_csv, index=False)

    # 4) Filtrar píxeles <399 m2
    logger.info(f"Registros antes de filtrar píxeles incompletos: {len(gdf)}")
    gdf_filtered = gdf.copy()
    gdf_filtered['area_m2'] = gdf_filtered.geometry.area
    gdf_filtered = gdf_filtered[gdf_filtered['area_m2'] >= 399].copy()
    logger.info(f"Registros después de filtrar <399 m2: {len(gdf_filtered)}")

    # 4.1) Filtrar p95<2
    p95_field = "p95"  # Asumimos que este es el campo estándar
    if p95_field in gdf_filtered.columns:
        logger.info(
            f"Registros antes de filtrar píxeles p95<2: {len(gdf_filtered)}")
        gdf_filtered[p95_field] = gdf_filtered[p95_field].astype(float)
        gdf_filtered = gdf_filtered[gdf_filtered[p95_field] >= 2].copy()
        logger.info(
            f"Registros después de filtrar p95<2: {len(gdf_filtered)}")

    # 5) Segundo dissolve
    dissolved_final = gdf_filtered.dissolve(by=group_cols, as_index=False)
    dissolved_final['area_m2'] = dissolved_final.geometry.area
    dissolved_final['area_ha'] = dissolved_final['area_m2'] / 10_000

    dissolved_initial_for_merge = dissolved_initial[group_cols + [
        'area_ha', 'intensidad']].copy()
    dissolved_initial_for_merge = dissolved_initial_for_merge.rename(
        columns={'area_ha': 'area_ha_original'})
    dissolved_final = dissolved_final.merge(
        dissolved_initial_for_merge, on=group_cols, how='left')
    dissolved_final.rename(
        columns={
            'area_ha': 'area_ha_post_filtros'},
            inplace=True)

    dissolved_final = dissolved_final.merge(
        dissolved_initial[group_cols + ['n_parcelas']],
        on=group_cols,
        how='left'
    )

    keep_cols = group_cols + ['area_ha_original',
        'area_ha_post_filtros',
        'n_parcelas',
        'intensidad',
        'geometry']
    dissolved_final = dissolved_final[keep_cols].copy()

    # 5.1) Filtrar por area minima
    logger.info(
        f"Registros antes de filtrar area minima ha: {len(dissolved_final)}")
    dissolved_final = dissolved_final[dissolved_final['area_ha_post_filtros']
        >= area_minima_ha].copy()
    logger.info(
        f"Registros después de filtrar area minima {area_minima_ha} ha: {len(dissolved_final)}")

    # 6) Buffer negativo
    if output_gpkg:
        logger.info(f"Aplicando buffer negativo de {buffer_distance}m...")
        dissolved_final_buffer = dissolved_final.copy()
        dissolved_final_buffer.geometry = dissolved_final_buffer.geometry.buffer(
            buffer_distance)
        dissolved_final_buffer = dissolved_final_buffer[~dissolved_final_buffer.geometry.is_empty].copy(
        )
        dissolved_final_buffer['area_m2'] = dissolved_final_buffer.geometry.area
        dissolved_final_buffer['area_ha_descuento_buff'] = dissolved_final_buffer['area_m2'] / 10000

        logger.info(f"Guardando capa con buffer en: {output_gpkg}")
        try:
            pyogrio.write_dataframe(
                dissolved_final_buffer,
                output_gpkg,
                driver='GPKG',
                layer=f'dissolved_final_neg{abs(buffer_distance)}'
            )
        except Exception as e:
            logger.error(f"Error al guardar GPKG: {str(e)}")
            shp_path = output_gpkg.replace('.gpkg', '.shp')
            logger.info(f"Intentando guardar como shapefile: {shp_path}")
            pyogrio.write_dataframe(dissolved_final_buffer, shp_path)

        dissolved_final = dissolved_final_buffer

    return dissolved_final 