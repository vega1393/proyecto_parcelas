"""
Módulo para el cálculo de distribución proporcional de parcelas.
Implementa la metodología "Total-based" para distribuir un número fijo 
de parcelas proporcionalmente según el área de cada grupo.
"""

import logging
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Any, Tuple
import math

logger = logging.getLogger(__name__)


def calcular_distribucion_proporcional(
    gdf: gpd.GeoDataFrame,
    grouping_fields: List[str],
    total_parcels: int,
    minimum_config: Dict[str, Any],
    use_original_area: bool = True
) -> gpd.GeoDataFrame:
    """
    Calcula la distribución proporcional de parcelas por grupo.
    
    Args:
        gdf: GeoDataFrame con los datos agrupados
        grouping_fields: Campos para agrupar
        total_parcels: Número total de parcelas a distribuir
        minimum_config: Configuración de mínimo por grupo
        use_original_area: Si usar área original o calculada
        
    Returns:
        GeoDataFrame con columna 'n_parcelas' actualizada
    """
    logger.info(f"🎯 Iniciando distribución proporcional de {total_parcels} parcelas")
    
    # Validar datos de entrada
    if gdf.empty:
        logger.warning("GeoDataFrame vacío, no se pueden distribuir parcelas")
        return gdf.copy()
    
    if total_parcels <= 0:
        logger.warning("Número de parcelas debe ser mayor a 0")
        return gdf.copy()
    
    # Crear copia para trabajar
    result_gdf = gdf.copy()
    
    # Calcular área por grupo
    logger.info("📊 Calculando áreas por grupo...")
    areas_por_grupo = _calcular_areas_por_grupo(
        result_gdf, grouping_fields, use_original_area
    )
    
    if areas_por_grupo.empty:
        logger.error("No se pudieron calcular áreas por grupo")
        return result_gdf
    
    # Distribución proporcional base
    logger.info("🧮 Calculando distribución proporcional...")
    parcelas_por_grupo = _distribuir_proporcionalmente(
        areas_por_grupo, total_parcels
    )
    
    # Aplicar mínimo si está configurado
    if minimum_config.get("type") != "none":
        logger.info(f"⚙️ Aplicando mínimo por grupo: {minimum_config}")
        parcelas_por_grupo = _aplicar_minimo_por_grupo(
            parcelas_por_grupo, minimum_config, total_parcels
        )
    
    # Ajuste final para total exacto
    logger.info("✅ Ajustando para total exacto...")
    parcelas_por_grupo = _ajustar_total_exacto(
        parcelas_por_grupo, total_parcels
    )
    
    # Asignar resultados al GeoDataFrame
    result_gdf = _asignar_parcelas_a_gdf(
        result_gdf, parcelas_por_grupo, grouping_fields
    )
    
    # Mostrar estadísticas finales
    _mostrar_estadisticas_distribucion(
        parcelas_por_grupo, total_parcels, minimum_config
    )
    
    return result_gdf


def _calcular_areas_por_grupo(
    gdf: gpd.GeoDataFrame, 
    grouping_fields: List[str],
    use_original_area: bool
) -> pd.DataFrame:
    """Calcula el área total por grupo."""
    try:
        # Determinar columna de área a usar
        area_column = None
        if 'area_ha' in gdf.columns:
            area_column = 'area_ha'
        elif 'area_m2' in gdf.columns:
            area_column = 'area_m2'
            # Convertir a hectáreas
            gdf = gdf.copy()
            gdf['area_ha'] = gdf['area_m2'] / 10000
            area_column = 'area_ha'
        else:
            # Calcular área desde geometría
            logger.info("Calculando área desde geometría...")
            gdf = gdf.copy()
            gdf['area_ha'] = gdf.geometry.area / 10000
            area_column = 'area_ha'
        
        # Agrupar y sumar áreas
        areas_summary = gdf.groupby(grouping_fields).agg({
            area_column: 'sum'
        }).reset_index()
        
        areas_summary = areas_summary.rename(columns={area_column: 'area_total_ha'})
        
        # Crear identificador único de grupo
        areas_summary['group_id'] = areas_summary.apply(
            lambda row: "_".join([str(row[field]) for field in grouping_fields]),
            axis=1
        )
        
        logger.info(f"Calculadas áreas para {len(areas_summary)} grupos")
        logger.info(f"Área total: {areas_summary['area_total_ha'].sum():.2f} ha")
        
        return areas_summary
        
    except Exception as e:
        logger.error(f"Error calculando áreas por grupo: {e}")
        return pd.DataFrame()


