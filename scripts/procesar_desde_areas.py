"""
Script para procesar desde 04_areas_post_exclusion.gpkg usando las configuraciones actuales.
"""

import os
import sys
import logging
import geopandas as gpd
import pandas as pd
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path para poder importar los módulos
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from parcelas_fasa.pipeline.calculo_parcelas import calcular_cantidad_de_parcelas
from parcelas_fasa.pipeline.generacion_parcelas import generar_parcelas
from parcelas_fasa.utils.logging_utils import setup_logging

# Definir rutas por defecto
DEFAULT_INPUT_GPKG = r"C:\TRABAJO\06_proyectos\07_fasa2025\02_generacion_parcelas\01_parcelas_calibracion\01_first_run\20250516_e14_calibracion\04_areas_post_exclusion.gpkg"
DEFAULT_CSV_PATH = r"C:\TRABAJO\01_solicitud\73_recuperacion_parcelas_fasa25\info_excel\parcelas_faltantes_gridcode_v2.csv"

def verificar_columnas(gdf: gpd.GeoDataFrame, required_cols: list) -> bool:
    """
    Verifica que las columnas requeridas estén presentes en el GeoDataFrame.
    
    Args:
        gdf: GeoDataFrame a verificar
        required_cols: Lista de columnas requeridas
        
    Returns:
        bool: True si todas las columnas están presentes, False en caso contrario
    """
    missing_cols = [col for col in required_cols if col not in gdf.columns]
    if missing_cols:
        logger = logging.getLogger(__name__)
        logger.error(f"Columnas faltantes en el archivo de entrada: {missing_cols}")
        return False
    return True

def procesar_desde_areas(
    input_gpkg: str = DEFAULT_INPUT_GPKG,
    output_dir: str = None,
    custom_parcelas_csv: str = DEFAULT_CSV_PATH,
    min_distance: float = 80.0,
    buffer_distance: int = -30,
    area_minima_ha: float = 0.4,
    min_parcelas: int = 1,
    max_parcelas: int = None,
    intensidad: int = 80,
    use_intensidad_especifica: bool = False,
    intensidad_por_campo: dict = None
):
    """
    Procesa desde el archivo 04_areas_post_exclusion.gpkg usando las configuraciones especificadas.
    
    Args:
        input_gpkg: Ruta al archivo 04_areas_post_exclusion.gpkg
        output_dir: Directorio de salida
        custom_parcelas_csv: Ruta al CSV con conteo personalizado de parcelas (opcional)
        min_distance: Distancia mínima entre parcelas
        buffer_distance: Distancia de buffer en metros
        area_minima_ha: Área mínima en hectáreas
        min_parcelas: Mínimo de parcelas por grupo
        max_parcelas: Máximo de parcelas por grupo
        intensidad: Intensidad base (ha por parcela)
        use_intensidad_especifica: Si usar intensidades específicas por campo
        intensidad_por_campo: Diccionario con intensidades específicas
    """
    # Si no se especifica directorio de salida, usar el mismo del archivo de entrada
    if output_dir is None:
        output_dir = os.path.dirname(input_gpkg)
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Configurar archivo de log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(output_dir, f'procesamiento_{timestamp}.log')
    
    # Configurar logging
    setup_logging(log_file)
    logger = logging.getLogger(__name__)
    
    # Definir rutas de salida
    output_csv = os.path.join(output_dir, '05_cantidad_parcelas.csv')
    output_gpkg = os.path.join(output_dir, '05_cantidad_parcelas.gpkg')
    output_gpkg_dissolved = os.path.join(output_dir, '05_cantidad_parcelas_dissolved.gpkg')
    output_parcelas = os.path.join(output_dir, '06_parcelas.gpkg')
    
    try:
        # Leer el archivo de entrada
        logger.info(f"Leyendo archivo de entrada: {input_gpkg}")
        gdf = gpd.read_file(input_gpkg)
        
        # Verificar columnas requeridas
        required_cols = ['tipouso', 'zc_pira', 'gridcode']
        if not verificar_columnas(gdf, required_cols):
            raise ValueError("El archivo de entrada no contiene todas las columnas requeridas")
        
        # Definir campos para agrupar
        fields = ['tipouso', 'zc_pira']
        
        # Calcular cantidad de parcelas
        logger.info("Calculando cantidad de parcelas...")
        if custom_parcelas_csv:
            logger.info(f"Usando CSV personalizado: {custom_parcelas_csv}")
            
            # Verificar CSV personalizado
            custom_df = pd.read_csv(custom_parcelas_csv)
            csv_required_cols = ['tipouso', 'gridcode', 'zc_pira', 'conteo']
            if not all(col in custom_df.columns for col in csv_required_cols):
                missing_cols = [col for col in csv_required_cols if col not in custom_df.columns]
                raise ValueError(f"El CSV personalizado no contiene todas las columnas requeridas: {missing_cols}")
        
        dissolved_final = calcular_cantidad_de_parcelas(
            gdf=gdf,
            fields=fields,
            intensidad=intensidad,
            use_intensidad_especifica=use_intensidad_especifica,
            intensidad_por_campo=intensidad_por_campo or {},
            min_parcelas=min_parcelas,
            max_parcelas=max_parcelas,
            area_minima_ha=area_minima_ha,
            buffer_distance=buffer_distance,
            output_csv=output_csv,
            output_gpkg=output_gpkg,
            output_gpkg_dissolved_initial=output_gpkg_dissolved,
            custom_parcelas_csv=custom_parcelas_csv
        )
        
        # Verificar columnas en el resultado
        required_result_cols = ['tipouso', 'zc_pira', 'area_ha_original', 'n_parcelas', 'geometry']
        if not verificar_columnas(dissolved_final, required_result_cols):
            raise ValueError("El resultado no contiene todas las columnas requeridas")
        
        # Generar parcelas
        logger.info("Generando parcelas...")
        parcelas_gdf = generar_parcelas(
            gdf=dissolved_final,
            fields=fields,
            min_distance=min_distance,
            output_path=output_parcelas
        )
        
        logger.info("Proceso completado exitosamente")
        logger.info(f"Archivos generados:")
        logger.info(f"- CSV de cantidad de parcelas: {output_csv}")
        logger.info(f"- GPKG de cantidad de parcelas: {output_gpkg}")
        logger.info(f"- GPKG de parcelas disueltas: {output_gpkg_dissolved}")
        logger.info(f"- GPKG de parcelas generadas: {output_parcelas}")
        logger.info(f"- Archivo de log: {log_file}")
        
    except Exception as e:
        logger.error(f"Error durante el procesamiento: {str(e)}")
        raise

