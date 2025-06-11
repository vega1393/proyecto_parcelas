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
    except Exception as e:
        logger.error(f"Failed to load PO data: {e}", exc_info=True)
        return parcelas_gdf

    po_fields_to_join = [f.lower() for f in po_config.get("campos", [])]
    available_po_fields = [f for f in po_fields_to_join if f in po_gdf.columns]
    logger.info(f"Performing spatial join with PO fields: {available_po_fields}")

    parcels_with_po = gpd.sjoin(parcelas_gdf, po_gdf[available_po_fields + ['geometry']], how='left', predicate='intersects')
    
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
        
        if predio_field in parcels_with_po.columns and tipo_field in parcels_with_po.columns:
            # Sort for consistent numbering
            parcels_with_po = parcels_with_po.sort_values(by=[predio_field, tipo_field, 'id_parcela'])
            # Create sequential number within each property
            parcels_with_po['_temp_serial'] = parcels_with_po.groupby(predio_field).cumcount() + 1
            
            parcels_with_po['id_parcela_final'] = (
                parcels_with_po[tipo_field].astype(str).str.strip() + '_' +
                parcels_with_po[predio_field].astype(str).str.strip() + '_' +
                parcels_with_po['_temp_serial'].astype(str).str.zfill(3) +
                (f'_{entrega}' if entrega else '')
            )
            parcels_with_po = parcels_with_po.drop(columns=['_temp_serial'])
        else:
            logger.warning(f"Could not generate final ID. Missing required fields: {predio_field}, {tipo_field}")
            parcels_with_po['id_parcela_final'] = parcels_with_po['id_parcela']

    if output_path:
        logger.info(f"Saving {len(parcels_with_po)} parcels with PO attributes to: {output_path}")
        pyogrio.write_dataframe(parcels_with_po, output_path)

    return parcels_with_po