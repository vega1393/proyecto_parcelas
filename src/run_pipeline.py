"""
Wrapper script to run the parcel generation pipeline from a JSON config file.
Emits progress and logs to stdout for integration with PyQt QProcess.
"""

import sys
import json
import os
import traceback
from src.core.pipeline import ejecutar_proceso

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"type": "error", "message": "Missing config file argument."}))
        sys.exit(1)
    config_path = sys.argv[1]
    if not os.path.exists(config_path):
        print(json.dumps({"type": "error", "message": f"Config file not found: {config_path}"}))
        sys.exit(1)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            params = json.load(f)
    except Exception as e:
        print(json.dumps({"type": "error", "message": f"Failed to read config: {str(e)}"}))
        sys.exit(1)
    def progress_callback(value, status):
        print(json.dumps({"type": "progress", "value": value, "status": status}), flush=True)
    try:
        results = ejecutar_proceso(
            input_path=params["input_path"],
            output_dir=params["output_dir"],
            entrega=params.get("entrega"),
            estilo=params["style"],
            cfg_overrides=params["cfg_overrides"],
            progress_callback=progress_callback
        )
        print(json.dumps({"type": "success", "message": "Processing completed successfully."}), flush=True)
    except Exception as e:
        tb = traceback.format_exc()
        print(json.dumps({"type": "error", "message": str(e), "traceback": tb}), flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 