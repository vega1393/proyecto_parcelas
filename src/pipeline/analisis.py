"""
Módulo para el análisis de pérdidas de parcelas entre etapas.
"""

import logging
import pandas as pd
import geopandas as gpd
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


def analizar_perdidas_parcelas(
    gdf_calculado: gpd.GeoDataFrame,
    fields: List[str],
    gdf_generado: Optional[gpd.GeoDataFrame] = None,
    output_csv: Optional[str] = None
) -> pd.DataFrame:
    """
    Analiza la correspondencia entre parcelas planificadas y generadas.
    Lógica V2: Adaptada al flujo refactorizado donde el cálculo y los filtros
    se realizan en un solo paso.
    
    Args:
        gdf_calculado: GeoDataFrame con los grupos y n_parcelas planificadas
                       (salida de calculo_parcelas).
        fields: Campos de agrupación.
        gdf_generado: GeoDataFrame con las parcelas de puntos finales generadas (opcional).
        output_csv: Ruta del archivo CSV de salida (opcional).
        
    Returns:
        DataFrame con el análisis final.
    """
    logger.debug("Iniciando análisis de pérdidas (Lógica V2)...")
    
    # --- VALIDACIÓN DE CAMPOS ---
    available_fields = [field for field in fields if field in gdf_calculado.columns]
    missing_fields = [field for field in fields if field not in gdf_calculado.columns]
    
    if missing_fields:
        logger.warning(f"⚠️  Campos de agrupación faltantes en GDF de entrada y serán ignorados: {missing_fields}")
    
    if not available_fields:
        logger.error("❌ No hay campos de agrupación válidos para el análisis.")
        return pd.DataFrame()
    
    logger.info(f"📊 Analizando resultados usando campos: {available_fields}")

    # --- DATAFRAME BASE ---
    # El DataFrame de análisis se basa directamente en los resultados del cálculo
    analisis_df = gdf_calculado[available_fields + ['n_parcelas']].copy()
    analisis_df.rename(columns={'n_parcelas': 'parcelas_planificadas'}, inplace=True)

    # --- CONTEO DE PARCELAS GENERADAS ---
    if gdf_generado is not None and not gdf_generado.empty:
        # Asegurar que los campos de agrupación existen en el gdf generado
        gen_fields = [f for f in available_fields if f in gdf_generado.columns]
        if not gen_fields:
             logger.warning("No se encontraron campos de agrupación en el GDF de parcelas generadas. No se puede hacer el join.")
             analisis_df['parcelas_generadas'] = 0
        else:
            parcels_by_group = gdf_generado.groupby(gen_fields).size().reset_index(name='parcelas_generadas')
            
            # [NUEVO] Asegurar consistencia de tipos antes del merge
            for col in gen_fields:
                if col in analisis_df.columns and col in parcels_by_group.columns:
                    analisis_df[col] = analisis_df[col].astype(str)
                    parcels_by_group[col] = parcels_by_group[col].astype(str)

            analisis_df = analisis_df.merge(parcels_by_group, on=gen_fields, how='left')
            analisis_df['parcelas_generadas'] = analisis_df['parcelas_generadas'].fillna(0).astype(int)
    else:
        analisis_df['parcelas_generadas'] = 0

    # --- CÁLCULO DE DIFERENCIAS Y ESTADÍSTICAS ---
    analisis_df['diferencia'] = analisis_df['parcelas_planificadas'] - analisis_df['parcelas_generadas']
    
    total_planificadas = analisis_df['parcelas_planificadas'].sum()
    total_generadas = analisis_df['parcelas_generadas'].sum()
    
    grupos_totales_planificados = len(analisis_df)
    # Grupos donde se planificó al menos una parcela
    grupos_con_plan = analisis_df[analisis_df['parcelas_planificadas'] > 0]
    
    # Sobre los que tenían plan, cuántos se completaron
    grupos_completos = len(grupos_con_plan[grupos_con_plan['diferencia'] == 0])
    grupos_incompletos = len(grupos_con_plan[grupos_con_plan['diferencia'] != 0])
    
    tasa_exito = (total_generadas / total_planificadas * 100) if total_planificadas > 0 else 0

    # --- REPORTE EN LOG ---
    logger.info("=" * 70)
    logger.info("=== ANÁLISIS DE GENERACIÓN DE PARCELAS (REPORTE V2) ===")
    logger.info("=" * 70)
    
    logger.info("RESUMEN GENERAL:")
    logger.info(f"   - Total Parcelas Planificadas: {int(total_planificadas)}")
    logger.info(f"   - Total Parcelas Generadas:    {int(total_generadas)}")
    logger.info(f"   - Tasa de Éxito General:       {tasa_exito:.1f}%")
    
    logger.info("\nANÁLISIS POR GRUPOS:")
    logger.info(f"   - Grupos con parcelas planificadas: {len(grupos_con_plan)} de {grupos_totales_planificados}")
    logger.info(f"   - Grupos completos (100% generado): {grupos_completos}")
    logger.info(f"   - Grupos con pérdidas en generación: {grupos_incompletos}")
    
    if grupos_incompletos > 0:
        logger.warning("\nDETALLE DE GRUPOS CON PÉRDIDAS EN GENERACIÓN:")
        perdidas_df = grupos_con_plan[grupos_con_plan['diferencia'] > 0].copy()
        for _, row in perdidas_df.iterrows():
            grupo_id_parts = [f"{field}={row[field]}" for field in available_fields[:3]]
            grupo_id = ", ".join(grupo_id_parts)
            logger.warning(
                f"  - Grupo '{grupo_id}': "
                f"Planificadas={int(row['parcelas_planificadas'])}, "
                f"Generadas={int(row['parcelas_generadas'])} "
                f"(Pérdida: {int(row['diferencia'])})"
            )
            
    logger.info("\n" + "=" * 70)
        
    if output_csv:
        analisis_df.to_csv(output_csv, index=False)
        
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
    
    # === VALIDACIÓN ROBUSTA DE CAMPOS ===
    # Filtrar solo los campos que realmente existen en los GeoDataFrames
    available_fields = [field for field in fields if field in gdf_inicial.columns]
    missing_fields = [field for field in fields if field not in gdf_inicial.columns]
    
    if missing_fields:
        logger.warning(f"⚠️  Campos faltantes en análisis CSV (serán ignorados): {missing_fields}")
    
    if not available_fields:
        logger.error("❌ No hay campos válidos para análisis CSV")
        return pd.DataFrame()
    
    logger.info(f"📊 Analizando pérdidas CSV usando campos: {available_fields}")
    
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
        for col in available_fields:
            if col in gdf_prep.columns:
                gdf_prep[col] = gdf_prep[col].astype(str)
        
        # Agrupar por campos de agrupación
        if 'n_parcelas' in gdf_prep.columns:
            gdf_summary = gdf_prep.groupby(available_fields).agg({
                'n_parcelas': 'first'
            }).reset_index()
        else:
            # Si no hay n_parcelas, contar registros
            gdf_summary = gdf_prep.groupby(available_fields).size().reset_index(name='n_parcelas')
        
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
        (gdf_inicial, 'inicial', available_fields),
        (gdf_post_filtros, 'post_filtros', available_fields),
        (gdf_post_exclusion, 'post_exclusion', available_fields),
    ]
    
    for gdf, stage_name, stage_fields in stages:
        stage_summary = merge_with_gdf(gdf, stage_name)
        analisis_df = safe_merge(analisis_df, stage_summary, csv_grouping_cols, stage_fields, stage_name)
    
    # Análisis de parcelas finalmente generadas
    if gdf_final is not None and not gdf_final.empty:
        # Preparar GDF final
        gdf_final_prep = gdf_final.copy()
        for col in available_fields:
            if col in gdf_final_prep.columns:
                gdf_final_prep[col] = gdf_final_prep[col].astype(str)
        
        # Contar parcelas generadas por grupo
        parcels_generated = gdf_final_prep.groupby(available_fields).size().reset_index(name='parcelas_generadas')
        
        # Hacer merge
        analisis_df = safe_merge(analisis_df, parcels_generated, csv_grouping_cols, available_fields, 'generadas')
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