---

# Generador de Parcelas Geoespaciales

## 1. Descripción General

Este proyecto es una aplicación de escritorio desarrollada en Python con una interfaz gráfica de usuario (GUI) construida con PyQt6. Su objetivo principal es automatizar el proceso de generación de parcelas geoespaciales (puntos o polígonos) dentro de rodales o áreas de interés, aplicando una serie de filtros, exclusiones y configuraciones personalizadas. Está especialmente diseñado para flujos de trabajo en el ámbito de la ingeniería geomensura, forestal y GIS, permitiendo la creación de esquemas de muestreo o inventario.

La aplicación implementa un pipeline de procesamiento geoespacial modular y configurable, utilizando librerías como Geopandas, Shapely, Fiona y Pyogrio para la manipulación de datos vectoriales.

## 2. Características Principales

* **Interfaz Gráfica de Usuario (GUI) Intuitiva:** Facilita la configuración de los parámetros del pipeline, la selección de archivos y la ejecución de los procesos.
* **Pipeline de Procesamiento Geoespacial Configurable:** Permite definir paso a paso cómo se generan las parcelas, desde los datos de entrada hasta los productos finales.
* **Soporte para Diferentes Estilos de Generación:** Incluye configuraciones predefinidas para "Calibración", "Control" y un modo "Personalizado" (Custom) que ofrece máxima flexibilidad.
* **Manejo de Capas de Exclusión:** Permite restar áreas de las zonas de interés antes de la generación de parcelas (e.g., caminos, ríos, áreas protegidas).
* **Integración con Datos de Plan Operativo (PO):** Capacidad para cruzar las parcelas generadas con información de un Plan Operativo para enriquecer sus atributos.
* **Generación de Reportes y Análisis:** Incluye un análisis de pérdidas para comparar parcelas teóricas vs. reales.
* **Registro Detallado de Eventos (Logging):** Muestra mensajes del proceso en la GUI y puede guardarlos en archivos para depuración y seguimiento.
* **Procesamiento Asíncrono:** El pipeline principal se ejecuta en un proceso separado para no bloquear la interfaz de usuario.

## 3. Estructura del Proyecto

El proyecto está organizado de la siguiente manera:

```text
proyecto_parcelas/
├── gui_settings.json         # Guarda la configuración de la GUI entre sesiones
├── main.py                   # Punto de entrada de la aplicación, lanza la GUI
├── README.md                 # Este archivo
├── requirements.txt          # Dependencias de Python del proyecto
└── src/
    ├── __init__.py
    ├── config/                 # Módulos para la configuración del pipeline
    │   ├── config_base.py    # Definición base de la configuración del pipeline (dataclasses)
    │   ├── estilos.py        # Configuraciones predefinidas (Calibración, Control, Custom)
    │   └── __init__.py
    ├── core/                   # Lógica central del pipeline
    │   ├── pipeline.py       # Orquestador principal del flujo de procesamiento
    │   └── __init__.py
    ├── io/                     # Módulos para entrada/salida de datos
    │   ├── lectura.py        # Funciones para leer capas geoespaciales
    │   ├── rutas.py          # Gestión de rutas de archivos del proyecto
    │   └── __init__.py
    ├── json_config/            # Archivos JSON de ejemplo para configuraciones del pipeline
    │   ├── test_calibration.json
    │   ├── test_control.json
    │   └── test_custom.json
    ├── pipeline/               # Módulos para cada etapa específica del pipeline
    │   ├── analisis.py       # Análisis de pérdidas de parcelas
    │   ├── atributos_po.py   # Asignación de atributos del Plan Operativo
    │   ├── calculo_parcelas.py # Cálculo de la cantidad de parcelas
    │   ├── exclusiones.py      # Aplicación de exclusiones geométricas
    │   ├── filtros.py        # Filtros iniciales y cálculo de 'gridcode'
    │   ├── generacion_parcelas.py # Generación de puntos/polígonos de parcelas
    │   └── __init__.py
    ├── run_pipeline.py         # Script ejecutable para correr el pipeline (usado por QProcess)
    ├── ui/                     # Módulos de la Interfaz Gráfica de Usuario (PyQt6)
    │   ├── app.py            # Ventana principal de la aplicación y lógica de la GUI
    │   ├── __init__.py
    │   └── tab/                # Widgets para las diferentes pestañas de la GUI
    │       ├── config_tab.py
    │       ├── exclusion_tab.py
    │       ├── pipeline_tab.py
    │       ├── po_tab.py
    │       └── __init__.py
    └── utils/                  # Módulos con funciones de utilidad
        ├── geo_utils.py      # Utilidades geoespaciales (CRS, reparación de geometrías)
        ├── gpkg_helpers.py   # Ayudantes para trabajar con GPKG/FileGDB (listar capas, campos)
        ├── logging_utils.py  # Configuración del sistema de logging
        ├── settings.py       # Carga y guardado de la configuración de la GUI
        └── __init__.py
```