def _distribuir_proporcionalmente(
    areas_df: pd.DataFrame, 
    total_parcels: int
) -> pd.DataFrame:
    """Distribuye parcelas proporcionalmente según área."""
    if areas_df.empty:
        return areas_df
    
    # Calcular área total
    area_total = areas_df['area_total_ha'].sum()
    
    if area_total == 0:
        logger.warning("Área total es 0, distribuyendo equitativamente")
        parcelas_por_grupo = total_parcels / len(areas_df)
        areas_df['parcelas_proporcional'] = parcelas_por_grupo
        return areas_df
    
    # Calcular proporción y parcelas base
    areas_df['proporcion'] = areas_df['area_total_ha'] / area_total
    areas_df['parcelas_base'] = areas_df['proporcion'] * total_parcels
    
    # Parte entera y decimal
    areas_df['parcelas_entero'] = areas_df['parcelas_base'].apply(math.floor)
    areas_df['resto_decimal'] = areas_df['parcelas_base'] - areas_df['parcelas_entero']
    
    logger.debug(f"Distribución base: {areas_df['parcelas_entero'].sum()} de {total_parcels}")
    
    return areas_df


def _aplicar_minimo_por_grupo(
    parcelas_df: pd.DataFrame,
    minimum_config: Dict[str, Any], 
    total_parcels: int
) -> pd.DataFrame:
    """Aplica el mínimo por grupo configurado."""
    minimum_type = minimum_config.get("type", "none")
    minimum_value = minimum_config.get("value", 0.0)
    
    if minimum_type == "none":
        return parcelas_df
    
    # Calcular valor mínimo efectivo
    if minimum_type == "one":
        minimo_efectivo = 1
    elif minimum_type == "custom":
        minimo_efectivo = int(minimum_value)
    elif minimum_type == "percent":
        minimo_efectivo = max(1, math.ceil(total_parcels * minimum_value / 100))
    else:
        return parcelas_df
    
    logger.info(f"Aplicando mínimo de {minimo_efectivo} parcelas por grupo")
    
    # Aplicar mínimo
    parcelas_df['parcelas_minimo'] = parcelas_df['parcelas_entero'].apply(
        lambda x: max(x, minimo_efectivo)
    )
    
    # Verificar si el mínimo excede el total
    total_con_minimo = parcelas_df['parcelas_minimo'].sum()
    
    if total_con_minimo > total_parcels:
        logger.warning(
            f"Mínimo por grupo ({total_con_minimo}) excede total ({total_parcels}). "
            "Ajustando proporcionalmente..."
        )
        # Reducir proporcionalmente manteniendo el mínimo relativo
        factor_reduccion = total_parcels / total_con_minimo
        parcelas_df['parcelas_minimo'] = (
            parcelas_df['parcelas_minimo'] * factor_reduccion
        ).apply(math.floor)
        
        # Asegurar que cada grupo tenga al menos 1
        parcelas_df['parcelas_minimo'] = parcelas_df['parcelas_minimo'].apply(
            lambda x: max(1, x)
        )
    
    # Usar las parcelas con mínimo aplicado
    parcelas_df['parcelas_entero'] = parcelas_df['parcelas_minimo']
    
    return parcelas_df


