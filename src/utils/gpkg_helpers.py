"""
GPKG and GIS file helpers for the Parcel Generator project.

Helpers for working with GeoPackage and FileGDB files: listing layers and fields.
"""

from typing import List
import fiona

def list_layers(file_path: str) -> List[str]:
    """
    Returns a list of layer names in a GPKG or FileGDB file.
    """
    try:
        return fiona.listlayers(file_path)
    except Exception:
        return []

def list_fields(file_path: str, layer: str) -> List[str]:
    """
    Returns a list of field names for a given layer in a GPKG or FileGDB file.
    """
    try:
        with fiona.open(file_path, layer=layer) as src:
            return list(schema["properties"].keys())
    except Exception:
        return [] 