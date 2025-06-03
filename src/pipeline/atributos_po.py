"""
Módulo para la asignación de atributos del Plan Operativo (PO) a las parcelas.
"""

import logging
import geopandas as gpd
import pyogrio
from typing import Dict, Any, Optional, List, Tuple

from src.utils.geo_utils import verificar_y_transformar_crs

logger = logging.getLogger(__name__)


def asignar_atributos_po(
    parcelas_gdf: gpd.GeoDataFrame,
    po_config: Dict[str, Any],
    crs_target: int,
    output_path: Optional[str] = None,
    entrega: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    Asigna atributos desde el Plan Operativo (PO) a las parcelas generadas mediante
    una intersección espacial. Opcionalmente genera un ID FASA único.

    El ID FASA es un identificador único para cada parcela, formado por
    tipo de vegetación + ID de predio + número secuencial + código de entrega (opcional).

    Args:
        parcelas_gdf: GeoDataFrame con las parcelas generadas
        po_config: Configuración del PO con las claves:
            - ruta: Ruta al archivo GIS del Plan Operativo
            - campos: Lista de campos a extraer del PO
            - generar_id_fasa: Bool que indica si generar el ID FASA
            - campo_id_fasa: Nombre del campo para el ID FASA
            - prefijo_duplicado: Prefijo a usar si el campo ya existe
            - campos_id_fasa: Dict con las claves 'tipo' y 'predio' que mapean
              a nombres de columnas usadas para generar el ID FASA
        crs_target: CRS objetivo (código EPSG)
        output_path: Ruta donde guardar el resultado (opcional)
        entrega: Código de entrega a incluir en el ID FASA (opcional)

    Returns:
        GeoDataFrame con los atributos del PO y el ID FASA asignados
    """
    logger.info("Iniciando asignación de atributos desde PO...")
    
    # Importar la función leer_capa
    from src.io.lectura import leer_capa
    
    # Cargar PO
    try:
        ruta_po = po_config.get('ruta')
        capa_po = po_config.get('capa')
        logger.info(f"Cargando PO desde {ruta_po}" + (f", capa {capa_po}" if capa_po else ""))
        
        po_gdf = leer_capa(ruta_po, capa_po)
        
        # Verificar y transformar CRS
        po_gdf = verificar_y_transformar_crs(po_gdf, "PO", crs_target)
    except Exception as e:
        logger.error(f"Error al cargar PO: {str(e)}")
        return parcelas_gdf

    campos_po = [campo.lower() for campo in po_config["campos"]]  # Convertir campos solicitados a minúsculas
    logger.info(f"Campos solicitados (en minúsculas): {campos_po}")
    
    # Convertir columnas del PO a minúsculas
    columnas_originales = list(po_gdf.columns)
    po_gdf.columns = po_gdf.columns.str.lower()
    
    # Mostrar campos disponibles para diagnóstico
    logger.info(f"Campos disponibles en PO original: {columnas_originales}")
    logger.info(f"Campos disponibles en PO (minúsculas): {list(po_gdf.columns)}")

    campos_disponibles = [c for c in campos_po if c in po_gdf.columns]
    if not campos_disponibles:
        campos_disponibles_str = ", ".join(po_gdf.columns)
        campos_solicitados_str = ", ".join(campos_po)
        raise ValueError(
            f"Ninguno de los campos solicitados existe en la capa de PO. " 
            f"Campos solicitados: {campos_solicitados_str}. "
            f"Campos disponibles: {campos_disponibles_str}"
        )

    result_gdf = gpd.sjoin(
        parcelas_gdf,
        po_gdf[campos_disponibles + ['geometry']],
        how='left',
        predicate='intersects'
    )
    
    if 'index_right' in result_gdf.columns:
        result_gdf.drop(columns=['index_right'], inplace=True)

    # Mover datos de _right a la columna principal
    for campo in campos_disponibles:
        if f"{campo}_right" in result_gdf.columns:
            result_gdf[campo] = result_gdf[f"{campo}_right"]
            result_gdf.drop(columns=[f"{campo}_right"], inplace=True)

    # Eliminar duplicados con sufijo _left
    left_columns = [col for col in result_gdf.columns if col.endswith('_left')]
    for col_left in left_columns:
        # Obtener el nombre base de la columna (sin el sufijo _left)
        col_base = col_left[:-5]  # Eliminar los últimos 5 caracteres (_left)
        # Si la columna base también existe, mantener esa y eliminar la _left
        if col_base in result_gdf.columns:
            result_gdf.drop(columns=[col_left], inplace=True)
        # Si solo existe la versión _left, renombrarla a la versión base
        else:
            result_gdf[col_base] = result_gdf[col_left]
            result_gdf.drop(columns=[col_left], inplace=True)
            logger.info(f"Columna {col_left} renombrada a {col_base}")

    # Generar ID FASA
    campo_final = None
    if po_config.get("generar_id_fasa", True):
        logger.info("Generando ID FASA...")
        campo_tipo = po_config.get("campos_id_fasa", {}).get('tipo', 'tipouso')
        campo_predio = po_config.get("campos_id_fasa", {}).get('predio', 'id_predio')
        
        if campo_tipo not in result_gdf.columns or campo_predio not in result_gdf.columns:
            logger.warning(
                f"No se puede generar ID FASA: faltan campos {campo_tipo}, {campo_predio}")
        else:
            campo_final = po_config.get("campo_id_fasa", "id_parcela_fasa")
            if campo_final in result_gdf.columns:
                campo_final = f"{po_config.get('prefijo_duplicado', 'NEW_')}{campo_final}"
                logger.warning(
                    f"Campo {campo_final} ya existe, usando {campo_final}")

            result_gdf = result_gdf.sort_values([campo_predio, campo_tipo])
            result_gdf['_temp_serial'] = result_gdf.groupby(
                campo_predio).cumcount() + 1
            result_gdf[campo_final] = (
                result_gdf[campo_tipo].astype(str) + '_' +
                result_gdf[campo_predio].astype(str) + '_' +
                result_gdf['_temp_serial'].astype(str).str.zfill(3) +
                (f'_{entrega}' if entrega else '')
            )
            result_gdf.drop(columns=['_temp_serial'], inplace=True)

    # Guardar
    if output_path:
        logger.info(f"Guardando parcelas con PO en: {output_path}")
        pyogrio.write_dataframe(result_gdf, output_path)

    return result_gdf


def reordenar_columnas(
    gdf: gpd.GeoDataFrame,
    output_path: Optional[str] = None,
    output_layer: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    Reordena las columnas del GeoDataFrame para una mejor visualización.
    
    Args:
        gdf: GeoDataFrame a reordenar
        output_path: Ruta para guardar el resultado (opcional)
        output_layer: Nombre de la capa para guardar (opcional)
        
    Returns:
        GeoDataFrame con las columnas reordenadas
    """
    logger.info("Reordenando columnas...")
    column_mapping = {
        'id_parce_1': 'id_parcela_fasa'
    }
    gdf = gdf.rename(columns=column_mapping)

    desired_columns = [
        'id_parcela_fasa', 'id_predio', 'id_rodal', 'apl',
        'tipo_uso', 'tipouso', 'area_m2', 'gridcode',
        'punto_x', 'punto_y', 'geometry'
    ]
    existing_columns = [c for c in desired_columns if c in gdf.columns]
    additional_columns = [c for c in gdf.columns if c not in desired_columns]
    final_columns = existing_columns + additional_columns
    gdf_reordered = gdf[final_columns].copy()

    if output_path:
        if not output_layer:
            output_layer = 'parcelas_reordenadas'
        logger.info(f"Guardando GPKG reordenado en: {output_path}")
        try:
            pyogrio.write_dataframe(
                gdf_reordered,
                output_path,
                layer=output_layer,
                driver="GPKG"
            )
        except Exception as e:
            logger.error(f"Error al guardar GPKG: {str(e)}")
            shp_path = output_path.replace('.gpkg', '.shp')
            logger.info(f"Intentando guardar como shapefile: {shp_path}")
            pyogrio.write_dataframe(gdf_reordered, shp_path)

    return gdf_reordered 