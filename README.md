# 🌍 Parcel Generator Enhanced v1.1

## 📋 Descripción General

**Parcel Generator Enhanced** es una aplicación profesional de escritorio para la **generación automatizada de parcelas geoespaciales** en proyectos de ingeniería forestal, geomensura y SIG. La aplicación permite crear esquemas de muestreo e inventario de manera eficiente y precisa.

### 🆕 **Nuevas Funcionalidades v1.1**
- ✅ **Soporte completo para Geodatabases de Esri (.gdb)**
- ✅ Selección asistida de archivos geoespaciales
- ✅ Interfaz mejorada con controles centralizados
- ✅ Conservación automática de configuraciones
- ✅ Manejo robusto de procesos y logs

---

## 🚀 Instalación y Configuración (Para Usuarios Sin Conocimientos Técnicos)

### 📋 **Requisitos del Sistema**
- **Sistema Operativo**: Windows 10/11, macOS 10.14+, o Linux Ubuntu 18.04+
- **Memoria RAM**: Mínimo 4GB (recomendado 8GB)
- **Espacio en Disco**: 2GB libres
- **Conexión a Internet**: Solo para la instalación inicial

### 🔧 **Paso 1: Instalar Python**

#### **Windows:**
1. Ve a [python.org/downloads](https://python.org/downloads)
2. Descarga **Python 3.9 o superior** (recomendado Python 3.11)
3. **IMPORTANTE**: Durante la instalación, marca la casilla **"Add Python to PATH"**
4. Completa la instalación con las opciones por defecto

#### **macOS:**
1. Instala **Homebrew** (si no lo tienes):
   - Abre Terminal y ejecuta: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Instala Python: `brew install python`

#### **Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### 📁 **Paso 2: Descargar la Aplicación**
1. Descarga el proyecto como ZIP o clona el repositorio
2. Extrae los archivos en una carpeta fácil de encontrar (ej: `C:\ParcelGenerator` en Windows)

### 🐍 **Paso 3: Crear Entorno Virtual**

#### **Windows (PowerShell o CMD):**
```cmd
# Navegar a la carpeta del proyecto
cd C:\ParcelGenerator

# Crear entorno virtual
    python -m venv venv

# Activar entorno virtual
venv\Scripts\activate
    ```

#### **macOS/Linux (Terminal):**
        ```bash
# Navegar a la carpeta del proyecto
cd /ruta/a/ParcelGenerator

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
        source venv/bin/activate
        ```

### 📦 **Paso 4: Instalar Dependencias**
Con el entorno virtual activado:
    ```bash
    pip install -r requirements.txt
    ```

**Nota**: La instalación puede tardar 5-10 minutos. Es normal ver muchos mensajes durante el proceso.

### ▶️ **Paso 5: Ejecutar la Aplicación**
```bash
python main.py
```

### 🎯 **Verificación de Instalación**
Si todo está correcto, verás la ventana principal de la aplicación con:
- Pestañas en la parte superior (Pipeline, Sampling Method, etc.)
- Botones de ejecución (🚀 Run Pipeline, ⏹️ Stop)
- Área de logs en la parte inferior

---

## 🗂️ **Formatos de Archivo Soportados**

La aplicación soporta todos los formatos geoespaciales estándar:

| Formato | Extensión | Descripción | Recomendación |
|---------|-----------|-------------|---------------|
| **GeoPackage** | `.gpkg` | Formato moderno y eficiente | ⭐ **Recomendado** |
| **Shapefile** | `.shp` | Formato clásico de ESRI | ✅ Compatible |
| **Geodatabase** | `.gdb` | Base de datos de ESRI | ✅ **¡NUEVO!** Soporte completo |
| **GeoJSON** | `.geojson` | Formato web estándar | ✅ Compatible |
| **KML** | `.kml` | Google Earth | ✅ Compatible |
| **GML** | `.gml` | Geography Markup Language | ✅ Compatible |

### 🏛️ **Trabajando con Geodatabases (.gdb)**

Las **Geodatabases de Esri** son carpetas especiales que contienen datos geoespaciales. La aplicación incluye soporte nativo para estos archivos:

#### **Cómo Seleccionar una Geodatabase:**
1. Haz clic en cualquier botón **"Browse"** o **"Buscar"**
2. Si no ves tu archivo .gdb en el diálogo, **cancela el diálogo**
3. Aparecerá un mensaje: *"¿Quiere seleccionar una Geodatabase (.gdb)?"*
4. Haz clic en **"Sí"**
5. Selecciona la carpeta que termine en `.gdb`
6. La aplicación validará automáticamente el archivo

---

## 🎯 **Guía de Uso Rápido**

### 🔄 **Flujo de Trabajo Básico**

#### **1. Configuración Inicial (Tab: Pipeline)**
- **Input File**: Selecciona tu archivo de datos (shapefile, geopackage, o geodatabase)
- **Output Directory**: Elige dónde guardar los resultados
- **Processing Style**: Selecciona "calibration", "control", o "custom"

#### **2. Método de Muestreo (Tab: Sampling Method)**
- **Opción A - CSV**: Si tienes un archivo CSV con especificaciones
- **Opción B - Intensidad**: Define porcentaje de muestreo (ej: 12%)

#### **3. Configuraciones Adicionales (Opcional)**
- **Plan Operativo**: Si tienes datos de PO para enriquecer
- **Exclusion Layers**: Áreas a excluir (caminos, ríos, etc.)
- **GridCode**: Para códigos automáticos
- **Delivery**: Configurar nombres de archivos

#### **4. Ejecución**
1. Revisa la configuración con **"Show Complete Configuration Summary"**
2. Haz clic en **🚀 Run Pipeline**
3. Monitorea el progreso en los logs
4. Los resultados aparecerán en tu directorio de salida

---

## 📚 **Características Técnicas**

### 🏗️ **Arquitectura del Sistema**
- **Frontend**: PyQt6 para interfaz gráfica moderna
- **Backend**: GeoPandas + Shapely para procesamiento geoespacial
- **I/O**: Fiona + PyOGRIO para lectura de archivos
- **Procesamiento**: Pipeline modular y configurable

### 🔧 **Funcionalidades Avanzadas**
- **Pipeline Configurable**: Estilos predefinidos y personalización completa
- **Procesamiento Asíncrono**: No bloquea la interfaz durante operaciones pesadas
- **Análisis de Pérdidas**: Comparación entre parcelas teóricas vs. reales
- **Logging Detallado**: Seguimiento completo del proceso
- **Configuraciones Persistentes**: Guarda y carga configuraciones

### 📁 **Estructura de Archivos de Salida**
```
output_directory/
├── results/
│   ├── YYYYMMDD_CODIGO_PARCELAS_FINALES.gpkg
│   └── YYYYMMDD_CODIGO_PARCELAS_FINALES_ordenada.gpkg
├── logs/
│   └── pipeline_TIMESTAMP.log
├── summary/
│   └── execution_summary.json
└── config/
    └── YYYYMMDD_CODIGO_pipeline_config_executed.json
```

---

## 🛠️ **Estructura del Proyecto**

```
proyecto_parcelas/
├── main.py                    # 🚀 Punto de entrada de la aplicación
├── requirements.txt           # 📦 Dependencias de Python
├── README.md                  # 📖 Este archivo
├── help.md                    # ❓ Manual de usuario detallado
├── gui_settings.json          # ⚙️ Configuración persistente de la GUI
├── GEODATABASE_SUPPORT.md     # 🏛️ Documentación técnica de .gdb
└── src/
    ├── config/                # ⚙️ Configuraciones del pipeline
    │   ├── config_base.py     # Estructura base de configuración
    │   └── estilos.py         # Estilos predefinidos (calibration, control, custom)
    ├── core/
    │   └── pipeline.py        # 🔄 Orquestador principal del procesamiento
    ├── io/
    │   ├── lectura.py         # 📂 Lectura de archivos geoespaciales
    │   └── rutas.py           # 🗂️ Gestión de rutas
    ├── pipeline/              # 🔧 Módulos de procesamiento
    │   ├── analisis.py        # 📊 Análisis de pérdidas
    │   ├── calculo_parcelas.py # 🧮 Cálculo de cantidad de parcelas
    │   ├── exclusiones.py     # 🚫 Aplicación de exclusiones
    │   ├── filtros.py         # 🔍 Filtros y gridcode
    │   └── generacion_parcelas.py # 🎯 Generación de parcelas
    ├── ui/                    # 🖥️ Interfaz gráfica
    │   ├── app.py             # Ventana principal
    │   ├── dialogs/           # Diálogos especializados
    │   └── tab/               # Pestañas de la interfaz
    ├── utils/                 # 🛠️ Utilidades
    │   ├── dialog_utils.py    # 🗂️ Diálogos mejorados con soporte .gdb
    │   ├── geo_utils.py       # 🌍 Utilidades geoespaciales
    │   ├── gpkg_helpers.py    # 📦 Ayudantes para GeoPackage
    │   └── settings.py        # ⚙️ Configuración persistente
    └── run_pipeline.py        # ▶️ Ejecutor del pipeline
```

---

## 🆘 **Solución de Problemas**

### ❌ **Errores Comunes y Soluciones**

#### **"Python no se reconoce como comando"**
- **Solución**: Reinstala Python marcando "Add Python to PATH"
- **Windows**: Busca "Variables de entorno" y añade Python manualmente

#### **"pip no se reconoce como comando"**
- **Solución**: Usa `python -m pip` en lugar de `pip`

#### **"No module named 'PyQt6'"**
- **Solución**: Activa el entorno virtual y ejecuta `pip install -r requirements.txt`

#### **"Cannot open .gdb file"**
- **Causa**: Geodatabase corrupta o incompatible
- **Solución**: Verifica el archivo con software GIS o usa `ogrinfo`

#### **"No quedan registros después de filtrar"**
- **Causa**: Filtros muy restrictivos
- **Solución**: Revisa configuración de tipos de uso de suelo

#### **La aplicación se cierra inesperadamente**
- **Solución**: Ejecuta desde terminal para ver mensajes de error
- **Windows**: `cmd` → navegar a carpeta → `python main.py`

### 🔍 **Diagnóstico Avanzado**
1. **Activa modo DEBUG**: En la aplicación, ve a Configuration → Log Level → DEBUG
2. **Revisa logs detallados**: Los errores aparecerán en el área de logs
3. **Exporta configuración**: Guarda tu configuración para análisis

---

## 📞 **Soporte y Recursos**

### 📖 **Documentación**
- **Manual de Usuario**: Abre la aplicación → Tab "Help"
- **Documentación Técnica**: `GEODATABASE_SUPPORT.md`
- **Ejemplos de Configuración**: Carpeta `src/json_config/`

### 🛠️ **Para Desarrolladores**
- **Python**: 3.8+ requerido, 3.11+ recomendado
- **IDE Recomendado**: VS Code con extensiones de Python
- **Testing**: Ejecuta `python -m pytest` (si tienes tests)

### 🌐 **Recursos Externos**
- **GDAL/OGR**: [gdal.org](https://gdal.org) - Para soporte avanzado de formatos
- **GeoPandas**: [geopandas.org](https://geopandas.org) - Documentación de análisis geoespacial
- **PyQt6**: [doc.qt.io](https://doc.qt.io/qtforpython/) - Documentación de la interfaz

---

## 📝 **Registro de Cambios**

### **v1.1** (Diciembre 2024) - **ACTUAL**
- ✅ **Soporte completo para Geodatabases (.gdb)**
- ✅ Selección asistida de archivos geoespaciales
- ✅ Validación automática de geodatabases
- ✅ Controles de ejecución centralizados
- ✅ Conservación de archivos de configuración temporal
- ✅ Mejoras en manejo de procesos y threading
- ✅ Documentación expandida para usuarios no técnicos

### **v1.0** (Noviembre 2024)
- ✅ Versión inicial con funcionalidad completa
- ✅ Soporte para GeoPackage y Shapefile
- ✅ Pipeline configurable con múltiples estilos
- ✅ Interfaz gráfica moderna con PyQt6

---

## 📄 **Licencia y Créditos**

**Desarrollado para**: Proyectos de ingeniería forestal y geomensura  
**Tecnologías**: Python, PyQt6, GeoPandas, GDAL/OGR  
**Versión**: Enhanced v1.1  
**Última actualización**: Diciembre 2024

---

## 🚀 **¡Comienza Ahora!**

1. **Instala Python** siguiendo los pasos de arriba
2. **Descarga** el proyecto
3. **Ejecuta** `pip install -r requirements.txt`
4. **Lanza** la aplicación con `python main.py`
5. **Explora** el tab "Help" dentro de la aplicación para tutoriales detallados

**¡Disfruta generando parcelas geoespaciales de manera profesional!** 🌍✨ 