"""
Módulo para la gestión de rutas de archivos.
"""

import os
from typing import Dict, Any, Optional


def configurar_rutas(input_path: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Configura las rutas de archivos para el procesamiento.

    Args:
        input_path: Ruta del archivo de entrada
        output_dir: Directorio de salida (opcional)

    Returns:
        Diccionario con todas las rutas configuradas
    """
    rutas = {
        'input': input_path,
        'output_dir': output_dir or os.path.join(os.path.dirname(input_path), "outputs")
    }
    
    # Crear directorio de salida si no existe
    if not os.path.exists(rutas['output_dir']):
        os.makedirs(rutas['output_dir'])

    # Configurar rutas para archivos de salida
    rutas.update({
        'log_file': os.path.join(rutas['output_dir'], "proceso.log"),
        'csv_resumen': os.path.join(rutas['output_dir'], "01_resumen_parcelas_por_grupo.csv"),
        'gpkg_inicial': os.path.join(rutas['output_dir'], "01_areas_agrupadas_inicial.gpkg"),
        'gpkg_areas': os.path.join(rutas['output_dir'], "02_areas_filtradas_buffer.gpkg"),
        'gpkg_exclusion': os.path.join(rutas['output_dir'], "04_areas_post_exclusion.gpkg"),
        'gpkg_parcelas': os.path.join(rutas['output_dir'], "05_parcelas_generadas.gpkg"),
        'gpkg_poligonos': os.path.join(rutas['output_dir'], "06_poligonos_parcelas.gpkg"),
        'gpkg_po': os.path.join(rutas['output_dir'], "07_parcelas_con_po.gpkg"),
        'gpkg_final': os.path.join(rutas['output_dir'], "08_parcelas_reordenadas.gpkg"),
        'csv_analisis': os.path.join(rutas['output_dir'], "analisis_perdidas_parcelas.csv")
    })
    
    return rutas 