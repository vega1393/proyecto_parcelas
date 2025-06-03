"""
GUI settings utilities for the Parcel Generator project.
All configuration is stored in JSON format.
"""

import os
import json
from typing import Any, Dict

SETTINGS_FILE = os.path.join(os.getcwd(), "gui_settings.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "input_path": "",
    "output_dir": "",
    "style": "calibration",
    "custom_params": {
        "intensity": 50,
        "min_parcels": 1,
        "max_parcels": 10,
        "min_area": 0.3,
        "buffer_distance": -20,
        "min_distance": 60.0
    },
    "po_config": {
        "path": "",
        "layer": "",
        "fields": []
    },
    "exclusion_list": [],
    "intensity_by_field": {}
}

def load_gui_settings() -> Dict[str, Any]:
    """
    Loads GUI settings from a JSON file. Returns defaults if not found or error.
    """
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_SETTINGS, **data}
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_gui_settings(settings: Dict[str, Any]) -> None:
    """
    Saves GUI settings to a JSON file.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        # In production, log this error
        pass 