def _ajustar_total_exacto(
    parcelas_df: pd.DataFrame, 
    total_parcels: int
) -> pd.DataFrame:
    """Ajusta la distribución para obtener el total exacto (Largest Remainder Method)."""
    if parcelas_df.empty:
        return parcelas_df
    
    # Total actual de enteros
    total_enteros = int(parcelas_df['parcelas_entero'].sum())
    parcelas_restantes = total_parcels - total_enteros
    
    logger.debug(f"Total enteros: {total_enteros}, Restantes: {parcelas_restantes}")
    
    if parcelas_restantes == 0:
        # Ya tenemos el total exacto
        parcelas_df['n_parcelas'] = parcelas_df['parcelas_entero'].astype(int)
        return parcelas_df
    
    if parcelas_restantes > 0:
        # Faltan parcelas - asignar a grupos con mayor resto decimal
        parcelas_df_sorted = parcelas_df.sort_values(
            'resto_decimal', ascending=False
        ).reset_index(drop=True)
        
        # Asignar parcelas adicionales
        parcelas_df_sorted['parcelas_adicionales'] = 0
        parcelas_df_sorted.loc[:parcelas_restantes-1, 'parcelas_adicionales'] = 1
        
        # Calcular total final
        parcelas_df_sorted['n_parcelas'] = (
            parcelas_df_sorted['parcelas_entero'] + 
            parcelas_df_sorted['parcelas_adicionales']
        ).astype(int)
        
        # Restaurar orden original
        parcelas_df = parcelas_df_sorted.sort_index()
        
    else:
        # Sobran parcelas - quitar de grupos con menor resto decimal
        parcelas_sobrantes = abs(parcelas_restantes)
        parcelas_df_sorted = parcelas_df.sort_values(
            'resto_decimal', ascending=True
        ).reset_index(drop=True)
        
        # Quitar parcelas
        parcelas_df_sorted['parcelas_reducidas'] = 0
        for i in range(min(parcelas_sobrantes, len(parcelas_df_sorted))):
            if parcelas_df_sorted.loc[i, 'parcelas_entero'] > 0:
                parcelas_df_sorted.loc[i, 'parcelas_reducidas'] = 1
        
        # Calcular total final
        parcelas_df_sorted['n_parcelas'] = (
            parcelas_df_sorted['parcelas_entero'] - 
            parcelas_df_sorted['parcelas_reducidas']
        ).astype(int)
        
        # Restaurar orden original
        parcelas_df = parcelas_df_sorted.sort_index()
    
    # Validar total final
    total_final = int(parcelas_df['n_parcelas'].sum())
    if total_final != total_parcels:
        logger.warning(
            f"⚠️ Ajuste no exacto: {total_final} vs {total_parcels}"
        )
    
    return parcelas_df


def _asignar_parcelas_a_gdf(
    gdf: gpd.GeoDataFrame,
    parcelas_df: pd.DataFrame, 
    grouping_fields: List[str]
) -> gpd.GeoDataFrame:
    """Asigna las parcelas calculadas al GeoDataFrame original."""
    if parcelas_df.empty:
        gdf['n_parcelas'] = 0
        return gdf
    
    # Crear diccionario de mapeo grupo -> parcelas
    parcelas_mapping = {}
    for _, row in parcelas_df.iterrows():
        group_key = "_".join([str(row[field]) for field in grouping_fields])
        parcelas_mapping[group_key] = int(row['n_parcelas'])
    
    # Función para obtener parcelas por grupo
    def get_parcelas_for_group(row):
        group_key = "_".join([str(row[field]) for field in grouping_fields])
        return parcelas_mapping.get(group_key, 0)
    
    # Asignar parcelas
    gdf['n_parcelas'] = gdf.apply(get_parcelas_for_group, axis=1)
    
    return gdf


