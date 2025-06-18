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
    Analiza las pérdidas de parcelas en cada etapa del proceso.
    
    Args:
        gdf_inicial: GeoDataFrame inicial con áreas agrupadas
        fields: Campos de agrupación
        gdf_post_filtros: GeoDataFrame después de aplicar filtros (opcional)
        gdf_post_exclusion: GeoDataFrame después de exclusiones (opcional)
        gdf_final: GeoDataFrame final con parcelas generadas (opcional)
        output_csv: Ruta del archivo CSV de salida (opcional)
        
    Returns:
        DataFrame con el análisis de pérdidas por grupo
    """
    logger.debug("Iniciando análisis de pérdidas de parcelas...")
    
    # Crear un DataFrame base con los grupos iniciales y sus n_parcelas planificadas
    analisis_df = gdf_inicial[fields + ['n_parcelas']].copy()
    analisis_df = analisis_df.rename(columns={'n_parcelas': 'n_parcelas_inicial'})
    
    # Agregar información de áreas
    if 'area_ha' in gdf_inicial.columns:
        analisis_df['area_ha_inicial'] = gdf_inicial['area_ha']
    elif 'area_m2' in gdf_inicial.columns:
        analisis_df['area_ha_inicial'] = gdf_inicial['area_m2'] / 10000
    else:
        analisis_df['area_ha_inicial'] = gdf_inicial.geometry.area / 10000
    
    # Análisis post-filtros
    if gdf_post_filtros is not None:
        # Preparar diccionario de agregación dinámicamente
        agg_dict = {'n_parcelas': 'first'}
        
        # Solo agregar area_ha si existe en el DataFrame
        if 'area_ha' in gdf_post_filtros.columns:
            agg_dict['area_ha'] = 'first'
        
        post_filtros_summary = gdf_post_filtros.groupby(fields).agg(agg_dict).reset_index()
        
        # Si no tenemos area_ha, calcularla desde area_m2 o geometría
        if 'area_ha' not in post_filtros_summary.columns:
            if 'area_m2' in gdf_post_filtros.columns:
                area_ha_values = gdf_post_filtros.groupby(fields)['area_m2'].first().values / 10000
                post_filtros_summary['area_ha'] = area_ha_values
            else:
                area_ha_values = gdf_post_filtros.groupby(fields).apply(
                    lambda x: x.geometry.area.iloc[0] / 10000
                ).values
                post_filtros_summary['area_ha'] = area_ha_values
        
        # Merge con sufijos para evitar conflictos
        analisis_df = analisis_df.merge(
            post_filtros_summary, 
            on=fields, how='left', suffixes=('', '_post_filtros')
        )
        
        # Renombrar columnas con sufijos si es necesario
        if 'n_parcelas_post_filtros' in analisis_df.columns:
            analisis_df['n_parcelas_post_filtros'] = analisis_df['n_parcelas_post_filtros'].fillna(0)
        else:
            analisis_df['n_parcelas_post_filtros'] = analisis_df['n_parcelas'].fillna(0)
            
        if 'area_ha_post_filtros' in analisis_df.columns:
            analisis_df['area_ha_post_filtros'] = analisis_df['area_ha_post_filtros'].fillna(0)
        else:
            analisis_df['area_ha_post_filtros'] = analisis_df['area_ha'].fillna(0)
        
        # Limpiar columnas duplicadas
        analisis_df = analisis_df.drop(columns=['n_parcelas', 'area_ha'], errors='ignore')
    else:
        analisis_df['n_parcelas_post_filtros'] = analisis_df['n_parcelas_inicial']
        analisis_df['area_ha_post_filtros'] = analisis_df['area_ha_inicial']

    # Análisis post-exclusión
    if gdf_post_exclusion is not None:
        # Preparar diccionario de agregación dinámicamente
        agg_dict = {'n_parcelas': 'first'}
        
        # Verificar qué columna de área existe
        area_col = None
        if 'area_ha_post_exclusion' in gdf_post_exclusion.columns:
            area_col = 'area_ha_post_exclusion'
            agg_dict[area_col] = 'first'
        elif 'area_ha' in gdf_post_exclusion.columns:
            area_col = 'area_ha'
            agg_dict[area_col] = 'first'
        
        post_exclusion_summary = gdf_post_exclusion.groupby(fields).agg(agg_dict).reset_index()
        
        # Si no tenemos columna de área, calcularla
        if area_col is None:
            if 'area_m2' in gdf_post_exclusion.columns:
                area_ha_values = gdf_post_exclusion.groupby(fields)['area_m2'].first().values / 10000
                post_exclusion_summary['area_ha_post_exclusion'] = area_ha_values
            else:
                area_ha_values = gdf_post_exclusion.groupby(fields).apply(
                    lambda x: x.geometry.area.iloc[0] / 10000
                ).values
                post_exclusion_summary['area_ha_post_exclusion'] = area_ha_values
        elif area_col != 'area_ha_post_exclusion':
            # Renombrar la columna de área al nombre estándar
            post_exclusion_summary = post_exclusion_summary.rename(columns={area_col: 'area_ha_post_exclusion'})
        
        analisis_df = analisis_df.merge(post_exclusion_summary, on=fields, how='left')
        analisis_df['n_parcelas'] = analisis_df['n_parcelas'].fillna(0)
        analisis_df['area_ha_post_exclusion'] = analisis_df['area_ha_post_exclusion'].fillna(0)
    else:
        analisis_df['n_parcelas'] = analisis_df['n_parcelas_post_filtros']
        analisis_df['area_ha_post_exclusion'] = analisis_df['area_ha_post_filtros']
    
    # Análisis de parcelas finalmente generadas
    if gdf_final is not None:
        parcels_by_group = gdf_final.groupby(fields).size().reset_index(name='parcelas_generadas')
        analisis_df = analisis_df.merge(parcels_by_group, on=fields, how='left')
        analisis_df['parcelas_generadas'] = analisis_df['parcelas_generadas'].fillna(0)
    else:
        analisis_df['parcelas_generadas'] = 0

    # Calcular diferencias
    analisis_df['perdida_filtros'] = analisis_df['n_parcelas_inicial'] - analisis_df['n_parcelas_post_filtros']
    analisis_df['perdida_exclusion'] = analisis_df['n_parcelas_post_filtros'] - analisis_df['n_parcelas']
    analisis_df['diferencia_final'] = analisis_df['n_parcelas'] - analisis_df['parcelas_generadas']
    
    if output_csv:
        analisis_df.to_csv(output_csv, index=False)

    total_planificadas = analisis_df['n_parcelas'].sum()
    total_generadas = analisis_df['parcelas_generadas'].sum()
    diferencia = total_planificadas - total_generadas
    
    # Calcular estadísticas de grupos
    grupos_totales = len(analisis_df)
    grupos_completos = len(analisis_df[analisis_df['diferencia_final'] == 0])
    grupos_incompletos = len(analisis_df[analisis_df['diferencia_final'] > 0])
    grupos_sin_parcelas = len(analisis_df[analisis_df['parcelas_generadas'] == 0])
    
    logger.info("=" * 70)
    logger.info("=== ANÁLISIS DETALLADO DE PÉRDIDAS DE PARCELAS ===")
    logger.info("=" * 70)
    
    # Resumen general
    logger.info("RESUMEN GENERAL:")
    logger.info(f"   - Total grupos procesados: {grupos_totales}")
    logger.info(f"   - Total parcelas planificadas: {int(total_planificadas)}")
    logger.info(f"   - Total parcelas generadas: {int(total_generadas)}")
    logger.info(f"   - Tasa de exito: {(total_generadas/total_planificadas*100):.1f}%")
    
    if diferencia > 0:
        logger.info(f"   - Parcelas no generadas: {int(diferencia)}")
    else:
        logger.info("   - No hubo perdidas finales.")
    
    logger.info("")
    
    # Estadísticas de grupos
    logger.info("ANALISIS POR GRUPOS:")
    logger.info(f"   - Grupos completos (100%): {grupos_completos}/{grupos_totales} ({grupos_completos/grupos_totales*100:.1f}%)")
    logger.info(f"   - Grupos incompletos: {grupos_incompletos}/{grupos_totales} ({grupos_incompletos/grupos_totales*100:.1f}%)")
    logger.info(f"   - Grupos sin parcelas: {grupos_sin_parcelas}/{grupos_totales} ({grupos_sin_parcelas/grupos_totales*100:.1f}%)")
    
    logger.info("")
    
    # Mostrar tabla detallada si hay problemas o en modo DEBUG
    if diferencia > 0 or logger.isEnabledFor(logging.DEBUG):
        logger.info("TABLA DETALLADA POR GRUPO:")
        logger.info("-" * 70)
        
        # Encabezados de la tabla
        header = f"{'Grupo':<20} {'Plan.':<6} {'Gen.':<6} {'Dif.':<6} {'Estado':<10}"
        logger.info(header)
        logger.info("-" * 70)
        
        # Mostrar cada grupo
        for _, row in analisis_df.iterrows():
            # Crear identificador del grupo
            grupo_id = " | ".join([f"{field}:{row[field]}" for field in fields[:2]])  # Solo primeros 2 campos
            if len(grupo_id) > 18:
                grupo_id = grupo_id[:15] + "..."
            
            planificadas = int(row['n_parcelas'])
            generadas = int(row['parcelas_generadas'])
            diferencia_grupo = int(row['diferencia_final'])
            
            if diferencia_grupo == 0:
                estado = "OK COMPLETO"
            elif generadas == 0:
                estado = "SIN PARCELAS"
            else:
                estado = "INCOMPLETO"
            
            fila = f"{grupo_id:<20} {planificadas:<6} {generadas:<6} {diferencia_grupo:<6} {estado:<10}"
            logger.info(fila)
        
        logger.info("-" * 70)
    
    # Resumen de pérdidas por etapa
    if 'perdida_filtros' in analisis_df.columns and 'perdida_exclusion' in analisis_df.columns:
        perdidas_filtros = analisis_df['perdida_filtros'].sum()
        perdidas_exclusion = analisis_df['perdida_exclusion'].sum()
        
        logger.info("")
        logger.info("PERDIDAS POR ETAPA:")
        logger.info(f"   - Perdidas por filtros: {int(perdidas_filtros)}")
        logger.info(f"   - Perdidas por exclusiones: {int(perdidas_exclusion)}")
        logger.info(f"   - Perdidas por generacion: {int(diferencia)}")
    
    logger.info("=" * 70)
        
    return analisis_df 