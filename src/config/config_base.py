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
        estilo: Nombre del estilo de configuración
        overrides: Diccionario con valores a sobrescribir
        
    Returns:
        Diccionario con la configuración final
    """
    from src.config.estilos import CALIBRATION_CONFIG, CONTROL_CONFIG, Ecustom_CONFIG
    
    # Seleccionar configuración base según el estilo
    style_configs = {
        "calibration": CALIBRATION_CONFIG,
        "control": CONTROL_CONFIG,
        "custom": Ecustom_CONFIG
    }
    
    if estilo not in style_configs:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Estilo '{estilo}' no reconocido, usando 'custom'")
        estilo = "custom"
    
    # Crear copia de la configuración base
    cfg = style_configs[estilo].copy()
    
    # Aplicar overrides si se proporcionan
    if overrides:
        cfg.update(overrides)
    
    # Sincronización automática de filtros basada en INTENSIDAD_POR_CAMPO
    intensidad_por_campo = cfg.get("INTENSIDAD_POR_CAMPO", {})
    
    if intensidad_por_campo and "tipouso" in intensidad_por_campo:
        tipos_configurados = list(intensidad_por_campo["tipouso"].keys())
        if tipos_configurados:
            # Actualizar los filtros para usar solo los tipos configurados
            if "FILTROS_CAMPOS" not in cfg:
                cfg["FILTROS_CAMPOS"] = {}
            
            # Mantener otros filtros (como apl) pero actualizar tipouso
            filtros_actuales = cfg["FILTROS_CAMPOS"].copy()
            filtros_actuales["tipouso"] = tipos_configurados
            
            # Si hay overrides específicos, remover filtros innecesarios como 'apl'
            # cuando no están en los campos del PO
            if overrides and "PO_CONFIG" in overrides:
                po_campos = overrides["PO_CONFIG"].get("campos", [])
                po_campos_lower = [c.lower() for c in po_campos]
                
                # Remover filtros para campos que no están en el PO
                filtros_limpios = {}
                for campo, filtro in filtros_actuales.items():
                    if campo == "tipouso" or campo.lower() in po_campos_lower:
                        filtros_limpios[campo] = filtro
                    else:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Removiendo filtro para campo '{campo}' (no presente en PO)")
                
                cfg["FILTROS_CAMPOS"] = filtros_limpios
            else:
                cfg["FILTROS_CAMPOS"] = filtros_actuales
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Filtros de tipouso actualizados dinámicamente: {tipos_configurados}")
    
    return cfg 