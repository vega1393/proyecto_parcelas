# src/run_pipeline.py

import sys
import json
import os
import traceback
import shutil

# No tener código ejecutable (prints, imports complejos) a nivel de módulo.
# Solo definiciones de funciones y clases si las hubiera.

def main():
    """
    Punto de entrada principal para ejecutar el pipeline desde la línea de comandos.
    Todo el código se mueve aquí para ser seguro con multiprocessing.
    """
    
    # Configurar logging condicional basado en variable de entorno
    pipeline_log_level = os.environ.get("PIPELINE_LOG_LEVEL", "INFO")
    
    # Función helper para logging condicional
    def debug_print(message):
        """Solo imprime mensajes DEBUG si el nivel de logging lo permite."""
        if pipeline_log_level == "DEBUG":
            print(f"[DEBUG] {message}")
    
    debug_print("INICIO DEL PROCESO PRINCIPAL DE RUN_PIPELINE")

    # Mover las importaciones que son parte de la lógica aquí dentro
    try:
        from src.core.pipeline import ejecutar_proceso
        from src.utils.logging_utils import setup_logging
        debug_print("Módulos del pipeline importados correctamente.")
    except ImportError as e:
        # Este es un error crítico, lo reportamos en JSON y salimos
        error_message = f"Fallo crítico durante la importación inicial en run_pipeline.py: {e}"
        tb_lines = traceback.format_exc().splitlines()
        print(json.dumps({"type": "error", "message": error_message, "traceback_lines": tb_lines}), flush=True)
        sys.exit(1)

    if len(sys.argv) < 2:
        error_msg = "Argumento de archivo de configuración faltante."
        print(json.dumps({"type": "error", "message": error_msg}), flush=True)
        sys.exit(1)

    config_path = sys.argv[1]
    debug_print(f"Ruta de configuración recibida: {config_path}")

    if not os.path.exists(config_path):
        error_msg = f"Archivo de configuración no encontrado: {config_path}"
        print(json.dumps({"type": "error", "message": error_msg}), flush=True)
        sys.exit(1)

    # Cargar configuración
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        debug_print("Configuración JSON cargada.")
        
    except Exception as e:
        error_msg = f"Error cargando configuración JSON: {e}"
        print(json.dumps({"type": "error", "message": error_msg}), flush=True)
        sys.exit(1)

    # Callback para reportar progreso
    def progress_callback(value, status):
        print(json.dumps({"type": "progress", "value": value, "status": status}), flush=True)

    try:
        debug_print("Llamando a ejecutar_proceso...")
        
        # Extraer delivery config si está presente
        delivery_config = config.get('delivery_config')
        if delivery_config:
            debug_print(f"Delivery config extracted: {delivery_config}")
        
        resultados = ejecutar_proceso(
            input_path=config["input_path"],
            output_dir=config.get("output_dir"),
            entrega=config.get("entrega"),
            estilo=config.get("style", "calibration"),
            cfg_overrides=config.get("cfg_overrides", {}),
            progress_callback=progress_callback,
            use_csv=config.get("use_csv", False),
            csv_path=config.get("csv_path"),
            grouping_fields=config.get("grouping_fields"),
            delivery_config=delivery_config,
            gridcode_column_csv=config.get("gridcode_column_csv")
        )
        
        print(json.dumps({"type": "success", "message": "Proceso completado exitosamente", "resultados": "Ver archivos de salida"}), flush=True)
        
        # Limpiar archivo temporal de configuración si existe
        if os.path.exists(config_path) and config_path.startswith(os.path.join(os.path.dirname(__file__), "src", "json_config", "tmp")):
            try:
                # Copiar archivo temporal al directorio de salida antes de eliminarlo
                output_dir = config.get("output_dir")
                if output_dir and os.path.exists(output_dir):
                    # Crear directorio de configuraciones si no existe
                    config_history_dir = os.path.join(output_dir, "config")
                    os.makedirs(config_history_dir, exist_ok=True)
                    
                    # Generar nombre descriptivo para el archivo de configuración
                    temp_filename = os.path.basename(config_path)
                    delivery_config = config.get("delivery_config", {})
                    date_str = delivery_config.get("date_today", "")
                    delivery_code = delivery_config.get("delivery_code", "")
                    
                    if date_str and delivery_code:
                        config_filename = f"{date_str}_{delivery_code.upper()}_pipeline_config_executed.json"
                    else:
                        config_filename = f"pipeline_config_executed_{temp_filename}"
                    
                    config_dest_path = os.path.join(config_history_dir, config_filename)
                    
                    # Copiar archivo temporal al directorio de salida
                    shutil.copy2(config_path, config_dest_path)
                    print(f"[INFO] Configuration saved to output directory: {config_dest_path}")
                
                # Ahora eliminar el archivo temporal
                os.remove(config_path)
                print(f"[INFO] Removed temporary config: {config_path}")
            except Exception as e:
                print(f"[WARNING] Could not process temporary config file: {e}")
        
    except Exception as e:
        error_message = f"Error durante la ejecución del pipeline: {str(e)}"
        tb_lines = traceback.format_exc().splitlines()
        print(json.dumps({"type": "error", "message": error_message, "traceback_lines": tb_lines}), flush=True)
        sys.exit(1)


# El bloque de seguridad que hace que todo funcione
if __name__ == "__main__":
    # Esta es la única sección que se ejecuta cuando corres el script directamente.
    # Los procesos hijos que se importan no ejecutarán esto.
    main()