def main():
    """Función principal para ejecutar el script desde línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Procesar desde 04_areas_post_exclusion.gpkg')
    parser.add_argument('--input-gpkg', default=DEFAULT_INPUT_GPKG, help='Ruta al archivo 04_areas_post_exclusion.gpkg')
    parser.add_argument('--output-dir', help='Directorio de salida (por defecto: mismo que el archivo de entrada)')
    parser.add_argument('--csv', default=DEFAULT_CSV_PATH, help='Ruta al CSV con conteo personalizado de parcelas')
    parser.add_argument('--min-distance', type=float, default=80.0, help='Distancia mínima entre parcelas')
    parser.add_argument('--buffer-distance', type=int, default=-30, help='Distancia de buffer en metros')
    parser.add_argument('--area-minima', type=float, default=0.4, help='Área mínima en hectáreas')
    parser.add_argument('--min-parcelas', type=int, default=1, help='Mínimo de parcelas por grupo')
    parser.add_argument('--max-parcelas', type=int, help='Máximo de parcelas por grupo')
    parser.add_argument('--intensidad', type=int, default=80, help='Intensidad base (ha por parcela)')
    parser.add_argument('--use-intensidad-especifica', action='store_true', help='Usar intensidades específicas por campo')
    
    args = parser.parse_args()
    
    # Configurar intensidad por campo si se usa
    intensidad_por_campo = None
    if args.use_intensidad_especifica:
        intensidad_por_campo = {
            "tipouso": {
                "PIRA": 140,
                "EUNI": 100,
                "EUGL": 100,
                "EHNG": 100,
                "EGRN": 100
            }
        }
    
    procesar_desde_areas(
        input_gpkg=args.input_gpkg,
        output_dir=args.output_dir,
        custom_parcelas_csv=args.csv,
        min_distance=args.min_distance,
        buffer_distance=args.buffer_distance,
        area_minima_ha=args.area_minima,
        min_parcelas=args.min_parcelas,
        max_parcelas=args.max_parcelas,
        intensidad=args.intensidad,
        use_intensidad_especifica=args.use_intensidad_especifica,
        intensidad_por_campo=intensidad_por_campo
    )

if __name__ == "__main__":
    main() 