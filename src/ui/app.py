"""
Main window for the Parcel Generator application using PyQt6.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QTextEdit, QMessageBox,
    QListWidget, QListWidgetItem, QInputDialog, QTabWidget
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment # Import QProcessEnvironment
from src.utils.settings import load_gui_settings, save_gui_settings
from src.utils.gpkg_helpers import list_layers, list_fields
from src.core.pipeline import ejecutar_proceso # Esta importación es para la lógica interna si la hubiera, no para QProcess
import os
import sys # <--- AÑADIDO IMPORT SYS
import json
import tempfile
from typing import Optional
from src.ui.tab.pipeline_tab import PipelineTab
from src.ui.tab.po_tab import POTab
from src.ui.tab.exclusion_tab import ExclusionTab
from src.ui.tab.config_tab import ConfigTab

print("[DEBUG] INICIO ui/app.py")

class ParcelGeneratorApp(QMainWindow):
    """
    Main application window for the Parcel Generator.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Parcel Generator")
        self.setMinimumSize(900, 650)
        self.settings = load_gui_settings()
        self.po_layer = None
        self.po_fields = []
        self.exclusion_list = self.settings.get("exclusion_list", [])
        self.process = None
        self._imported_config_path = None  # Ruta del último JSON importado
        self._imported_config_hash = None  # Hash del contenido importado
        self._last_gui_hash = None         # Hash del último estado de la GUI
        self._last_temp_config_path = None  # Ruta del último archivo temporal generado
        self._current_log_level = "INFO"
        self._init_ui()
        self._restore_gui_settings()

    def _init_ui(self) -> None:
        """
        Initializes the main UI layout.
        """
        central_widget = QWidget()
        tabs = QTabWidget()
        self.pipeline_tab = PipelineTab()
        self.po_tab = POTab()
        self.exclusion_tab = ExclusionTab()
        self.config_tab = ConfigTab()
        tabs.addTab(self.pipeline_tab, "Pipeline")
        tabs.addTab(self.po_tab, "Plan Operative (PO)")
        tabs.addTab(self.exclusion_tab, "Exclusion Layers")
        tabs.addTab(self.config_tab, "Configuration")
        layout = QVBoxLayout()
        layout.addWidget(tabs)
        # --- Log transversal ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Log and messages will appear here...")
        layout.addWidget(self.log_text)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --- Conexión de señales y eventos entre tabs y lógica global ---
        # Pipeline: Run/Stop/Browse
        self.pipeline_tab.run_btn.clicked.connect(self._on_run_clicked)
        self.pipeline_tab.stop_btn.clicked.connect(self._on_stop_clicked)
        self.pipeline_tab.input_line.textChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.output_line.textChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.style_combo.currentTextChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.intensity_spin.valueChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.min_parcels_spin.valueChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.max_parcels_spin.valueChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.min_area_spin.valueChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.buffer_spin.valueChanged.connect(self._on_any_field_changed)
        self.pipeline_tab.min_distance_spin.valueChanged.connect(self._on_any_field_changed)
        # Browse buttons
        self.pipeline_tab.input_line.setPlaceholderText("Input file path...")
        self.pipeline_tab.output_line.setPlaceholderText("Output directory...")
        self.pipeline_tab.input_line.mouseDoubleClickEvent = lambda event: self._select_input_file()
        self.pipeline_tab.output_line.mouseDoubleClickEvent = lambda event: self._select_output_dir()

        # PO tab: campos y browse
        self.po_tab.po_path_line.textChanged.connect(self._on_any_field_changed)
        self.po_tab.po_layer_combo.currentTextChanged.connect(self._on_any_field_changed)
        self.po_tab.po_fields_btn.clicked.connect(self._select_po_fields)
        # Browse PO file
        self.po_tab.po_path_line.mouseDoubleClickEvent = lambda event: self._select_po_file()

        # Exclusiones: agregar/quitar
        self.exclusion_tab.excl_list_widget.model().rowsInserted.connect(self._on_any_field_changed)
        self.exclusion_tab.excl_list_widget.model().rowsRemoved.connect(self._on_any_field_changed)
        # Botones de exclusión
        self.exclusion_tab.findChild(QPushButton, "add_exclusion_btn").clicked.connect(self._add_exclusion)
        self.exclusion_tab.findChild(QPushButton, "remove_exclusion_btn").clicked.connect(self._remove_exclusion)

        # Configuración: export/import/settings
        self.config_tab.findChild(QPushButton, "export_config_btn").clicked.connect(self._export_pipeline_config)
        self.config_tab.findChild(QPushButton, "import_config_btn").clicked.connect(self._import_pipeline_config)
        self.config_tab.findChild(QPushButton, "save_settings_btn").clicked.connect(self._save_gui_settings)
        self.config_tab.findChild(QPushButton, "load_settings_btn").clicked.connect(self._restore_gui_settings)
        self.config_tab.findChild(QComboBox, "log_level_combo").currentTextChanged.connect(self._on_log_level_changed)
        self.config_tab.configChanged.connect(self._on_config_changed)

    # --- PO and Exclusion logic ---
    def _select_po_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PO file", "", "Geo Files (*.shp *.gpkg *.geojson *.gdb);;All Files (*)")
        if file_path:
            self.po_tab.po_path_line.setText(file_path)
            layers = list_layers(file_path)
            self.po_tab.po_layer_combo.clear()
            self.po_tab.po_layer_combo.addItems(layers)
            if layers:
                self.po_tab.po_layer_combo.setCurrentIndex(0)
            self.po_fields = []
            self.po_tab.po_fields_label.setText("")

    def _on_po_layer_changed(self, layer: str) -> None:
        self.po_layer = layer
        self.po_fields = []
        self.po_tab.po_fields_label.setText("")

    def _select_po_fields(self) -> None:
        file_path = self.po_tab.po_path_line.text()
        layer = self.po_tab.po_layer_combo.currentText()
        if not file_path or not layer:
            QMessageBox.warning(self, "PO selection", "Please select a PO file and layer first.")
            return
        fields = list_fields(file_path, layer)
        if not fields:
            QMessageBox.warning(self, "PO selection", "No fields found in the selected layer.")
            return
        selected, ok = QInputDialog.getItem(self, "Select PO fields", "Fields (comma separated):", [", ".join(fields)], 0, True)
        if ok and selected:
            self.po_fields = [f.strip() for f in selected.split(",") if f.strip()]
            self.po_tab.po_fields_label.setText(", ".join(self.po_fields))

    def _add_exclusion(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select exclusion file", "", "Geo Files (*.shp *.gpkg *.geojson *.gdb);;All Files (*)")
        if not file_path:
            return
        layer = None
        if file_path.lower().endswith((".gpkg", ".gdb")):
            layers = list_layers(file_path)
            if not layers:
                QMessageBox.warning(self, "No layers found", f"No layers found in {file_path}")
                return
            if len(layers) == 1:
                layer = layers[0]
            else:
                layer, ok = self._select_layer_dialog(layers)
                if not ok:
                    return
        desc, ok = QInputDialog.getText(self, "Exclusion description", "Description:", text=os.path.basename(file_path))
        if not ok:
            return
        exclusion = {"path": file_path, "layer": layer, "description": desc}
        self.exclusion_list.append(exclusion)
        self._update_exclusion_list()

    def _remove_exclusion(self) -> None:
        selected = self.exclusion_tab.excl_list_widget.currentRow()
        if selected >= 0:
            self.exclusion_list.pop(selected)
            self._update_exclusion_list()

    def _update_exclusion_list(self) -> None:
        self.exclusion_tab.excl_list_widget.clear()
        for excl in self.exclusion_list:
            text = excl.get("description", os.path.basename(excl.get("path", "Unknown")))
            if excl.get("layer"):
                text += f" ({excl['layer']})"
            self.exclusion_tab.excl_list_widget.addItem(QListWidgetItem(text))

    # --- Existing logic ---
    def _select_input_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select input file", "", "Geo Files (*.shp *.gpkg *.geojson);;All Files (*)")
        if file_path:
            self.pipeline_tab.input_line.setText(file_path)
            # Logic for layer selection if gpkg/gdb can remain if needed, or simplified
            # For now, keeping it as is, as it's not directly related to the QProcess issue

    def _select_layer_dialog(self, layers):
        layer, ok = QInputDialog.getItem(self, "Select Layer", "Available layers:", layers, 0, False)
        return layer, ok

    def _select_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select output directory", "")
        if dir_path:
            self.pipeline_tab.output_line.setText(dir_path)

    def _on_style_changed(self, style: str) -> None:
        self._set_advanced_params_visible(style == "custom")

    def _set_advanced_params_visible(self, visible: bool) -> None:
        # This function can remain as is
        self.pipeline_tab.intensity_spin.setVisible(visible)
        self.pipeline_tab.min_parcels_spin.setVisible(visible)
        self.pipeline_tab.max_parcels_spin.setVisible(visible)
        self.pipeline_tab.min_area_spin.setVisible(visible)
        self.pipeline_tab.buffer_spin.setVisible(visible)
        self.pipeline_tab.min_distance_spin.setVisible(visible)

    def _on_run_clicked(self) -> None:
        input_path = self.pipeline_tab.input_line.text().strip()
        output_dir = self.pipeline_tab.output_line.text().strip()
        style = self.pipeline_tab.style_combo.currentText()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Input required", "Please select a valid input file.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Output required", "Please select an output directory.")
            return

        gui_params = self._get_pipeline_params()
        gui_hash = self._hash_dict(gui_params)
        use_imported = False
        config_path_to_use = None
        if self._imported_config_path and self._imported_config_hash == gui_hash:
            use_imported = True
            config_path_to_use = self._imported_config_path
            self.log_text.append(f"[INFO] Using imported config for pipeline: {config_path_to_use}")
            self._last_temp_config_path = None
        else:
            # Genera un nuevo JSON temporal
            json_config_dir = os.path.join(os.path.dirname(__file__), "..", "json_config")
            os.makedirs(json_config_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json", dir=json_config_dir) as tmp:
                json.dump(gui_params, tmp, indent=2)
                config_path_to_use = tmp.name
            self.log_text.append(f"[INFO] Using new generated config for pipeline: {config_path_to_use}")
            self._last_temp_config_path = config_path_to_use

        cfg_overrides = {}
        if style == "custom":
            cfg_overrides = {
                "INTENSITY": self.pipeline_tab.intensity_spin.value(),
                "MIN_PARCELS": self.pipeline_tab.min_parcels_spin.value(),
                "MAX_PARCELS": self.pipeline_tab.max_parcels_spin.value(),
                "MIN_AREA": self.pipeline_tab.min_area_spin.value(),
                "BUFFER_DISTANCE": self.pipeline_tab.buffer_spin.value(),
                "MIN_DISTANCE": self.pipeline_tab.min_distance_spin.value()
            }
        po_config = {
            "ruta": self.po_tab.po_path_line.text(),
            "capa": self.po_tab.po_layer_combo.currentText(),
            "campos": self.po_fields
        } if self.po_tab.po_path_line.text() and self.po_tab.po_layer_combo.currentText() else None
        if po_config:
            cfg_overrides["PO_CONFIG"] = po_config
        if self.exclusion_list:
            cfg_overrides["CAPAS_EXCLUSION"] = self.exclusion_list

        params = {
            "input_path": input_path,
            "output_dir": output_dir,
            "entrega": None,
            "style": style,
            "cfg_overrides": cfg_overrides
        }

        self.pipeline_tab.progress_bar.setValue(0)
        self.log_text.append("[INFO] Starting processing (QProcess)...")
        self.pipeline_tab.run_btn.setEnabled(False)
        self.pipeline_tab.stop_btn.setEnabled(True)
        self.process = QProcess(self)
        self.process.setProgram("python")
        self.process.setArguments(["-m", "src.run_pipeline", config_path_to_use])
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.process.setWorkingDirectory(project_root)
        # Set log level as environment variable
        env = self.process.processEnvironment() or QProcessEnvironment.systemEnvironment()
        env.insert("LOG_LEVEL", self._current_log_level)
        self.process.setProcessEnvironment(env)
        self.process.readyReadStandardOutput.connect(self._on_process_stdout)
        self.process.readyReadStandardError.connect(self._on_process_stderr)
        self.process.finished.connect(self._on_process_finished)
        self.process.start()

    def _on_process_stdout(self):
        data = self.process.readAllStandardOutput().data().decode().strip()
        # self.log_text.append(f"[DEBUG UI STDOUT RAW] '{data}'") # Para depurar la data cruda
        if not data: # Ignorar si está vacío después de strip()
            return

        for line in data.splitlines(): # Procesar cada línea si hay múltiples mensajes JSON
            line = line.strip()
            if not line:
                continue
            
            self.log_text.append(f"[FROM PROCESS STDOUT] {line}") # Mostrar toda la línea para depuración
            try:
                msg = json.loads(line)
                msg_type = msg.get("type", "").lower()

                if msg_type == "progress":
                    value = msg.get("value", 0)
                    status = msg.get("status", "")
                    self.pipeline_tab.progress_bar.setValue(value)
                    self.log_text.append(f"[PROGRESS] {value}% - {status}")
                elif msg_type == "success":
                    self.pipeline_tab.progress_bar.setValue(100)
                    self.log_text.append(f"[SUCCESS] {msg.get('message', 'Processing completed successfully.')}")
                    QMessageBox.information(self, "Process Completed", msg.get('message', "Parcel generation completed successfully."))
                    # self._on_process_finished() No llamar aquí, se llama en el slot 'finished'
                elif msg_type == "error":
                    error_message = msg.get('message', 'An unknown error occurred.')
                    # <--- CAMBIO AQUÍ: obtener 'traceback_lines' y unir
                    traceback_lines_list = msg.get('traceback_lines', []) 
                    traceback_info_formatted = "\n".join(traceback_lines_list)
                    # --- FIN DEL CAMBIO ---
                    full_error_details = f"{error_message}\n\nTraceback (from process):\n{traceback_info_formatted}"
                    self.log_text.append(f"[ERROR FROM PROCESS] {full_error_details}")
                    QMessageBox.critical(self, "Error During Processing", full_error_details)
                elif msg_type == "log":  # Para mensajes de logging genéricos desde el script
                    level = msg.get("level", "info").upper()
                    logger_name = msg.get("logger", "process")
                    log_message = msg.get("message", "")
                    self.log_text.append(f"[{level} - {logger_name}] {log_message}")
                else: # Si no es JSON o tipo desconocido, mostrar como texto plano
                    self.log_text.append(f"[STDOUT UNPARSED] {line}")
            except json.JSONDecodeError:
                # Si la línea no es un JSON válido, simplemente agrégala al log como texto.
                self.log_text.append(f"[STDOUT NON-JSON] {line}")
            except Exception as e:
                self.log_text.append(f"[ERROR PARSING STDOUT] Exception: {str(e)} - Original line: {line}")


    def _on_process_stderr(self):
        # Leer todo lo disponible en stderr para no perder mensajes
        error_data = self.process.readAllStandardError().data().decode().strip()
        if error_data:
            for line in error_data.splitlines():
                line = line.strip()
                if line:
                    self.log_text.append(f"[STDERR FROM PROCESS] {line}")

    def _on_process_finished(self):
        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus() # NormalExit o CrashExit

        self.log_text.append(f"[INFO] Process finished. Exit Code: {exit_code}, Exit Status: {exit_status.name}")
        
        if exit_status == QProcess.ExitStatus.CrashExit:
            self.log_text.append("[ERROR] The process crashed.")
            QMessageBox.warning(self, "Process Crashed", "The processing script crashed unexpectedly.")
        elif exit_code != 0:
             self.log_text.append(f"[WARNING] Process finished with non-zero exit code: {exit_code}.")
             # No mostrar QMessageBox aquí si ya se mostró uno por un error JSON
        
        self.pipeline_tab.run_btn.setEnabled(True)
        self.pipeline_tab.stop_btn.setEnabled(False)
        # Limpieza segura de archivos temporales
        temp_file_to_delete = getattr(self, '_last_temp_config_path', None)
        if temp_file_to_delete and isinstance(temp_file_to_delete, str):
            try:
                if os.path.exists(temp_file_to_delete):
                    os.remove(temp_file_to_delete)
                    self.log_text.append(f"[INFO] Deleted temporary config file: {temp_file_to_delete}")
            except Exception as e:
                self.log_text.append(f"[WARNING] Could not delete temporary config file {temp_file_to_delete}: {e}")
        self._last_temp_config_path = None
        self.process = None

    def _on_stop_clicked(self):
        reply = QMessageBox.question(
            self,
            "Confirm Stop",
            "Are you sure you want to stop the process and all its children?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            self.log_text.append("[INFO] Stopping process and all children...")
            try:
                import psutil
                pid = self.process.processId()
                if pid:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.terminate()
                        except Exception:
                            pass
                    gone, alive = psutil.wait_procs(children, timeout=3)
                    for child in alive:
                        try:
                            child.kill()
                        except Exception:
                            pass
                    parent.terminate()
                    try:
                        parent.wait(timeout=3)
                    except Exception:
                        parent.kill()
                else:
                    self.process.kill()
            except ImportError:
                self.log_text.append("[WARNING] psutil not installed, using QProcess.kill(). For more robust termination, install psutil.")
                self.process.kill()
            except Exception as e:
                self.log_text.append(f"[ERROR] Failed to stop all processes robustly: {str(e)}. Using QProcess.kill().")
                self.process.kill()
            self.process.waitForFinished(3000)
            self.pipeline_tab.run_btn.setEnabled(True)
            self.pipeline_tab.stop_btn.setEnabled(False)
        else:
            self.log_text.append("[WARNING] No process is running.")

    def _sync_tabs_to_attrs(self) -> None:
        """
        Sincroniza los valores de los widgets de los tabs con los atributos internos de la clase.
        """
        # Pipeline tab
        self.input_path = self.pipeline_tab.input_line.text()
        self.output_dir = self.pipeline_tab.output_line.text()
        self.style = self.pipeline_tab.style_combo.currentText()
        self.intensity = self.pipeline_tab.intensity_spin.value()
        self.min_parcels = self.pipeline_tab.min_parcels_spin.value()
        self.max_parcels = self.pipeline_tab.max_parcels_spin.value()
        self.min_area = self.pipeline_tab.min_area_spin.value()
        self.buffer_distance = self.pipeline_tab.buffer_spin.value()
        self.min_distance = self.pipeline_tab.min_distance_spin.value()
        # PO tab
        self.po_path = self.po_tab.po_path_line.text()
        self.po_layer = self.po_tab.po_layer_combo.currentText()
        self.po_fields = [f.strip() for f in self.po_tab.po_fields_label.text().split(",") if f.strip()]
        # Exclusion tab
        # self.exclusion_list = [self.exclusion_tab.excl_list_widget.item(i).text() for i in range(self.exclusion_tab.excl_list_widget.count())]

    def _sync_attrs_to_tabs(self) -> None:
        """
        Sincroniza los atributos internos de la clase con los widgets de los tabs.
        Si alguna ruta no existe, muestra un mensaje en el widget correspondiente.
        Además, log temporal para depuración de PO.
        """
        # Pipeline tab
        self.pipeline_tab.input_line.setText(getattr(self, "input_path", ""))
        self.pipeline_tab.output_line.setText(getattr(self, "output_dir", ""))
        idx = self.pipeline_tab.style_combo.findText(getattr(self, "style", "calibration"))
        if idx >= 0:
            self.pipeline_tab.style_combo.setCurrentIndex(idx)
        self.pipeline_tab.intensity_spin.setValue(getattr(self, "intensity", 50))
        self.pipeline_tab.min_parcels_spin.setValue(getattr(self, "min_parcels", 1))
        self.pipeline_tab.max_parcels_spin.setValue(getattr(self, "max_parcels", 10))
        self.pipeline_tab.min_area_spin.setValue(getattr(self, "min_area", 0.3))
        self.pipeline_tab.buffer_spin.setValue(getattr(self, "buffer_distance", -20))
        self.pipeline_tab.min_distance_spin.setValue(getattr(self, "min_distance", 60.0))
        # PO tab
        po_path = getattr(self, "po_path", "")
        po_layer = getattr(self, "po_layer", "")
        po_fields = getattr(self, "po_fields", [])
        self.log_text.append(f"[DEBUG] PO path exists: {os.path.exists(po_path)}")
        if po_path and not os.path.exists(po_path):
            self.po_tab.po_path_line.setText(f"{po_path} [NOT FOUND - Check path or permissions]")
            self.po_tab.po_layer_combo.clear()
            self.po_tab.po_layer_combo.addItem("INVALID PATH")
            self.po_tab.po_fields_label.setText(", ".join(po_fields))
        elif po_path:
            self.po_tab.po_path_line.setText(po_path)
            try:
                layers = list_layers(po_path)
                self.log_text.append(f"[DEBUG] list_layers: {layers}")
                self.po_tab.po_layer_combo.clear()
                self.po_tab.po_layer_combo.addItems(layers)
                idx_layer = self.po_tab.po_layer_combo.findText(po_layer)
                self.log_text.append(f"[DEBUG] Looking for layer: '{po_layer}' (found idx: {idx_layer})")
                if idx_layer >= 0:
                    self.po_tab.po_layer_combo.setCurrentIndex(idx_layer)
                else:
                    self.po_tab.po_layer_combo.addItem(f"{po_layer} [NOT FOUND]")
                    self.po_tab.po_layer_combo.setCurrentIndex(self.po_tab.po_layer_combo.count()-1)
            except Exception as e:
                self.log_text.append(f"[DEBUG] Exception in list_layers: {e}")
                self.po_tab.po_layer_combo.clear()
                self.po_tab.po_layer_combo.addItem("INVALID PATH")
            self.po_tab.po_fields_label.setText(", ".join(po_fields))
        else:
            self.po_tab.po_path_line.setText("")
            self.po_tab.po_layer_combo.clear()
            self.po_tab.po_fields_label.setText("")
        # Exclusion tab
        self.exclusion_tab.excl_list_widget.clear()
        for excl in getattr(self, "exclusion_list", []):
            if isinstance(excl, dict):
                path = excl.get("path", "")
                desc = excl.get("description", os.path.basename(path) or "Unknown")
                layer = excl.get("layer")
                if path and not os.path.exists(path):
                    text = f"{desc} [NOT FOUND]"
                else:
                    text = desc
                if layer:
                    text += f" ({layer})"
                self.exclusion_tab.excl_list_widget.addItem(text)
            else:
                self.exclusion_tab.excl_list_widget.addItem(str(excl))

    def _get_pipeline_params(self):
        self._sync_tabs_to_attrs()
        input_path = self.input_path.strip()
        output_dir = self.output_dir.strip()
        style = self.style
        cfg_overrides = {}
        if style == "custom":
            cfg_overrides = {
                "INTENSITY": self.intensity,
                "MIN_PARCELS": self.min_parcels,
                "MAX_PARCELS": self.max_parcels,
                "MIN_AREA": self.min_area,
                "BUFFER_DISTANCE": self.buffer_distance,
                "MIN_DISTANCE": self.min_distance
            }
        po_config = {
            "ruta": self.po_path,
            "capa": self.po_layer,
            "campos": self.po_fields
        } if self.po_path and self.po_layer else None
        if po_config:
            cfg_overrides["PO_CONFIG"] = po_config
        if self.exclusion_list:
            cfg_overrides["CAPAS_EXCLUSION"] = self.exclusion_list
        params = {
            "input_path": input_path,
            "output_dir": output_dir,
            "entrega": None,
            "style": style,
            "cfg_overrides": cfg_overrides
        }
        return params

    def _set_pipeline_params(self, params):
        # Carga los valores del dict de pipeline en los atributos y los tabs
        self.input_path = params.get("input_path", "")
        self.output_dir = params.get("output_dir", "")
        self.style = params.get("style", "calibration")
        cfg_overrides = params.get("cfg_overrides", {})
        if self.style == "custom":
            self.intensity = cfg_overrides.get("INTENSITY", 50)
            self.min_parcels = cfg_overrides.get("MIN_PARCELS", 1)
            self.max_parcels = cfg_overrides.get("MAX_PARCELS", 10)
            self.min_area = cfg_overrides.get("MIN_AREA", 0.3)
            self.buffer_distance = cfg_overrides.get("BUFFER_DISTANCE", -20)
            self.min_distance = cfg_overrides.get("MIN_DISTANCE", 60.0)
        po_conf = cfg_overrides.get("PO_CONFIG", {})
        self.po_path = po_conf.get("ruta", "")
        self.po_layer = po_conf.get("capa", "")
        self.po_fields = po_conf.get("campos", [])
        self.exclusion_list = cfg_overrides.get("CAPAS_EXCLUSION", [])
        # Log temporal para depuración
        self.log_text.append(f"[DEBUG] PO path: {self.po_path}")
        self.log_text.append(f"[DEBUG] PO layer: {self.po_layer}")
        self.log_text.append(f"[DEBUG] PO fields: {self.po_fields}")
        self._sync_attrs_to_tabs()

    def _save_gui_settings(self) -> None:
        self._sync_tabs_to_attrs()
        settings = {
            "input_path": self.input_path,
            "output_dir": self.output_dir,
            "style": self.style,
            "custom_params": {
                "intensity": self.intensity,
                "min_parcels": self.min_parcels,
                "max_parcels": self.max_parcels,
                "min_area": self.min_area,
                "buffer_distance": self.buffer_distance,
                "min_distance": self.min_distance
            },
            "po_config": {
                "path": self.po_path,
                "layer": self.po_layer,
                "fields": self.po_fields
            },
            "exclusion_list": self.exclusion_list,
            "intensity_by_field": self.settings.get("intensity_by_field", {})
        }
        save_gui_settings(settings)
        self.log_text.append("[INFO] Settings saved.")
        self.config_tab.configChanged.emit(settings)

    def _restore_gui_settings(self) -> None:
        settings = load_gui_settings()
        self.input_path = settings.get("input_path", "")
        self.output_dir = settings.get("output_dir", "")
        self.style = settings.get("style", "calibration")
        params = settings.get("custom_params", {})
        self.intensity = params.get("intensity", 50)
        self.min_parcels = params.get("min_parcels", 1)
        self.max_parcels = params.get("max_parcels", 10)
        self.min_area = params.get("min_area", 0.3)
        self.buffer_distance = params.get("buffer_distance", -20)
        self.min_distance = params.get("min_distance", 60.0)
        po_conf = settings.get("po_config", {})
        self.po_path = po_conf.get("path", "")
        self.po_layer = po_conf.get("layer", "")
        self.po_fields = po_conf.get("fields", [])
        self.exclusion_list = settings.get("exclusion_list", [])
        self.settings = settings
        self._sync_attrs_to_tabs()
        self.log_text.append("[INFO] Settings loaded.")
        self.config_tab.configChanged.emit(settings)

    def _on_any_field_changed(self):
        self._sync_tabs_to_attrs()
        self._last_gui_hash = self._hash_dict(self._get_pipeline_params())

    def _on_log_level_changed(self, level):
        self._current_log_level = level
        self.log_text.append(f"[INFO] Log level set to: {level}")

    def _export_pipeline_config(self):
        params = self._get_pipeline_params()
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Pipeline Config", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(params, f, indent=4)
                self.log_text.append(f"[INFO] Pipeline config exported to: {file_path}")
            except Exception as e:
                self.log_text.append(f"[ERROR] Failed to export config: {str(e)}")

    def _import_pipeline_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Pipeline Config", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                self._set_pipeline_params(params)
                self._imported_config_path = file_path
                self._imported_config_hash = self._hash_dict(params)
                self._last_gui_hash = self._hash_dict(self._get_pipeline_params())
                self.log_text.append(f"[INFO] Pipeline config imported from: {file_path}")
                self.log_text.append(f"[INFO] Ready to run with imported config: {file_path}")
            except Exception as e:
                self.log_text.append(f"[ERROR] Failed to import config: {str(e)}")

    def _hash_dict(self, d):
        import hashlib
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode("utf-8")).hexdigest()

    def _on_config_changed(self, config: dict) -> None:
        """
        Callback que se ejecuta cuando la configuración cambia en ConfigTab.
        Refresca los tabs relevantes (por ejemplo, POTab).
        """
        if hasattr(self.po_tab, "refresh_from_config"):
            self.po_tab.refresh_from_config(config.get("po_config", {}))