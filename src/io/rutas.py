"""
Módulo para la gestión de rutas de archivos.
"""

import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def configurar_rutas(
    input_path: str, 
    output_dir: Optional[str] = None,
    delivery_config: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Configura las rutas de archivos para el procesamiento usando configuración de delivery.

    Args:
        input_path: Ruta del archivo de entrada
        output_dir: Directorio de salida (opcional)
        delivery_config: Configuración de delivery con códigos, fechas y nomenclatura

    Returns:
        Diccionario con todas las rutas configuradas
    """
    base_output_dir = output_dir or os.path.join(os.path.dirname(input_path), "outputs")
    
    # Configuración de delivery por defecto
    if not delivery_config:
        delivery_config = {
            "delivery_code": "d01",
            "date_today": "20250617",
            "base_prefix": "",
            "custom_suffix": "",
            "subdirectories": {
                "results": "results",
                "logs": "logs",
                "summary": "summary"
            }
        }
    
    # Construir nombre base para archivos
    date_str = delivery_config.get("date_today", "20250617")
    delivery_code = delivery_config.get("delivery_code", "d01")
    base_prefix = delivery_config.get("base_prefix", "")
    custom_suffix = delivery_config.get("custom_suffix", "")
    
    # Construir partes del nombre
    name_parts = []
    if base_prefix:
        name_parts.append(base_prefix)
    if delivery_code:
        name_parts.append(delivery_code.upper())
    
    base_name = "_".join(name_parts) if name_parts else "PARCELAS"
    if custom_suffix:
        base_name += custom_suffix
    
    # Crear estructura de directorios
    subdirs = delivery_config.get("subdirectories", {})
    results_dir = subdirs.get("results", "results")
    logs_dir = subdirs.get("logs", "logs")
    summary_dir = subdirs.get("summary", "summary")
    
    # Crear directorios
    full_results_dir = os.path.join(base_output_dir, results_dir)
    full_logs_dir = os.path.join(base_output_dir, logs_dir)
    full_summary_dir = os.path.join(base_output_dir, summary_dir)
    
    for directory in [base_output_dir, full_results_dir, full_logs_dir, full_summary_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
    
    rutas = {
        'input': input_path,
        'output_dir': base_output_dir,
        'results_dir': full_results_dir,
        'logs_dir': full_logs_dir,
        'summary_dir': full_summary_dir
    }
    
    # Configurar rutas para archivos de salida con nomenclatura profesional
    rutas.update({
        # Logs
        'log_file': os.path.join(full_logs_dir, f"{date_str}_{base_name}_proceso.log"),
        
        # Summary files
        'csv_resumen': os.path.join(full_summary_dir, f"{date_str}_{base_name}_resumen_parcelas_por_grupo.csv"),
        'csv_analisis': os.path.join(full_summary_dir, f"{date_str}_{base_name}_analisis_perdidas_parcelas.csv"),
        
        # Results - Archivos intermedios
        'gpkg_gridcode': os.path.join(full_results_dir, f"{date_str}_{base_name}_00_grilla_con_gridcode.gpkg"),
        'gpkg_inicial': os.path.join(full_results_dir, f"{date_str}_{base_name}_01_areas_agrupadas_inicial.gpkg"),
        'gpkg_areas': os.path.join(full_results_dir, f"{date_str}_{base_name}_02_areas_filtradas_buffer.gpkg"),
        'gpkg_exclusion': os.path.join(full_results_dir, f"{date_str}_{base_name}_04_areas_post_exclusion.gpkg"),
        'gpkg_parcelas': os.path.join(full_results_dir, f"{date_str}_{base_name}_05_parcelas_generadas.gpkg"),
        'gpkg_poligonos': os.path.join(full_results_dir, f"{date_str}_{base_name}_06_poligonos_parcelas.gpkg"),
        'gpkg_po': os.path.join(full_results_dir, f"{date_str}_{base_name}_07_parcelas_con_po.gpkg"),
        
        # Results - Archivo final
        'gpkg_final': os.path.join(full_results_dir, f"{date_str}_{base_name}_PARCELAS_FINALES.gpkg")
    })
    
    logger.info(f"Configured file naming with pattern: {date_str}_{base_name}_*")
    logger.info(f"Output structure: {base_output_dir} -> {results_dir}/, {logs_dir}/, {summary_dir}/")
    
    return rutas 