### 3.1. Descripción de Scripts y Módulos

#### Raíz del Proyecto

* **`main.py`**
    * Punto de entrada principal de la aplicación.
    * Lanza la interfaz gráfica de usuario (GUI) de PyQt6, inicializando la ventana principal y gestionando el ciclo de vida de la aplicación.
* **`gui_settings.json`**
    * Archivo de configuración persistente de la GUI.
    * Guarda el estado de la interfaz (últimos archivos usados, parámetros, etc.) entre sesiones.
* **`requirements.txt`**
    * Lista de dependencias de Python necesarias para ejecutar el proyecto.

#### `src/`

* **`src/config/`**
    * **`config_base.py`**: Define la estructura base de la configuración del pipeline usando `dataclasses`. Especifica todos los parámetros posibles que pueden ser usados en el pipeline.
    * **`estilos.py`**: Contiene configuraciones predefinidas para distintos estilos de generación de parcelas (Calibración, Control, Custom). Cada estilo es una instancia de la configuración base con valores adaptados a un caso de uso.
* **`src/core/`**
    * **`pipeline.py`**: Orquestador principal del flujo de procesamiento geoespacial. Implementa la función `run_parcel_generation_pipeline`, que ejecuta secuencialmente todos los pasos del pipeline: lectura de datos, aplicación de filtros, exclusiones, generación de parcelas, análisis de pérdidas, etc.
* **`src/io/`**
    * **`lectura.py`**: Funciones para leer capas geoespaciales desde archivos. Incluye utilidades para cargar datos vectoriales y validar su estructura.
    * **`rutas.py`**: Gestión de rutas de archivos y directorios del proyecto. Centraliza la lógica para construir rutas de entrada/salida y nombres de archivos.
* **`src/json_config/`**
    * **`test_calibration.json`**, **`test_control.json`**, **`test_custom.json`**: Ejemplos de archivos de configuración JSON para distintos estilos de pipeline. Útiles para pruebas y como referencia de la estructura esperada.
* **`src/pipeline/`**
    * **`analisis.py`**: Módulo para el análisis de pérdidas de parcelas. Compara el número de parcelas teóricas y reales, generando reportes de eficiencia.
    * **`atributos_po.py`**: Asigna atributos del Plan Operativo a las parcelas generadas mediante uniones espaciales.
    * **`calculo_parcelas.py`**: Calcula la cantidad de parcelas a generar en cada rodal o área de interés.
    * **`exclusiones.py`**: Aplica exclusiones geométricas (e.g., caminos, ríos) a las áreas de interés antes de la generación de parcelas.
    * **`filtros.py`**: Aplica filtros iniciales a los datos de entrada, como área mínima o valores específicos de atributos.
    * **`generacion_parcelas.py`**: Genera las geometrías de las parcelas (puntos o polígonos) dentro de los rodales o áreas de interés.
