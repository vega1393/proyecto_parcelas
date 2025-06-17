"""
Módulo para el análisis de pérdidas de parcelas entre etapas.
"""

import logging
import pandas as pd
import geopandas as gpd
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


def analizar_perdidas_parcelas(
    gdf_inicial: gpd.GeoDataFrame,
    fields: List[str],
    gdf_post_filtros: Optional[gpd.GeoDataFrame] = None,
    gdf_post_exclusion: Optional[gpd.GeoDataFrame] = None,
    gdf_final: Optional[gpd.GeoDataFrame] = None,
    output_csv: Optional[str] = None
) -> pd.DataFrame:
    """
    Reporta pérdidas de parcelas entre etapas.
    
    Args:
        gdf_inicial: GeoDataFrame inicial con la cantidad de parcelas planificadas
        fields: Lista de campos para identificar grupos
        gdf_post_filtros: GeoDataFrame después de aplicar filtros (opcional)
        gdf_post_exclusion: GeoDataFrame después de aplicar exclusiones (opcional)
        gdf_final: GeoDataFrame con las parcelas finales generadas (opcional)
        output_csv: Ruta para guardar el CSV de análisis (opcional)
        
    Returns:
        DataFrame con el análisis de pérdidas
    """
    def get_grupo_id(row):
        components = []
        for field in fields + ['gridcode']:
            if field in row:
                components.append(f"{field}: {row[field]}")
        return " | ".join(components)

    gdf_inicial['grupo_id'] = gdf_inicial.apply(get_grupo_id, axis=1)
    
    # Verificar que existan las columnas necesarias
    required_cols = ['grupo_id', 'area_ha', 'n_parcelas', 'intensidad']
    available_cols = [col for col in required_cols if col in gdf_inicial.columns]
    
    if 'n_parcelas' not in gdf_inicial.columns:
        logger.error("Columna 'n_parcelas' no encontrada en gdf_inicial. Análisis de pérdidas no puede continuar.")
        return pd.DataFrame()  # Retornar DataFrame vacío
    
    grupos_inicial = gdf_inicial[available_cols].copy()
    grupos_inicial_con_parcelas = grupos_inicial[grupos_inicial['n_parcelas'] > 0]
    analisis_df = grupos_inicial_con_parcelas.copy()
    analisis_df['parcelas_post_filtros'] = 0
    analisis_df['parcelas_post_exclusion'] = 0
    analisis_df['parcelas_generadas'] = 0

    if gdf_post_filtros is not None:
        gdf_post_filtros['grupo_id'] = gdf_post_filtros.apply(
            get_grupo_id, axis=1)
        for idx in analisis_df.index:
            gid = analisis_df.loc[idx, 'grupo_id']
            gf = gdf_post_filtros[gdf_post_filtros['grupo_id'] == gid]
            if not gf.empty and 'n_parcelas' in gf.columns:
                analisis_df.loc[idx,
     'parcelas_post_filtros'] = gf['n_parcelas'].iloc[0]
            elif not gf.empty:
                logger.warning(f"Columna 'n_parcelas' no encontrada en gdf_post_filtros para grupo {gid}")
                analisis_df.loc[idx, 'parcelas_post_filtros'] = 0

    if gdf_post_exclusion is not None:
        gdf_post_exclusion['grupo_id'] = gdf_post_exclusion.apply(
            get_grupo_id, axis=1)
        for idx in analisis_df.index:
            gid = analisis_df.loc[idx, 'grupo_id']
            gf = gdf_post_exclusion[gdf_post_exclusion['grupo_id'] == gid]
            if not gf.empty and 'n_parcelas' in gf.columns:
                analisis_df.loc[idx,
     'parcelas_post_exclusion'] = gf['n_parcelas'].iloc[0]
            elif not gf.empty:
                logger.warning(f"Columna 'n_parcelas' no encontrada en gdf_post_exclusion para grupo {gid}")
                analisis_df.loc[idx, 'parcelas_post_exclusion'] = 0

    if gdf_final is not None:
        gdf_final['grupo_id'] = gdf_final.apply(get_grupo_id, axis=1)
        conteo = gdf_final['grupo_id'].value_counts()
        for idx in analisis_df.index:
            gid = analisis_df.loc[idx, 'grupo_id']
            analisis_df.loc[idx, 'parcelas_generadas'] = conteo.get(gid, 0)

    analisis_df['diferencia_final'] = analisis_df['n_parcelas'] - \
        analisis_df['parcelas_generadas']
    
    if output_csv:
        analisis_df.to_csv(output_csv, index=False)

    total_planificadas = analisis_df['n_parcelas'].sum()
    total_generadas = analisis_df['parcelas_generadas'].sum()
    diferencia = total_planificadas - total_generadas
    
    logger.info("=== Análisis de pérdidas de parcelas ===")
    logger.info(
        f"Total planificadas: {total_planificadas}, generadas: {total_generadas}")
    if diferencia > 0:
        logger.info(f"Parcelas no generadas: {diferencia}")
    else:
        logger.info("No hubo pérdidas finales.")
        
    return analisis_df 