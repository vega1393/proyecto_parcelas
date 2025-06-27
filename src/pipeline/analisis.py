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


def analizar_perdidas_con_csv(
    csv_original: pd.DataFrame,
    csv_grouping_cols: List[str],
    csv_count_col: str,
    gdf_inicial: gpd.GeoDataFrame,
    fields: List[str],
    gdf_post_filtros: Optional[gpd.GeoDataFrame] = None,
    gdf_post_exclusion: Optional[gpd.GeoDataFrame] = None,
    gdf_final: Optional[gpd.GeoDataFrame] = None,
    output_csv: Optional[str] = None
) -> pd.DataFrame:
    """
    Analiza las pérdidas de parcelas comparando con el CSV original.
    Esta función proporciona un análisis más preciso incluyendo:
    - Comparación con el CSV original
    - Identificación de grupos perdidos y sus causas
    - Porcentajes reales de éxito
    
    Args:
        csv_original: DataFrame del CSV original con las parcelas planificadas
        csv_grouping_cols: Columnas de agrupación del CSV
        csv_count_col: Columna que contiene el número de parcelas en el CSV
        gdf_inicial: GeoDataFrame inicial con áreas agrupadas
        fields: Campos de agrupación
        gdf_post_filtros: GeoDataFrame después de aplicar filtros (opcional)
        gdf_post_exclusion: GeoDataFrame después de exclusiones (opcional)
        gdf_final: GeoDataFrame final con parcelas generadas (opcional)
        output_csv: Ruta del archivo CSV de salida (opcional)
        
    Returns:
        DataFrame con el análisis completo de pérdidas por grupo
    """
    logger.debug("Iniciando análisis de pérdidas con CSV original...")
    
    # Preparar el CSV original para análisis
    csv_df = csv_original.copy()
    
    # FILTRAR grupos con 0 parcelas (grupos marcadores que no deben generar parcelas)
    grupos_totales_csv = len(csv_df)
    csv_df = csv_df[csv_df[csv_count_col] > 0].copy()
    grupos_validos_csv = len(csv_df)
    
    logger.info(f"📋 Grupos del CSV: {grupos_totales_csv} total, {grupos_validos_csv} con parcelas > 0")
    logger.info(f"⚙️ Filtrados {grupos_totales_csv - grupos_validos_csv} grupos marcadores con 0 parcelas")
    
    # Harmonizar tipos de datos del CSV (convertir a string para consistencia)
    for col in csv_grouping_cols:
        if col in csv_df.columns:
            csv_df[col] = csv_df[col].astype(str)
    
    # Crear el DataFrame base con todos los grupos del CSV original
    analisis_df = csv_df[csv_grouping_cols + [csv_count_col]].copy()
    analisis_df = analisis_df.rename(columns={csv_count_col: 'parcelas_csv_original'})
    
    # Crear identificador único para cada grupo
    analisis_df['grupo_id'] = analisis_df.apply(
        lambda row: " | ".join([f"{col}:{row[col]}" for col in csv_grouping_cols]), 
        axis=1
    )
    
    # Función helper para hacer merge con GeoDataFrames
    def merge_with_gdf(gdf, stage_name):
        if gdf is None or gdf.empty:
            return pd.DataFrame()
        
        # Preparar GDF para merge
        gdf_prep = gdf.copy()
        
        # Harmonizar tipos de datos
        for col in fields:
            if col in gdf_prep.columns:
                gdf_prep[col] = gdf_prep[col].astype(str)
        
        # Agrupar por campos de agrupación
        if 'n_parcelas' in gdf_prep.columns:
            gdf_summary = gdf_prep.groupby(fields).agg({
                'n_parcelas': 'first'
            }).reset_index()
        else:
            # Si no hay n_parcelas, contar registros
            gdf_summary = gdf_prep.groupby(fields).size().reset_index(name='n_parcelas')
        
        # Renombrar columnas para la etapa
        gdf_summary = gdf_summary.rename(columns={'n_parcelas': f'parcelas_{stage_name}'})
        
        return gdf_summary
    
    # Función helper para hacer merge con consistencia de columnas
    def safe_merge(left_df, right_df, left_cols, right_cols, stage_name):
        if right_df.empty:
            left_df[f'parcelas_{stage_name}'] = 0
            left_df[f'causa_perdida_{stage_name}'] = 'Sin datos'
            return left_df
        
        # Crear mapeo de columnas si son diferentes
        if left_cols != right_cols:
            # Crear diccionario de mapeo
            col_mapping = dict(zip(right_cols, left_cols))
            right_df_mapped = right_df.rename(columns=col_mapping)
        else:
            right_df_mapped = right_df.copy()
        
        # Hacer merge
        merged = left_df.merge(right_df_mapped, on=left_cols, how='left')
        
        # Llenar valores nulos
        merged[f'parcelas_{stage_name}'] = merged[f'parcelas_{stage_name}'].fillna(0)
        
        # Determinar causa de pérdida
        def determinar_causa(row):
            if row[f'parcelas_{stage_name}'] == 0:
                return f'Eliminado en {stage_name}'
            elif row[f'parcelas_{stage_name}'] < row['parcelas_csv_original']:
                return f'Parcialmente perdido en {stage_name}'
            else:
                return 'OK'
        
        merged[f'causa_perdida_{stage_name}'] = merged.apply(determinar_causa, axis=1)
        
        return merged
    
    # Análisis por etapas
    stages = [
        (gdf_inicial, 'inicial', fields),
        (gdf_post_filtros, 'post_filtros', fields),
        (gdf_post_exclusion, 'post_exclusion', fields),
    ]
    
    for gdf, stage_name, stage_fields in stages:
        stage_summary = merge_with_gdf(gdf, stage_name)
        analisis_df = safe_merge(analisis_df, stage_summary, csv_grouping_cols, stage_fields, stage_name)
    
    # Análisis de parcelas finalmente generadas
    if gdf_final is not None and not gdf_final.empty:
        # Preparar GDF final
        gdf_final_prep = gdf_final.copy()
        for col in fields:
            if col in gdf_final_prep.columns:
                gdf_final_prep[col] = gdf_final_prep[col].astype(str)
        
        # Contar parcelas generadas por grupo
        parcels_generated = gdf_final_prep.groupby(fields).size().reset_index(name='parcelas_generadas')
        
        # Hacer merge
        analisis_df = safe_merge(analisis_df, parcels_generated, csv_grouping_cols, fields, 'generadas')
    else:
        analisis_df['parcelas_generadas'] = 0
        analisis_df['causa_perdida_generadas'] = 'Sin parcelas finales'
    
    # Calcular métricas finales
    analisis_df['diferencia_total'] = analisis_df['parcelas_csv_original'] - analisis_df['parcelas_generadas']
    analisis_df['porcentaje_exito'] = (analisis_df['parcelas_generadas'] / analisis_df['parcelas_csv_original'] * 100).round(1)
    
    # Determinar estado final
    def determinar_estado_final(row):
        if row['parcelas_generadas'] == 0:
            return 'GRUPO PERDIDO'
        elif row['parcelas_generadas'] < row['parcelas_csv_original']:
            return 'PARCIALMENTE PERDIDO'
        else:
            return 'COMPLETO'
    
    analisis_df['estado_final'] = analisis_df.apply(determinar_estado_final, axis=1)
    
    # Determinar causa principal de pérdida
    def determinar_causa_principal(row):
        if row['parcelas_generadas'] == row['parcelas_csv_original']:
            return 'Sin pérdidas'
        
        # Revisar en qué etapa se perdió
        causas = []
        for stage in ['inicial', 'post_filtros', 'post_exclusion', 'generadas']:
            causa_col = f'causa_perdida_{stage}'
            if causa_col in row and row[causa_col] != 'OK' and row[causa_col] != 'Sin datos':
                causas.append(row[causa_col])
        
        if causas:
            return causas[0]  # Primera causa encontrada
        else:
            return 'Causa desconocida'
    
    analisis_df['causa_principal'] = analisis_df.apply(determinar_causa_principal, axis=1)
    
    # Guardar CSV si se especifica
    if output_csv:
        analisis_df.to_csv(output_csv, index=False)
    
    # Generar reporte detallado
    _generar_reporte_detallado(analisis_df, csv_grouping_cols)
    
    return analisis_df


