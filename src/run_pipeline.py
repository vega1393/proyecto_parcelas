# run_pipeline.py
print("[DEBUG] INICIO RUN_PIPELINE")
import sys
import json
import os
import traceback
print("[DEBUG] IMPORTS OK")

pipeline_module = None
ejecutar_proceso_func = None # Placeholder para la función

try:
    print("[DEBUG] RUN_PIPELINE: Attempting to import 'src.core.pipeline' itself...")
    # Descomenta las siguientes líneas si quieres probar la importación de geopandas y pyogrio directamente aquí:
    # print("[DEBUG] RUN_PIPELINE: Attempting: import geopandas")
    # import geopandas
    # print("[DEBUG] RUN_PIPELINE: geopandas imported successfully by run_pipeline")
    # print("[DEBUG] RUN_PIPELINE: Attempting: import pyogrio")
    # import pyogrio
    # print("[DEBUG] RUN_PIPELINE: pyogrio imported successfully by run_pipeline")

    import src.core.pipeline # Intenta importar el módulo completo primero
    pipeline_module = src.core.pipeline
    print("[DEBUG] RUN_PIPELINE: Module 'src.core.pipeline' imported successfully.")
    print("[DEBUG] RUN_PIPELINE: Attempting to get 'ejecutar_proceso' from module...")
    ejecutar_proceso_func = pipeline_module.ejecutar_proceso
    print("[DEBUG] RUN_PIPELINE: IMPORT PIPELINE AND FUNCTION OK")
except Exception as e:
    error_message = f"Failed during import sequence in run_pipeline.py: {str(e)}"
    tb_message = traceback.format_exc()
    # Intenta enviar como JSON, pero también imprime en crudo por robustez
    try:
        print(json.dumps({"type": "error", "message": error_message, "traceback": tb_message}), flush=True)
    except Exception as json_e:
        sys.stderr.write(f"JSON DUMP FAILED in run_pipeline: {str(json_e)}\n")
    # Imprime directamente a stderr también, lo cual QProcess debería capturar.
    sys.stderr.write(f"RAW ERROR in run_pipeline.py: {error_message}\n")
    sys.stderr.write(f"RAW TRACEBACK in run_pipeline.py:\n{tb_message}\n")
    sys.stderr.flush() # Asegura que se escriba inmediatamente
    sys.exit(1) # Es crucial salir para que QProcess.finished se active y el GUI sepa que falló.

# Verificación adicional: si ejecutar_proceso_func no se asignó, es un error.
if not ejecutar_proceso_func:
    # Este caso debería ser capturado por sys.exit(1) en el except, pero como doble seguridad:
    err_msg_fallback = "Critical error: ejecutar_proceso_func could not be imported and was not set after try-except block."
    try:
        print(json.dumps({"type": "error", "message": err_msg_fallback}), flush=True)
    except Exception: # pragma: no cover
        pass
    sys.stderr.write(f"FATAL FALLBACK in run_pipeline.py: {err_msg_fallback}\n")
    sys.stderr.flush()
    sys.exit(1)

def main():
    print("[DEBUG] RUN_PIPELINE: MAIN INICIADO")
    if len(sys.argv) < 2:
        error_msg = "Missing config file argument."
        print(json.dumps({"type": "error", "message": error_msg}), flush=True)
        sys.stderr.write(f"ERROR in run_pipeline.py: {error_msg}\n")
        sys.exit(1)

    config_path = sys.argv[1]
    print(f"[DEBUG] RUN_PIPELINE: CONFIG PATH: {config_path}")

    if not os.path.exists(config_path):
        error_msg = f"Config file not found: {config_path}"
        print(json.dumps({"type": "error", "message": error_msg}), flush=True)
        sys.stderr.write(f"ERROR in run_pipeline.py: {error_msg}\n")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            params = json.load(f)
        print("[DEBUG] RUN_PIPELINE: CONFIG JSON CARGADO")
    except Exception as e:
        error_msg = f"Failed to read or parse config file {config_path}: {str(e)}"
        tb = traceback.format_exc()
        print(json.dumps({"type": "error", "message": error_msg, "traceback": tb}), flush=True)
        sys.stderr.write(f"ERROR in run_pipeline.py: {error_msg}\nTRACEBACK:\n{tb}\n")
        sys.exit(1)

    def progress_callback(value, status):
        # Asegura que el flush se haga para que el GUI reciba el mensaje a tiempo.
        print(json.dumps({"type": "progress", "value": value, "status": status}), flush=True)

    try:
        print("[DEBUG] RUN_PIPELINE: LLAMANDO ejecutar_proceso_func")
        # Llama a la función obtenida del módulo importado
        results = ejecutar_proceso_func(
            input_path=params["input_path"],
            output_dir=params["output_dir"],
            entrega=params.get("entrega"),
            estilo=params["style"], # 'pipeline.py' espera 'estilo', params tiene 'style'
            cfg_overrides=params["cfg_overrides"],
            progress_callback=progress_callback
        )
        print(json.dumps({"type": "success", "message": "Processing completed successfully."}), flush=True)
    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"Error during ejecutar_proceso_func: {str(e)}"
        print(json.dumps({"type": "error", "message": error_msg, "traceback": tb}), flush=True)
        # También a stderr para asegurar visibilidad si el GUI no lo muestra bien
        sys.stderr.write(f"ERROR in run_pipeline.py main try block: {error_msg}\nTRACEBACK:\n{tb}\n")
        sys.stderr.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()