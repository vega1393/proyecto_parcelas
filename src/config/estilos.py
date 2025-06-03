"""
Configuraciones específicas para cada estilo de generación de parcelas.
"""

from src.config.config_base import BASE_CONFIG, filtrar_apl

# Configuración para estilo "calibración"
CALIBRATION_CONFIG = BASE_CONFIG.copy()
CALIBRATION_CONFIG.update({
    "USE_GRIDCODE": True,
    # Parámetros principales
    "INTENSIDAD": 80,
    "USE_INTENSIDAD_ESPECIFICA": True,
    "INTENSIDAD_POR_CAMPO": {
        "tipouso": {
            "PIRA": 140,
            "EUNI": 100,
            "EUGL": 100,
            "EHNG": 100,
            "EGRN": 100
        }
    },
    "MIN_PARCELAS": None,
    "MAX_PARCELAS": None,
    "AREA_MINIMA_HA": 0.4,
    "BUFFER_DISTANCE": -30,
    "MIN_DISTANCE": 80.0,
})

# Configuración para estilo "control"
CONTROL_CONFIG = BASE_CONFIG.copy()
CONTROL_CONFIG.update({
    "USE_GRIDCODE": True,
    # Parámetros principales
    "INTENSIDAD": 80,
    "USE_INTENSIDAD_ESPECIFICA": False,
    "INTENSIDAD_POR_CAMPO": {},
    "MIN_PARCELAS": 1,
    "MAX_PARCELAS": 20,
    "AREA_MINIMA_HA": 0.4,
    "BUFFER_DISTANCE": -30,
    "MIN_DISTANCE": 80.0,
    "FIELDS": ["zc_pira", "tipo_uso", "tipouso", "apl", "id_predio"],
})

# Configuración para estilo "especial"
ESPECIAL_CONFIG = BASE_CONFIG.copy()
ESPECIAL_CONFIG.update({
    "USE_GRIDCODE": False,  # Ejemplo: no usar gridcode
    # Parámetros principales
    "INTENSIDAD": 50,
    "USE_INTENSIDAD_ESPECIFICA": True,
    "INTENSIDAD_POR_CAMPO": {
        "tipouso": {
            "PIRA": 140
        }
    },
    "MIN_PARCELAS": None,
    "MAX_PARCELAS": 10,
    "AREA_MINIMA_HA": 0.3,
    "BUFFER_DISTANCE": -20,
    "MIN_DISTANCE": 60.0,
    "ID_PARCELA_INICIO": 100,
    "VERSION_PARCELA": "B",
    "FIELDS": ["zc_pira", "tipo_uso", "tipouso", "apl", "id_predio"],
}) 