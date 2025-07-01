"""
GPKG and GIS file helpers for the Parcel Generator project.

Helpers for working with GeoPackage and FileGDB files: listing layers and fields.
Updated to use pyogrio for better performance and robustness.
"""

from typing import List
import logging

logger = logging.getLogger(__name__)

def list_layers(file_path: str) -> List[str]:
    """
    Returns a list of layer names in a GPKG or FileGDB file.
    
    Uses pyogrio as primary method with fiona as fallback for compatibility.
    
    Args:
        file_path: Path to the GeoPackage or FileGDB file
        
    Returns:
        List of layer names, empty list if file cannot be read
    """
    try:
        # Method 1: Try pyogrio first (modern, faster)
        import pyogrio
        layers_info = pyogrio.list_layers(file_path)
        # pyogrio returns tuples (name, type, feature_count), we only need names
        return [layer_info[0] for layer_info in layers_info]
    except ImportError:
        logger.debug("pyogrio not available, falling back to fiona")
    except Exception as e:
        logger.debug(f"pyogrio failed to list layers: {e}, falling back to fiona")
    
    try:
        # Method 2: Fallback to fiona (legacy compatibility)
        import fiona
        return fiona.listlayers(file_path)
    except ImportError:
        logger.error("Neither pyogrio nor fiona available for listing layers")
        return []
    except Exception as e:
        logger.error(f"Failed to list layers from {file_path}: {e}")
        return []

def list_fields(file_path: str, layer: str) -> List[str]:
    """
    Returns a list of field names for a given layer in a GPKG or FileGDB file.
    
    Uses pyogrio as primary method with fiona as fallback for compatibility.
    
    Args:
        file_path: Path to the GeoPackage or FileGDB file
        layer: Name of the layer
        
    Returns:
        List of field names, empty list if layer cannot be read
    """
    try:
        # Method 1: Try pyogrio first (modern, faster)
        import pyogrio
        # Read just one feature to get schema information
        df = pyogrio.read_dataframe(file_path, layer=layer, max_features=1)
        # Remove geometry column from field list
        fields = [col for col in df.columns if col != 'geometry']
        return fields
    except ImportError:
        logger.debug("pyogrio not available, falling back to fiona")
    except Exception as e:
        logger.debug(f"pyogrio failed to list fields: {e}, falling back to fiona")
    
    try:
        # Method 2: Fallback to fiona (legacy compatibility)
        import fiona
        with fiona.open(file_path, layer=layer) as src:
            return list(src.schema["properties"].keys())
    except ImportError:
        logger.error("Neither pyogrio nor fiona available for listing fields")
        return []
    except Exception as e:
        logger.error(f"Failed to list fields from layer '{layer}' in {file_path}: {e}")
        return [] 