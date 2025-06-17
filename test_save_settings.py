#!/usr/bin/env python3
"""
Test script to verify that Save Settings functionality works correctly.
"""

import json
import os
import sys

def test_save_settings():
    """Test if gui_settings.json contains all expected configurations."""
    
    settings_file = "gui_settings.json"
    
    if not os.path.exists(settings_file):
        print("❌ ERROR: gui_settings.json no encontrado")
        return False
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except Exception as e:
        print(f"❌ ERROR: No se pudo leer gui_settings.json: {e}")
        return False
    
    print("🔍 VERIFICANDO CONFIGURACIONES GUARDADAS...")
    print("=" * 50)
    
    # Verificar configuraciones básicas
    basic_configs = [
        "input_path", "output_dir", "style", "use_csv", 
        "grouping_fields", "po_config", "exclusion_list"
    ]
    
    for config in basic_configs:
        if config in settings:
            print(f"✅ {config}: PRESENTE")
        else:
            print(f"❌ {config}: FALTANTE")
    
    # Verificar configuraciones nuevas
    new_configs = ["gridcode_config", "delivery_config", "cfg_overrides"]
    
    for config in new_configs:
        if config in settings:
            print(f"✅ {config}: PRESENTE")
            if config == "cfg_overrides":
                overrides = settings[config]
                if overrides:
                    print(f"   📋 cfg_overrides contiene: {list(overrides.keys())}")
                    
                    # Verificar tipos de uso específicos
                    if "USE_INTENSIDAD_ESPECIFICA" in overrides:
                        print(f"   ✅ USE_INTENSIDAD_ESPECIFICA: {overrides['USE_INTENSIDAD_ESPECIFICA']}")
                    
                    if "INTENSIDAD_POR_CAMPO" in overrides:
                        intensidad = overrides["INTENSIDAD_POR_CAMPO"]
                        if "tipouso" in intensidad:
                            tipos = intensidad["tipouso"]
                            print(f"   ✅ Tipos de uso configurados: {list(tipos.keys())}")
                            print(f"   📊 Intensidades: {tipos}")
                        else:
                            print(f"   ⚠️  INTENSIDAD_POR_CAMPO sin tipouso")
                    else:
                        print(f"   ⚠️  cfg_overrides sin INTENSIDAD_POR_CAMPO")
                else:
                    print(f"   ⚠️  cfg_overrides está vacío")
        else:
            print(f"❌ {config}: FALTANTE")
    
    # Verificar configuración del PO
    print("\n🔍 VERIFICANDO CONFIGURACIÓN DEL PLAN OPERATIVO...")
    po_config = settings.get("po_config", {})
    if po_config:
        print(f"✅ PO ruta: {po_config.get('ruta', 'N/A')}")
        print(f"✅ PO capa: {po_config.get('capa', 'N/A')}")
        print(f"✅ PO campos: {po_config.get('campos', [])}")
        print(f"✅ PO campos_id_fasa: {po_config.get('campos_id_fasa', {})}")
    else:
        print("❌ PO config faltante")
    
    # Verificar GridCode
    print("\n🔍 VERIFICANDO CONFIGURACIÓN DE GRIDCODE...")
    gridcode_config = settings.get("gridcode_config", {})
    if gridcode_config:
        enabled = gridcode_config.get("enabled", False)
        print(f"✅ GridCode habilitado: {enabled}")
        if enabled:
            params = gridcode_config.get("gridcode_params", {})
            print(f"✅ GridCode parámetros: {list(params.keys())}")
    else:
        print("❌ GridCode config faltante")
    
    print("\n" + "=" * 50)
    print("✅ VERIFICACIÓN COMPLETADA")
    
    return True

if __name__ == "__main__":
    test_save_settings() 