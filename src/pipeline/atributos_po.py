# src/pipeline/atributos_po.py

import logging
import geopandas as gpd
import pandas as pd
import pyogrio
from typing import Dict, Any, Optional, List

from src.utils.geo_utils import verificar_y_transformar_crs
from src.io.lectura import leer_capa

logger = logging.getLogger(__name__)

def generar_id_fasa(parcels_gdf: gpd.GeoDataFrame, po_config: Dict[str, Any], entrega: Optional[str] = None) -> gpd.GeoDataFrame:
    """
    Genera IDs específicos de parcelas basados en la configuración del PO.
    
    Args:
        parcels_gdf: GeoDataFrame con las parcelas
        po_config: Configuración del Plan Operativo
        entrega: Código de entrega (opcional)
        
    Returns:
        GeoDataFrame con IDs de parcelas generados
    """
    id_config = po_config.get("campos_id_fasa", {})
    predio_field = id_config.get('predio', 'predio').lower()
    tipo_field = id_config.get('tipo', 'tipouso').lower()
    
    logger.debug(f"Looking for ID fields: predio='{predio_field}', tipo='{tipo_field}'")
    logger.debug(f"Available columns: {list(parcels_gdf.columns)}")
    
    if predio_field in parcels_gdf.columns and tipo_field in parcels_gdf.columns:
        # Check if fields have actual values
        predio_values = parcels_gdf[predio_field].notna().sum()
        tipo_values = parcels_gdf[tipo_field].notna().sum()
        logger.debug(f"Field '{predio_field}' has {predio_values} non-null values")
        logger.debug(f"Field '{tipo_field}' has {tipo_values} non-null values")
        
        if predio_values > 0 and tipo_values > 0:
            # Sort for consistent numbering
            parcels_gdf = parcels_gdf.sort_values(by=[predio_field, tipo_field, 'id_parcela'])
            # Create sequential number within each property
            parcels_gdf['_temp_serial'] = parcels_gdf.groupby(predio_field).cumcount() + 1
            
            parcels_gdf['id_parcel'] = (
                parcels_gdf[tipo_field].astype(str).str.strip() + '_' +
                parcels_gdf[predio_field].astype(str).str.strip() + '_' +
                parcels_gdf['_temp_serial'].astype(str).str.zfill(3) +
                (f'_{entrega}' if entrega else '')
            )
            parcels_gdf = parcels_gdf.drop(columns=['_temp_serial'])
            logger.debug("Final parcel IDs generated successfully")
        else:
            logger.warning(f"Fields exist but have no values: {predio_field}={predio_values}, {tipo_field}={tipo_values}")
            parcels_gdf['id_parcel'] = parcels_gdf['id_parcela']
    else:
        logger.warning(f"Could not generate final ID. Missing required fields: {predio_field}, {tipo_field}")
        parcels_gdf['id_parcel'] = parcels_gdf['id_parcela']
    
    return parcels_gdf

def asignar_atributos_po(parcelas_gdf: gpd.GeoDataFrame, po_config: Dict[str, Any], crs_target: int, output_path: Optional[str] = None, entrega: Optional[str] = None) -> gpd.GeoDataFrame:
    """Assigns attributes from the Operational Plan (PO) to the generated parcels."""
    logger.info("Assigning attributes from Operational Plan (PO)...")
    
    try:
        po_gdf = leer_capa(po_config['ruta'], po_config.get('capa'))
        po_gdf = verificar_y_transformar_crs(po_gdf, "PO", crs_target)
        # Normalize PO columns for consistency
        po_gdf.columns = [c.lower() for c in po_gdf.columns]
        
        # Debug: log PO data info
        logger.debug(f"PO data loaded: {len(po_gdf)} records")
        logger.debug(f"PO columns available: {list(po_gdf.columns)}")
        
    except Exception as e:
        logger.error(f"Failed to load PO data: {e}", exc_info=True)
        return parcelas_gdf

    po_fields_to_join = [f.lower() for f in po_config.get("campos", [])]
    available_po_fields = [f for f in po_fields_to_join if f in po_gdf.columns]
    logger.debug(f"Performing spatial join with PO fields: {available_po_fields}")

    # Debug: log parcels info before join
    logger.debug(f"Parcels before join: {len(parcelas_gdf)} records")
    logger.debug(f"Parcel columns: {list(parcelas_gdf.columns)}")

    parcels_with_po = gpd.sjoin(parcelas_gdf, po_gdf[available_po_fields + ['geometry']], how='left', predicate='intersects')
    
    # Debug: log join results
    logger.debug(f"Parcels after join: {len(parcels_with_po)} records")
    logger.debug(f"Columns after join: {list(parcels_with_po.columns)}")

    # Handle column conflicts from spatial join
    renamed_columns = {}
    columns_to_drop = []
    
    for field in available_po_fields:
        left_col = f"{field}_left"
        right_col = f"{field}_right"
        
        if left_col in parcels_with_po.columns and right_col in parcels_with_po.columns:
            # Replace left with right values, keeping right as the main column
            logger.debug(f"Replacing '{left_col}' with '{right_col}' -> '{field}'")
            parcels_with_po[field] = parcels_with_po[right_col]
            columns_to_drop.extend([left_col, right_col])
            renamed_columns[right_col] = field
        elif right_col in parcels_with_po.columns:
            # Only right column exists, rename it
            parcels_with_po = parcels_with_po.rename(columns={right_col: field})
            renamed_columns[right_col] = field
    
    # Handle index_right column
    if 'index_right' in parcels_with_po.columns:
        parcels_with_po = parcels_with_po.rename(columns={'index_right': 'index'})
        renamed_columns['index_right'] = 'index'
    
    logger.debug(f"Renamed columns: {renamed_columns}")
    
    # Drop conflicting columns
    columns_to_drop = [col for col in columns_to_drop if col in parcels_with_po.columns]
    if columns_to_drop:
        parcels_with_po = parcels_with_po.drop(columns=columns_to_drop)
        logger.debug(f"Dropped columns: {columns_to_drop}")
    
    logger.debug(f"Final columns after cleanup: {list(parcels_with_po.columns)}")

    # Check spatial join success
    non_null_joins = 0
    for field in available_po_fields:
        if field in parcels_with_po.columns:
            non_null_count = parcels_with_po[field].notna().sum()
            logger.debug(f"Field '{field}': {non_null_count}/{len(parcels_with_po)} parcels have values")
            if non_null_count > 0:
                non_null_joins += 1
    
    if non_null_joins == 0:
        logger.warning("No spatial joins were successful. Check CRS compatibility and spatial overlap.")
    
    # Drop duplicates if a parcel intersects multiple PO polygons, keeping the first
    parcels_with_po = parcels_with_po.drop_duplicates(subset=['id_parcela'], keep='first')
    if 'index_right' in parcels_with_po.columns:
        parcels_with_po = parcels_with_po.drop(columns=['index_right'])

    # Generate a more specific parcel ID if configured
    if po_config.get("generar_id_fasa", True):
        logger.debug("Generating final parcel ID...")
        parcels_with_po = generar_id_fasa(parcels_with_po, po_config, entrega)
    
    # Save to file if output path provided
    if output_path:
        try:
            pyogrio.write_dataframe(parcels_with_po, output_path, layer='parcelas_con_atributos')
            logger.info(f"Parcels with PO attributes saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save parcels with PO attributes: {e}")
    
    return parcels_with_po