def _mostrar_estadisticas_distribucion(
    parcelas_df: pd.DataFrame,
    total_parcels: int, 
    minimum_config: Dict[str, Any]
) -> None:
    """Muestra estadísticas de la distribución."""
    if parcelas_df.empty:
        return
    
    total_final = int(parcelas_df['n_parcelas'].sum())
    grupos_totales = len(parcelas_df)
    grupos_con_parcelas = len(parcelas_df[parcelas_df['n_parcelas'] > 0])
    
    logger.info("=" * 60)
    logger.info("📊 ESTADÍSTICAS DE DISTRIBUCIÓN PROPORCIONAL")
    logger.info("=" * 60)
    logger.info(f"Parcelas objetivo: {total_parcels}")
    logger.info(f"Parcelas distribuidas: {total_final}")
    logger.info(f"Precisión: {total_final/total_parcels*100:.1f}%")
    logger.info(f"Grupos totales: {grupos_totales}")
    logger.info(f"Grupos con parcelas: {grupos_con_parcelas}")
    
    if grupos_con_parcelas > 0:
        min_parcelas = int(parcelas_df[parcelas_df['n_parcelas'] > 0]['n_parcelas'].min())
        max_parcelas = int(parcelas_df['n_parcelas'].max())
        avg_parcelas = parcelas_df[parcelas_df['n_parcelas'] > 0]['n_parcelas'].mean()
        
        logger.info(f"Parcelas por grupo: {min_parcelas}-{max_parcelas} (promedio: {avg_parcelas:.1f})")
    
    # Información del mínimo aplicado
    minimum_type = minimum_config.get("type", "none")
    if minimum_type != "none":
        logger.info(f"Mínimo aplicado: {minimum_type}")
        if minimum_type in ["custom", "percent"]:
            logger.info(f"Valor mínimo: {minimum_config.get('value', 0)}")
    
    logger.info("=" * 60)


def generar_preview_distribucion(
    areas_df: pd.DataFrame,
    total_parcels: int,
    minimum_config: Dict[str, Any],
    max_groups: int = 10
) -> str:
    """
    Genera un preview de cómo quedaría la distribución.
    
    Args:
        areas_df: DataFrame con áreas por grupo
        total_parcels: Total de parcelas a distribuir
        minimum_config: Configuración de mínimo
        max_groups: Máximo número de grupos a mostrar
        
    Returns:
        String con el preview formateado
    """
    if areas_df.empty:
        return "No hay datos para mostrar preview."
    
    try:
        # Calcular distribución temporal
        temp_df = _distribuir_proporcionalmente(areas_df.copy(), total_parcels)
        
        if minimum_config.get("type") != "none":
            temp_df = _aplicar_minimo_por_grupo(
                temp_df, minimum_config, total_parcels
            )
        
        temp_df = _ajustar_total_exacto(temp_df, total_parcels)
        
        # Crear preview text
        preview_lines = []
        preview_lines.append(f"📊 Preview de distribución ({total_parcels} parcelas total):")
        preview_lines.append("")
        
        # Mostrar top grupos
        display_df = temp_df.head(max_groups)
        
        for _, row in display_df.iterrows():
            group_id = row['group_id']
            area = row['area_total_ha']
            parcelas = int(row['n_parcelas'])
            porcentaje = (area / temp_df['area_total_ha'].sum()) * 100
            
            preview_lines.append(
                f"• {group_id}: {parcelas} parcelas ({area:.1f} ha, {porcentaje:.1f}%)"
            )
        
        if len(temp_df) > max_groups:
            remaining = len(temp_df) - max_groups
            remaining_parcels = temp_df.iloc[max_groups:]['n_parcelas'].sum()
            preview_lines.append(f"... y {remaining} grupos más ({remaining_parcels} parcelas)")
        
        preview_lines.append("")
        preview_lines.append(f"Total verificado: {int(temp_df['n_parcelas'].sum())} parcelas")
        
        return "\n".join(preview_lines)
        
    except Exception as e:
        return f"Error generando preview: {e}"