* **`src/ui/`**
    * **`app.py`**: Ventana principal de la aplicación y lógica de la GUI. Gestiona la interacción entre las pestañas, la configuración, la ejecución del pipeline y el registro de logs.
    * **`tab/`**: Contiene los widgets de cada pestaña de la GUI:
        * `pipeline_tab.py`: Pestaña principal para configurar y ejecutar el pipeline.
        * `po_tab.py`: Pestaña para seleccionar el archivo y campos del Plan Operativo.
        * `exclusion_tab.py`: Pestaña para gestionar capas de exclusión.
        * `config_tab.py`: Pestaña para ajustes avanzados y gestión de configuraciones.
* **`src/utils/`**
    * **`geo_utils.py`**: Utilidades para operaciones geoespaciales generales, como manejo de CRS y reparación de geometrías.
    * **`gpkg_helpers.py`**: Funciones auxiliares para trabajar con archivos GeoPackage y FileGDB: listar capas y campos.
    * **`logging_utils.py`**: Configuración y utilidades para el sistema de logging del proyecto.
    * **`settings.py`**: Carga y guardado de la configuración de la GUI en `gui_settings.json`.
* **`src/run_pipeline.py`**
    * _Script ejecutable para correr el pipeline de generación de parcelas._
    * Recibe como argumento un archivo de configuración JSON, inicializa el pipeline y ejecuta todos los pasos definidos en `src/core/pipeline.py`. Es el punto de entrada cuando el pipeline se ejecuta desde la GUI o desde la línea de comandos.

## 4. Prerrequisitos

* Python (se recomienda 3.8 o superior).
* **GDAL:** Es una dependencia fundamental para `fiona` y `geopandas`. Debe estar instalada correctamente en el sistema y, preferiblemente, su ruta añadida a la variable de entorno `PATH`. La instalación puede variar según el sistema operativo.
    * En Windows, considera los instaladores de OSGeo4W o los wheels de Christoph Gohlke.
    * En Linux, usualmente se puede instalar mediante el gestor de paquetes (`sudo apt-get install gdal-bin libgdal-dev`).
    * En macOS, `brew install gdal`.

## 5. Instalación

