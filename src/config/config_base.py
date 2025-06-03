"""
Configuración base para la generación de parcelas.
Contiene parámetros comunes a todos los estilos.
"""

from typing import Dict, Any, List, Callable, Optional, Union
import os


def filtrar_apl(valor):
    """Función de filtro para APL."""
    try:
        return float(valor) < 2023
    except (ValueError, TypeError):
        return False


# Configuración base que será heredada por los estilos específicos
BASE_CONFIG = {
    "PROJECTED_CRS": 32718,  # UTM 18S
    "CAMPOS_METRICAS": {
        "p95": "p95",
        "cov": "cov"
    },
    "PO_CONFIG": {
        "ruta": r"C:\TRABAJO\06_proyectos\07_fasa2025\04_po_operativo\uso_suelo_from_arauco\UsoActual_Enero2025.gdb",
        "capa": "Uso_de_Suelo_Enero",  # Nombre de la capa dentro de la geodatabase
        "campos": ["id_predio", "id_rodal", "apl", "tipouso", "tipo_uso"],
        "generar_id_fasa": True,
        "campo_id_fasa": "id_parcela_fasa",
        "prefijo_duplicado": "new_",
        "campos_id_fasa": {
            "tipo": "tipouso",
            "predio": "id_predio"
        }
    },
    "AREA_PARCELA": 400,
    "ID_PARCELA_INICIO": 0,
    "VERSION_PARCELA": "",
    "FIELDS": ["zc_pira", "tipo_uso", "tipouso"],
    "FILTROS_CAMPOS": {
        "tipouso": ["PIRA", "EUNI", "EUGL", "EHNG", "EGRN"],
        "apl": filtrar_apl
    },
    "CAPAS_EXCLUSION": [
        {
            "ruta": r"C:\TRABAJO\06_proyectos\07_fasa2025\03_capas_interes_fasa\DAÑO_VIENTO_2024_POLiDAR2025.shp",
            "capa": None,
            "descripcion": "DAÑO_VIENTO_2024_POLiDAR2025"
        },
        {
            "ruta": r"C:\TRABAJO\06_proyectos\07_fasa2025\03_capas_interes_fasa\Capas_Operativas.gdb",
            "capa": "Incendios_Historicos_T2017_T2024",
            "descripcion": "Incendios_Historicos_T2017_T2024"
        },
        {
            "ruta": r"C:\TRABAJO\06_proyectos\07_fasa2025\03_capas_interes_fasa\predios_rojos.gpkg",
            "capa": "predios",
            "descripcion": "Predios de zona roja"
        },
        {
            "ruta": r"C:\TRABAJO\06_proyectos\07_fasa2025\03_capas_interes_fasa\raleos_20250217.gpkg",
            "capa": "raleos_20250217",
            "descripcion": "Raleos hasta 20250217"
        }
    ],
    "OPCIONES_ACTIVAS": [1, 2, 3, 4, 5, 6, 7]  # Pasos del pipeline
}


def get_config(estilo: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración para un estilo específico, aplicando overrides si se proporcionan.
    
    Args:
        estilo: Nombre del estilo ('calibracion', 'control', 'especial')
        overrides: Diccionario con valores que sobrescriben la configuración por defecto
        
    Returns:
        Diccionario con la configuración completa
    """
    if estilo == "calibracion":
        from src.config.estilos import CALIBRATION_CONFIG
        cfg = CALIBRATION_CONFIG.copy()
    elif estilo == "control":
        from src.config.estilos import CONTROL_CONFIG
        cfg = CONTROL_CONFIG.copy()
    elif estilo == "especial":
        from src.config.estilos import ESPECIAL_CONFIG
        cfg = ESPECIAL_CONFIG.copy()
    else:
        raise ValueError(f"Estilo no reconocido: {estilo}")
    
    # Aplicar overrides si existen
    if overrides:
        for k, v in overrides.items():
            if k in cfg and v is not None:
                cfg[k] = v
    
    return cfg 