# src/pipeline/atributos_po.py

import logging
import geopandas as gpd
import pandas as pd
import pyogrio
from typing import Dict, Any, Optional, List

from src.utils.geo_utils import verificar_y_transformar_crs
from src.io.lectura import leer_capa

logger = logging.getLogger(__name__)

def asignar_atributos_po(parcelas_gdf: gpd.GeoDataFrame, po_config: Dict[str, Any], crs_target: int, output_path: Optional[str] = None, entrega: Optional[str] = None) -> gpd.GeoDataFrame:
    """Assigns attributes from the Operational Plan (PO) to the generated parcels."""
    logger.info("Assigning attributes from Operational Plan (PO)...")
    
    try:
        po_gdf = leer_capa(po_config['ruta'], po_config.get('capa'))
        po_gdf = verificar_y_transformar_crs(po_gdf, "PO", crs_target)
        # Normalize PO columns for consistency
        po_gdf.columns = [c.lower() for c in po_gdf.columns]
        
        # Debug: log PO data info
        logger.info(f"PO data loaded: {len(po_gdf)} records")
        logger.info(f"PO columns available: {list(po_gdf.columns)}")
        
    except Exception as e:
        logger.error(f"Failed to load PO data: {e}", exc_info=True)
        return parcelas_gdf

    po_fields_to_join = [f.lower() for f in po_config.get("campos", [])]
    available_po_fields = [f for f in po_fields_to_join if f in po_gdf.columns]
    logger.info(f"Performing spatial join with PO fields: {available_po_fields}")

    # Debug: log parcels info before join
    logger.info(f"Parcels before join: {len(parcelas_gdf)} records")
    logger.info(f"Parcel columns: {list(parcelas_gdf.columns)}")

    parcels_with_po = gpd.sjoin(parcelas_gdf, po_gdf[available_po_fields + ['geometry']], how='left', predicate='intersects')
    
    # Debug: log join results
    logger.info(f"Parcels after join: {len(parcels_with_po)} records")
    logger.info(f"Columns after join: {list(parcels_with_po.columns)}")
    
    # Clean up column names after spatial join
    # Remove _left and _right suffixes, keeping PO values (_right) when available
    columns_to_rename = {}
    columns_to_drop = []
    
    for col in parcels_with_po.columns:
        if col.endswith('_left'):
            base_name = col[:-5]  # Remove '_left'
            right_col = base_name + '_right'
            
            if right_col in parcels_with_po.columns:
                # Keep the PO value (_right) and rename it to the base name
                columns_to_rename[right_col] = base_name
                columns_to_drop.append(col)  # Drop the _left column
                logger.info(f"Replacing '{col}' with '{right_col}' -> '{base_name}'")
            else:
                # No _right column exists, just rename _left to base name
                columns_to_rename[col] = base_name
                logger.info(f"Renaming '{col}' -> '{base_name}'")
        elif col.endswith('_right'):
            base_name = col[:-6]  # Remove '_right'
            left_col = base_name + '_left'
            
            if left_col not in parcels_with_po.columns:
                # No corresponding _left column, rename _right to base name
                columns_to_rename[col] = base_name
                logger.info(f"Renaming '{col}' -> '{base_name}'")
    
    # Apply column renaming
    if columns_to_rename:
        parcels_with_po = parcels_with_po.rename(columns=columns_to_rename)
        logger.info(f"Renamed columns: {columns_to_rename}")
    
    # Drop unnecessary columns
    if columns_to_drop:
        parcels_with_po = parcels_with_po.drop(columns=columns_to_drop)
        logger.info(f"Dropped columns: {columns_to_drop}")
    
    # Debug: log final column names
    logger.info(f"Final columns after cleanup: {list(parcels_with_po.columns)}")
    
    # Check for successful joins
    non_null_joins = 0
    for field in available_po_fields:
        if field in parcels_with_po.columns:
            non_null_count = parcels_with_po[field].notna().sum()
            logger.info(f"Field '{field}': {non_null_count}/{len(parcels_with_po)} parcels have values")
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
        logger.info("Generating final parcel ID...")
        id_config = po_config.get("campos_id_fasa", {})
        predio_field = id_config.get('predio', 'id_predio').lower()
        tipo_field = id_config.get('tipo', 'tipouso').lower()
        
        logger.info(f"Looking for ID fields: predio='{predio_field}', tipo='{tipo_field}'")
        logger.info(f"Available columns: {list(parcels_with_po.columns)}")
        
        if predio_field in parcels_with_po.columns and tipo_field in parcels_with_po.columns:
            # Check if fields have actual values
            predio_values = parcels_with_po[predio_field].notna().sum()
            tipo_values = parcels_with_po[tipo_field].notna().sum()
            logger.info(f"Field '{predio_field}' has {predio_values} non-null values")
            logger.info(f"Field '{tipo_field}' has {tipo_values} non-null values")
            
            if predio_values > 0 and tipo_values > 0:
                # Sort for consistent numbering
                parcels_with_po = parcels_with_po.sort_values(by=[predio_field, tipo_field, 'id_parcela'])
                # Create sequential number within each property
                parcels_with_po['_temp_serial'] = parcels_with_po.groupby(predio_field).cumcount() + 1
                
                parcels_with_po['id_parcel'] = (
                    parcels_with_po[tipo_field].astype(str).str.strip() + '_' +
                    parcels_with_po[predio_field].astype(str).str.strip() + '_' +
                    parcels_with_po['_temp_serial'].astype(str).str.zfill(3) +
                    (f'_{entrega}' if entrega else '')
                )
                parcels_with_po = parcels_with_po.drop(columns=['_temp_serial'])
                logger.info("Final parcel IDs generated successfully")
            else:
                logger.warning(f"Fields exist but have no values: {predio_field}={predio_values}, {tipo_field}={tipo_values}")
                parcels_with_po['id_parcel'] = parcels_with_po['id_parcela']
        else:
            logger.warning(f"Could not generate final ID. Missing required fields: {predio_field}, {tipo_field}")
            parcels_with_po['id_parcel'] = parcels_with_po['id_parcela']

    if output_path:
        logger.info(f"Saving {len(parcels_with_po)} parcels with PO attributes to: {output_path}")
        pyogrio.write_dataframe(parcels_with_po, output_path)

    return parcels_with_po