1.  **Clonar el Repositorio (si aplica):**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd proyecto_parcelas
    ```

2.  **Crear un Entorno Virtual:**
    ```bash
    python -m venv venv
    ```

3.  **Activar el Entorno Virtual:**
    * Linux/macOS:
        ```bash
        source venv/bin/activate
        ```
    * Windows (cmd/powershell):
        ```bash
        venv\Scripts\activate
        ```

4.  **Instalar Dependencias:**
    Asegúrate de tener GDAL correctamente instalado antes de este paso.
    ```bash
    pip install -r requirements.txt
    ```

## 6. Uso

### 6.1. Ejecutar la Aplicación

Para iniciar la interfaz gráfica de usuario:

```bash
python main.py
```

### 6.2. Interfaz Gráfica de Usuario (GUI)

La GUI está organizada en varias pestañas para facilitar la configuración del proceso:

* **Pestaña Principal (Pipeline):**
    * Define los directorios de entrada y salida.
    * Selecciona la capa de rodales (o unidades base de trabajo).
    * Especifica el campo identificador de los rodales.
    * Configura los parámetros básicos de las parcelas (tipo, tamaño, espaciamiento).
* **Pestaña Plan Operativo (PO):**
    * Configura la capa del Plan Operativo (opcional).
    * Selecciona los campos del PO que se transferirán a las parcelas.
* **Pestaña Exclusiones:**
    * Añade y gestiona capas vectoriales de exclusión (e.g., caminos, ríos).
    * Define un buffer opcional para cada capa de exclusión.
* **Pestaña Configuración:**
    * Permite ajustes más detallados del pipeline.
    * Selecciona el Estilo de Configuración (Calibracion, Control, Custom).
    * Modifica parámetros específicos como tolerancias, criterios de filtrado, etc., especialmente cuando se usa el estilo "Custom".
* **Consola de Logs:**
    * Un área de texto en la parte inferior de la ventana muestra mensajes en tiempo real del sistema de logging, informando sobre el progreso, advertencias o errores.

### 6.3. Ejecución del Pipeline

1.  **Configuración:** Navega por las pestañas y completa todos los campos requeridos según tus datos y el tipo de análisis deseado.
2.  **Inicio:** Haz clic en el botón "Ejecutar Pipeline" (o el nombre que tenga asignado).
3.  **Proceso:** La aplicación generará un archivo JSON con la configuración actual y la pasará al script `src/run_pipeline.py`. Este script se ejecuta en un proceso separado (`QProcess`) para evitar que la GUI se congele durante operaciones geoespaciales intensivas. El progreso se reflejará en la consola de logs.
4.  **Resultados:** Una vez finalizado, los archivos generados (capas de parcelas, reportes) se encontrarán en el directorio de salida especificado.

## 7. Configuración del Pipeline

La configuración del pipeline es flexible y se maneja a través de varios mecanismos:

* **`gui_settings.json`:**
    * Este archivo (ubicado en la raíz del proyecto) almacena el estado de la interfaz gráfica (últimas rutas de archivo seleccionadas, valores de campos de entrada) para persistencia entre sesiones. Se carga al iniciar la aplicación y se guarda al cerrarla o al modificar ciertos parámetros.
* **Estilos de Configuración (`src/config/estilos.py` y `src/config/config_base.py`):**
    * `config_base.py` define la estructura de la configuración del pipeline usando `dataclasses` (`PipelineConfig`). Contiene todos los posibles parámetros que controlan el flujo de trabajo.
    * `estilos.py` define instancias específicas de `PipelineConfig` para diferentes escenarios:
        * `CALIBRACION_CFG`: Configuración optimizada para parcelas de calibración.
        * `CONTROL_CFG`: Configuración para parcelas de control.
        * `CUSTOM_CFG`: Configuración base que puede ser ampliamente modificada desde la GUI o un archivo JSON.
    * Al seleccionar un estilo en la "Pestaña Configuración" de la GUI, se cargan estos valores predefinidos, que luego pueden ser ajustados si el estilo es "Custom" o si se modifican campos específicos.
* **Archivos JSON de Configuración (`src/json_config/`):**
    * Estos archivos (`test_calibration.json`, `test_control.json`, `test_custom.json`) son ejemplos de cómo se puede estructurar una configuración completa del pipeline en formato JSON.
    * Principalmente, sirven como referencia o para pruebas si se desea ejecutar `src/run_pipeline.py` directamente desde la línea de comandos (pasando la ruta al JSON como argumento).
    * La GUI internamente construye un diccionario con una estructura similar a estos JSON, que luego se pasa al proceso del pipeline.
* **Parámetros Clave (Configurables vía GUI o JSON):**
    * Rutas: `INPUT_DIR`, `OUTPUT_DIR`, `CAPA_RODALES_PATH`.
    * Identificadores: `CAMPO_RODAL_ID`, `NOMBRE_OUTPUT`.
    * Parcelas: `TIPO_PARCELA` (e.g., "Circular", "Rectangular"), `RADIO_PARCELA` o `ANCHO_PARCELA`/`LARGO_PARCELA`, `DISTANCIA_ENTRE_PARCELAS`, `DISTANCIA_ENTRE_LINEAS_PARCELAS`, `ORIENTACION`.
    * Plan Operativo: `PO_PATH`, `PO_FIELDS_TO_JOIN`, `PO_ID_FIELD`.
    * Exclusiones: Lista de capas de exclusión con sus respectivos buffers.
    * Filtros: `MIN_AREA_HA_RODALES`, `GRIDCODE_VALUES_TO_PROCESS`.
    * Y muchos otros parámetros detallados en `PipelineConfig`.

## 8. Flujo de Trabajo del Pipeline (`src/core/pipeline.py`)

El corazón del procesamiento reside en `src/core/pipeline.py`, orquestado por la función `run_parcel_generation_pipeline`. Cuando se ejecuta el pipeline (ya sea desde la GUI o directamente), ocurren los siguientes pasos principales:

1.  **Inicialización:**
    * El script `src/run_pipeline.py` recibe la configuración (generalmente como una ruta a un archivo JSON temporal creado por la GUI o un JSON de `src/json_config/`).
    * Se parsea la configuración y se instancian los objetos `PipelineConfig`, `RunConfiguration` (que incluye `PipelineConfig` y parámetros de ejecución como rutas) y `ProjectPaths` (para gestionar las rutas de salida).
    * Se configura el logging.

2.  **Ejecución Secuencial de Módulos:**
    La función `run_parcel_generation_pipeline` llama a una serie de funciones, cada una correspondiente a un módulo en `src/pipeline/`:
    * **Lectura de Datos (`src/io/lectura.py` -> `read_input_layer`):**
        * Carga la capa de rodales y otras capas de entrada necesarias.
        * Realiza validaciones iniciales (e.g., CRS).
    * **Filtros Iniciales (`src/pipeline/filtros.py` -> `Filtros` clase):**
        * Aplica filtros a los rodales, por ejemplo, por área mínima (`MIN_AREA_HA_RODALES`) o valores específicos de un campo (`GRIDCODE_VALUES_TO_PROCESS`).
        * Prepara los rodales para los siguientes pasos.
    * **Exclusiones (`src/pipeline/exclusiones.py` -> `Exclusiones` clase):**
        * Para cada capa de exclusión definida, aplica un buffer si se especificó.
        * Realiza una operación de diferencia espacial para sustraer estas áreas de exclusión de los rodales filtrados.
    * **Cálculo de Cantidad de Parcelas (`src/pipeline/calculo_parcelas.py` -> `CalculoParcelas` clase):**
        * Basándose en el área útil de los rodales (después de exclusiones) y los parámetros de densidad de parcelas (distancia entre parcelas y líneas), determina cuántas parcelas teóricas deben generarse por rodal.
    * **Generación de Geometrías de Parcelas (`src/pipeline/generacion_parcelas.py` -> `GeneracionParcelas` clase):**
        * Crea las geometrías de las parcelas (puntos o polígonos) dentro de los rodales procesados.
        * Implementa la lógica para distribuir las parcelas según la configuración (e.g., en grilla, con cierta orientación).
        * Asegura que las parcelas caigan completamente dentro de los límites del rodal útil.
    * **Asignación de Atributos del Plan Operativo (`src/pipeline/atributos_po.py` -> `AtributosPO` clase):**
        * Si se proporcionó una capa de Plan Operativo, realiza una unión espacial (spatial join) entre las parcelas generadas y la capa del PO.
        * Transfiere los campos seleccionados del PO a la tabla de atributos de las parcelas.
    * **Análisis de Pérdidas (`src/pipeline/analisis.py` -> `AnalisisPerdidas` clase):**
        * Compara el número de parcelas teóricas calculadas con el número de parcelas finales generadas.
        * Genera un reporte (e.g., archivo CSV o Excel) que detalla las pérdidas y sus posibles causas por rodal.

3.  **Salida de Resultados:**
    * Todas las capas intermedias (opcionalmente) y las capas finales (parcelas, rodales procesados) se guardan en el directorio de salida especificado, generalmente en formato GeoPackage (`.gpkg`).
    * Los reportes de análisis también se guardan en este directorio.

## 9. Desarrollo y Contribución

### 9.1. Convenciones de Código

* **Estilo:** Seguir las recomendaciones de PEP 8 para el código Python.
* **Idioma:**
    * Nombres de variables, funciones, clases, módulos y parámetros: Inglés.
    * Docstrings: Inglés. Deben ser descriptivos y explicar el propósito, argumentos y lo que retorna la función/clase.
    * Comentarios en el código: Inglés, concisos y solo cuando sea necesario para clarificar lógica compleja.
* **Tipado Estático:** Utilizar type hints de Python siempre que sea posible para mejorar la legibilidad y mantenibilidad.

### 9.2. Logging

* El sistema de logging está centralizado y configurado en `src/utils/logging_utils.py`.
* Utiliza el módulo estándar `logging` de Python.
* En cada módulo, obtener una instancia del logger con: `logger = logging.getLogger(__name__)`.
* Los logs se emiten a la consola de la GUI y también se pueden configurar para guardarse en un archivo.
* Niveles de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) deben usarse apropiadamente.

### 9.3. Añadir un Nuevo Paso al Pipeline

1.  **Crear el Módulo:**
    * Crea un nuevo archivo Python en `src/pipeline/nombre_del_nuevo_paso.py`.
    * Define la lógica principal en una función o clase dentro de este módulo. Por ejemplo:
        ```python
        # src/pipeline/nombre_del_nuevo_paso.py
        import logging
        import geopandas as gpd
        # from src.config.config_base import PipelineConfig # Si necesitas acceso a la config
        # from src.io.rutas import ProjectPaths # Si necesitas acceso a las rutas

        logger = logging.getLogger(__name__)

        def process_new_step(input_gdf: gpd.GeoDataFrame, param1: str, param2: int) -> gpd.GeoDataFrame:
            """
            Docstring for the new step.
            """
            logger.info(f"Executing new step with param1: {param1}, param2: {param2}")
            # ... a lot of new logic here ...
            processed_gdf = input_gdf.copy() # Placeholder
            return processed_gdf
        ```

2.  **Integrar en `src/core/pipeline.py`:**
    * Importa tu nueva función/clase en `src/core/pipeline.py`.
    * Incorpórala en la secuencia de ejecución dentro de `run_parcel_generation_pipeline`, pasando los datos necesarios (generalmente GeoDataFrames resultantes del paso anterior) y los parámetros de configuración.
    * Asegúrate de manejar las entradas y salidas de datos correctamente.

3.  **Actualizar Configuración (si es necesario):**
    * Si tu nuevo paso requiere nuevos parámetros configurables por el usuario:
        * Añade los nuevos campos a la `dataclass PipelineConfig` en `src/config/config_base.py`.
        * Actualiza las configuraciones de ejemplo en `src/config/estilos.py` (`CALIBRACION_CFG`, `CONTROL_CFG`, `CUSTOM_CFG`) con valores por defecto para los nuevos parámetros.
        * Actualiza los archivos JSON de ejemplo en `src/json_config/`.

4.  **Actualizar GUI (si es necesario):**
    * Si se añadieron nuevos parámetros configurables, modifica la pestaña correspondiente en `src/ui/tab/` para incluir nuevos widgets (QLineEdit, QComboBox, etc.) que permitan al usuario ingresar estos valores.
    * Asegúrate de que estos nuevos valores se lean correctamente y se incluyan en la configuración que se pasa al pipeline.
    * Esto implicará modificar la lógica en `src/ui/app.py` para recolectar estos nuevos parámetros y en la pestaña específica (e.g., `src/ui/tab/config_tab.py`) para crear los widgets.

### 9.4. Modificar la Interfaz Gráfica

* Los archivos de la GUI residen en `src/ui/` (lógica principal de la app) y `src/ui/tab/` (componentes de cada pestaña).
* La interfaz está construida mediante código PyQt6 (no se usan archivos `.ui` de Qt Designer directamente en el repositorio actual).
* Para añadir o modificar elementos:
    1.  Identifica la clase del widget de la pestaña o ventana que necesitas cambiar.
    2.  Añade nuevos widgets de PyQt6 (botones, campos de texto, etc.) en el método `__init__` o en un método de configuración de la UI de esa clase.
    3.  Conecta las señales de los nuevos widgets (e.g., `clicked`, `textChanged`) a los slots (métodos) apropiados para manejar la interacción del usuario.
    4.  Actualiza los métodos que cargan y guardan la configuración de la GUI (`load_settings_to_gui`, `get_settings_from_gui` en `src/ui/app.py` o métodos equivalentes en las pestañas) para incluir los nuevos campos.

## 10. Dependencias Clave

El archivo `requirements.txt` lista las dependencias principales:

* **PyQt6:** Framework para la interfaz gráfica de usuario.
* **geopandas:** Para trabajar con datos geoespaciales de manera similar a pandas, facilitando operaciones vectoriales.
* **pandas:** Para la manipulación y análisis de datos tabulares (atributos de las capas GIS).
* **numpy:** Para operaciones numéricas eficientes, es una dependencia central de pandas y geopandas.
* **shapely:** Para la manipulación y análisis de geometrías planas.
* **pyogrio:** Para lectura y escritura eficiente de formatos de archivo vectoriales. Geopandas puede usarlo como motor.
* **fiona:** Otra librería para leer y escribir formatos de archivo vectoriales. También es una dependencia de Geopandas y se usa directamente para ciertas operaciones como listar capas/campos.
* **matplotlib:** Usado por Geopandas para funcionalidades de ploteo (`.plot()`), aunque no se use directamente para crear gráficos en la GUI de esta aplicación, es una dependencia común en el ecosistema GeoPandas.

## 11. Solución de Problemas Comunes

* **Errores de GDAL/Fiona/Geopandas en la instalación o ejecución:**
    * *Causa Común:* GDAL no está instalado correctamente en el sistema o no es encontrado por las librerías de Python.
    * *Solución:*
        * Asegúrate de que GDAL esté instalado (ver sección "Prerrequisitos").
        * Verifica que la versión de GDAL sea compatible con las versiones de `fiona` y `geopandas` que estás instalando. A veces, instalar desde `conda-forge` (si usas Conda) maneja mejor estas complejas dependencias.
        * En Windows, asegúrate de que las variables de entorno de GDAL (como `GDAL_DATA`) estén configuradas si es necesario, o que los DLLs de GDAL estén en el `PATH`.
* **Permisos de Escritura:**
    * *Problema:* La aplicación no puede guardar archivos en el directorio de salida.
    * *Solución:* Verifica que tengas permisos de escritura en la ubicación seleccionada para la salida. Ejecuta la aplicación con los permisos adecuados si es necesario (aunque esto generalmente no debería ser requerido para directorios de usuario).
* **CRS (Sistema de Referencia de Coordenadas) Incorrecto o Mixto:**
    * *Problema:* Operaciones geoespaciales fallan o producen resultados incorrectos.
    * *Solución:* Asegúrate de que todas tus capas de entrada estén en el mismo CRS proyectado o que la aplicación maneje las transformaciones de CRS adecuadamente (ver `src/utils/geo_utils.py`). El proyecto parece tener funciones para verificar y uniformizar CRS.

## 12. Futuras Mejoras (Roadmap Potencial)

* Soporte para más formatos de entrada/salida: Además de GPKG y Shapefiles (implícito por Fiona/Pyogrio), explorar otros como PostGIS.
* Paralelización: Investigar la paralelización de tareas intensivas dentro del pipeline (e.g., procesamiento por rodal en paralelo) para mejorar el rendimiento en grandes datasets.
* Mejoras en Visualización: Integrar una vista previa de mapas simple dentro de la GUI para visualizar las capas de entrada o los resultados.
* Validación de Datos más Robusta: Expandir las validaciones de los datos de entrada.
* Interfaz de Línea de Comandos (CLI) Avanzada: Mejorar `run_pipeline.py` para que sea más flexible si se usa independientemente de la GUI.
* Empaquetado de la Aplicación: Crear un ejecutable standalone (e.g., usando PyInstaller o cx_Freeze) para facilitar la distribución a usuarios sin un entorno Python.
* Pruebas Unitarias y de Integración: Desarrollar un conjunto de pruebas para asegurar la estabilidad y correctitud del código a medida que evoluciona.

---