#!/usr/bin/env python3
"""
Script de debug para verificar que los valores se guarden y carguen correctamente
"""

import json
import os
from src.utils.settings import load_gui_settings, save_gui_settings

def test_settings_cycle():
    """Prueba el ciclo completo de guardado y carga de configuraciones."""
    
    print("=== PRUEBA DE GUARDADO Y CARGA DE CONFIGURACIONES ===\n")
    
    # 1. Cargar configuración actual
    print("1. Cargando configuración actual...")
    current_settings = load_gui_settings()
    
    # Mostrar valores clave del pipeline
    pipeline_values = current_settings.get("cfg_overrides", {})
    print(f"   PROJECTED_CRS: {pipeline_values.get('PROJECTED_CRS', 'No definido')}")
    print(f"   AREA_MINIMA_HA: {pipeline_values.get('AREA_MINIMA_HA', 'No definido')}")
    print(f"   BUFFER_DISTANCE: {pipeline_values.get('BUFFER_DISTANCE', 'No definido')}")
    print(f"   MIN_DISTANCE: {pipeline_values.get('MIN_DISTANCE', 'No definido')}")
    print(f"   ID_PARCELA_INICIO: {pipeline_values.get('ID_PARCELA_INICIO', 'No definido')}")
    print(f"   VERSION_PARCELA: {pipeline_values.get('VERSION_PARCELA', 'No definido')}")
    
    # 2. Modificar algunos valores para la prueba
    print("\n2. Modificando valores para prueba...")
    test_settings = current_settings.copy()
    test_overrides = test_settings.get("cfg_overrides", {}).copy()
    
    # Valores de prueba únicos
    test_overrides["PROJECTED_CRS"] = 31982  # Valor del JSON
    test_overrides["AREA_MINIMA_HA"] = 0.3
    test_overrides["BUFFER_DISTANCE"] = -20
    test_overrides["MIN_DISTANCE"] = 60.0
    test_overrides["ID_PARCELA_INICIO"] = 1
    test_overrides["VERSION_PARCELA"] = "A"
    
    test_settings["cfg_overrides"] = test_overrides
    
    print("   Valores modificados:")
    print(f"   PROJECTED_CRS: {test_overrides['PROJECTED_CRS']}")
    print(f"   AREA_MINIMA_HA: {test_overrides['AREA_MINIMA_HA']}")
    print(f"   BUFFER_DISTANCE: {test_overrides['BUFFER_DISTANCE']}")
    print(f"   MIN_DISTANCE: {test_overrides['MIN_DISTANCE']}")
    print(f"   ID_PARCELA_INICIO: {test_overrides['ID_PARCELA_INICIO']}")
    print(f"   VERSION_PARCELA: {test_overrides['VERSION_PARCELA']}")
    
    # 3. Guardar configuración modificada
    print("\n3. Guardando configuración modificada...")
    save_gui_settings(test_settings)
    print("   ✓ Configuración guardada")
    
    # 4. Recargar desde archivo
    print("\n4. Recargando desde archivo...")
    reloaded_settings = load_gui_settings()
    reloaded_overrides = reloaded_settings.get("cfg_overrides", {})
    
    print("   Valores recargados:")
    print(f"   PROJECTED_CRS: {reloaded_overrides.get('PROJECTED_CRS', 'No encontrado')}")
    print(f"   AREA_MINIMA_HA: {reloaded_overrides.get('AREA_MINIMA_HA', 'No encontrado')}")
    print(f"   BUFFER_DISTANCE: {reloaded_overrides.get('BUFFER_DISTANCE', 'No encontrado')}")
    print(f"   MIN_DISTANCE: {reloaded_overrides.get('MIN_DISTANCE', 'No encontrado')}")
    print(f"   ID_PARCELA_INICIO: {reloaded_overrides.get('ID_PARCELA_INICIO', 'No encontrado')}")
    print(f"   VERSION_PARCELA: {reloaded_overrides.get('VERSION_PARCELA', 'No encontrado')}")
    
    # 5. Verificar coincidencia
    print("\n5. Verificando coincidencia...")
    errors = []
    
    for key in ["PROJECTED_CRS", "AREA_MINIMA_HA", "BUFFER_DISTANCE", "MIN_DISTANCE", "ID_PARCELA_INICIO", "VERSION_PARCELA"]:
        original = test_overrides.get(key)
        reloaded = reloaded_overrides.get(key)
        
        if original != reloaded:
            errors.append(f"   ❌ {key}: esperado {original}, obtenido {reloaded}")
        else:
            print(f"   ✓ {key}: {original}")
    
    if errors:
        print("\n❌ ERRORES ENCONTRADOS:")
        for error in errors:
            print(error)
        return False
    else:
        print("\n✅ TODAS LAS VERIFICACIONES PASARON")
        return True

def check_json_file():
    """Verifica el contenido del archivo JSON directamente."""
    print("\n=== VERIFICACIÓN DIRECTA DEL ARCHIVO JSON ===")
    
    json_file = "gui_settings.json"
    if not os.path.exists(json_file):
        print(f"❌ Archivo {json_file} no existe")
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cfg_overrides = data.get("cfg_overrides", {})
        print("Valores en el archivo JSON:")
        print(f"   PROJECTED_CRS: {cfg_overrides.get('PROJECTED_CRS', 'No encontrado')}")
        print(f"   AREA_MINIMA_HA: {cfg_overrides.get('AREA_MINIMA_HA', 'No encontrado')}")
        print(f"   BUFFER_DISTANCE: {cfg_overrides.get('BUFFER_DISTANCE', 'No encontrado')}")
        print(f"   MIN_DISTANCE: {cfg_overrides.get('MIN_DISTANCE', 'No encontrado')}")
        print(f"   ID_PARCELA_INICIO: {cfg_overrides.get('ID_PARCELA_INICIO', 'No encontrado')}")
        print(f"   VERSION_PARCELA: '{cfg_overrides.get('VERSION_PARCELA', 'No encontrado')}'")
        
    except Exception as e:
        print(f"❌ Error leyendo JSON: {e}")

if __name__ == "__main__":
    # Verificar archivo JSON actual
    check_json_file()
    
    print("\n" + "="*60)
    
    # Ejecutar prueba completa
    success = test_settings_cycle()
    
    if success:
        print("\n🎉 PRUEBA EXITOSA: Los valores se guardan y cargan correctamente")
    else:
        print("\n⚠️  PRUEBA FALLIDA: Hay problemas con el guardado/carga") 