def _generar_reporte_detallado(analisis_df: pd.DataFrame, grouping_cols: List[str]) -> None:
    """
    Genera un reporte detallado de las pérdidas de parcelas.
    """
    # Métricas generales
    total_csv_original = analisis_df['parcelas_csv_original'].sum()
    total_generadas = analisis_df['parcelas_generadas'].sum()
    total_perdidas = total_csv_original - total_generadas
    porcentaje_exito_real = (total_generadas / total_csv_original * 100) if total_csv_original > 0 else 0
    
    # Estadísticas de grupos
    grupos_totales = len(analisis_df)
    grupos_completos = len(analisis_df[analisis_df['estado_final'] == 'COMPLETO'])
    grupos_parciales = len(analisis_df[analisis_df['estado_final'] == 'PARCIALMENTE PERDIDO'])
    grupos_perdidos = len(analisis_df[analisis_df['estado_final'] == 'GRUPO PERDIDO'])
    
    logger.info("=" * 80)
    logger.info("=== ANÁLISIS DETALLADO DE PÉRDIDAS VS CSV ORIGINAL ===")
    logger.info("=" * 80)
    
    # Resumen general
    logger.info("📊 RESUMEN GENERAL:")
    logger.info(f"   • Total grupos en CSV original: {grupos_totales}")
    logger.info(f"   • Total parcelas en CSV original: {int(total_csv_original)}")
    logger.info(f"   • Total parcelas generadas: {int(total_generadas)}")
    logger.info(f"   • Parcelas perdidas: {int(total_perdidas)}")
    logger.info(f"   • Tasa de éxito REAL: {porcentaje_exito_real:.1f}%")
    
    if total_perdidas > 0:
        logger.info(f"   🔴 Se perdieron {total_perdidas} parcelas ({100-porcentaje_exito_real:.1f}%)")
    else:
        logger.info("   ✅ No hubo pérdidas")
    
    logger.info("")
    
    # Estadísticas por grupos
    logger.info("📈 ANÁLISIS POR GRUPOS:")
    logger.info(f"   • Grupos completos (100%): {grupos_completos}/{grupos_totales} ({grupos_completos/grupos_totales*100:.1f}%)")
    logger.info(f"   • Grupos parcialmente perdidos: {grupos_parciales}/{grupos_totales} ({grupos_parciales/grupos_totales*100:.1f}%)")
    logger.info(f"   • Grupos completamente perdidos: {grupos_perdidos}/{grupos_totales} ({grupos_perdidos/grupos_totales*100:.1f}%)")
    
    logger.info("")
    
    # Análisis de causas principales
    logger.info("🔍 ANÁLISIS DE CAUSAS DE PÉRDIDA:")
    causas_perdida = analisis_df[analisis_df['diferencia_total'] > 0]['causa_principal'].value_counts()
    for causa, count in causas_perdida.items():
        parcelas_perdidas_causa = analisis_df[analisis_df['causa_principal'] == causa]['diferencia_total'].sum()
        logger.info(f"   • {causa}: {count} grupos, {int(parcelas_perdidas_causa)} parcelas perdidas")
    
    logger.info("")
    
    # Mostrar tabla detallada de grupos problemáticos
    grupos_problematicos = analisis_df[analisis_df['diferencia_total'] > 0].copy()
    
    if not grupos_problematicos.empty:
        logger.info("📋 GRUPOS CON PÉRDIDAS DETALLADAS:")
        logger.info("-" * 80)
        
        # Encabezados de la tabla
        header = f"{'Grupo':<25} {'CSV':<5} {'Gen':<5} {'Pérd':<5} {'%':<6} {'Causa':<20}"
        logger.info(header)
        logger.info("-" * 80)
        
        # Ordenar por diferencia total descendente
        grupos_problematicos = grupos_problematicos.sort_values('diferencia_total', ascending=False)
        
        for _, row in grupos_problematicos.head(20).iterrows():  # Mostrar top 20
            # Crear identificador del grupo (truncado)
            grupo_id = " | ".join([f"{col}:{row[col]}" for col in grouping_cols[:2]])
            if len(grupo_id) > 23:
                grupo_id = grupo_id[:20] + "..."
            
            csv_orig = int(row['parcelas_csv_original'])
            generadas = int(row['parcelas_generadas'])
            perdidas = int(row['diferencia_total'])
            porcentaje = row['porcentaje_exito']
            causa = row['causa_principal'][:18] + "..." if len(row['causa_principal']) > 18 else row['causa_principal']
            
            fila = f"{grupo_id:<25} {csv_orig:<5} {generadas:<5} {perdidas:<5} {porcentaje:<6.1f} {causa:<20}"
            logger.info(fila)
        
        if len(grupos_problematicos) > 20:
            logger.info(f"... y {len(grupos_problematicos) - 20} grupos más con pérdidas")
        
        logger.info("-" * 80)
    
    logger.info("")
    logger.info("📝 NOTA: Este análisis compara directamente con el CSV original")
    logger.info("         para proporcionar métricas de éxito más precisas.")
    logger.info("=" * 80) 