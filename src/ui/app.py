# src/ui/app.py

import os
import sys
import json
import tempfile
from typing import Dict, Any, Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QMessageBox, QTabWidget, QSplitter, QPushButton, QFileDialog,
    QComboBox
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment

from src.utils.settings import load_gui_settings, save_gui_settings
from src.ui.tab.pipeline_tab import PipelineTab
from src.ui.tab.po_tab import POTab
from src.ui.tab.exclusion_tab import ExclusionTab
from src.ui.tab.config_tab import ConfigTab

class ParcelGeneratorApp(QMainWindow):
    """
    Main application window for the Parcel Generator.
    Acts as a coordinator for the UI tabs and the processing pipeline.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Parcel Generator")
        self.setMinimumSize(900, 700)

        self.process: Optional[QProcess] = None
        self._last_temp_config_path: Optional[str] = None
        # [CORRECCIÓN] Diccionario central para mantener el estado de la configuración.
        self.pipeline_config: Dict[str, Any] = {}

        self._init_ui()
        self._connect_signals()
        self._restore_gui_settings()

    def _init_ui(self) -> None:
        """Initializes the main UI layout and sub-widgets (tabs)."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        splitter = QSplitter(Qt.Orientation.Vertical)

        tabs = QTabWidget()
        self.pipeline_tab = PipelineTab()
        self.po_tab = POTab()
        self.exclusion_tab = ExclusionTab()
        self.config_tab = ConfigTab()

        tabs.addTab(self.pipeline_tab, "Pipeline")
        tabs.addTab(self.po_tab, "Plan Operative (PO)")
        tabs.addTab(self.exclusion_tab, "Exclusion Layers")
        tabs.addTab(self.config_tab, "Configuration")

        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_btn_layout = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Logs")
        log_btn_layout.addWidget(self.clear_log_btn)
        log_btn_layout.addStretch(1)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Logs and messages will appear here...")
        
        log_layout.addLayout(log_btn_layout)
        log_layout.addWidget(self.log_text)

        splitter.addWidget(tabs)
        splitter.addWidget(log_widget)
        splitter.setSizes([450, 250])
        main_layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        """Connects signals from tabs and other widgets to the main window's slots."""
        self.pipeline_tab.runRequested.connect(self._run_pipeline)
        self.pipeline_tab.stop_btn.clicked.connect(self._stop_pipeline)
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        
        # [CORRECCIÓN] Añadir las conexiones que faltaban.
        # Esto asegura que la configuración central se actualiza cuando el usuario
        # cambia algo en las pestañas de PO o Exclusiones.
        self.po_tab.configChanged.connect(self._on_po_config_changed)
        self.exclusion_tab.configChanged.connect(self._on_exclusions_changed)

        self.config_tab.findChild(QPushButton, "export_config_btn").clicked.connect(self._export_config)
        self.config_tab.findChild(QPushButton, "import_config_btn").clicked.connect(self._import_config)
        self.config_tab.findChild(QPushButton, "save_settings_btn").clicked.connect(self._save_gui_settings)
        self.config_tab.findChild(QPushButton, "load_settings_btn").clicked.connect(self._restore_gui_settings)

    # --- SLOTS FOR HANDLING CONFIGURATION CHANGES ---

    def _on_po_config_changed(self, po_config: Dict[str, Any]) -> None:
        """
        [CORRECCIÓN] Este slot se activa cuando la config de PO cambia.
        """
        self.pipeline_config['PO_CONFIG'] = po_config
        self.log_text.append("[INFO] PO configuration updated.")

    def _on_exclusions_changed(self, exclusion_list: List[Dict[str, Any]]) -> None:
        """
        [CORRECCIÓN] Este slot se activa cuando la lista de exclusión cambia.
        """
        self.pipeline_config['CAPAS_EXCLUSION'] = exclusion_list
        self.log_text.append(f"[INFO] Exclusion list updated.")
        
    # --- Pipeline Execution ---
    
    def _run_pipeline(self) -> None:
        """Assembles the full config and starts the pipeline in a QProcess."""
        full_config = self._get_full_pipeline_config()

        if not full_config.get("input_path") or not os.path.exists(full_config.get("input_path")):
            QMessageBox.warning(self, "Input Error", "Please select a valid input file.")
            return
        if not full_config.get("output_dir"):
            QMessageBox.warning(self, "Output Error", "Please select an output directory.")
            return

        try:
            json_config_dir = os.path.join(os.path.dirname(__file__), "..", "json_config")
            os.makedirs(json_config_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json", dir=json_config_dir, encoding="utf-8") as tmp:
                json.dump(full_config, tmp, indent=4)
                self._last_temp_config_path = tmp.name
        except Exception as e:
            QMessageBox.critical(self, "Config Error", f"Failed to create temporary config file: {e}")
            return

        self.log_text.append(f"[INFO] Starting pipeline with config: {self._last_temp_config_path}")
        self.pipeline_tab.set_running_state(is_running=True)

        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments(["-m", "src.run_pipeline", self._last_temp_config_path])
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.process.setWorkingDirectory(project_root)
        
        env = QProcessEnvironment.systemEnvironment()
        log_level = self.config_tab.findChild(QComboBox, "log_level_combo").currentText()
        env.insert("LOG_LEVEL", log_level)
        self.process.setProcessEnvironment(env)
        
        self.process.readyReadStandardOutput.connect(self._on_process_stdout)
        self.process.readyReadStandardError.connect(self._on_process_stderr)
        self.process.finished.connect(self._on_process_finished)
        self.process.start()

    def _stop_pipeline(self) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            reply = QMessageBox.question(
                self, "Confirm Stop", "Are you sure you want to stop the process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.log_text.append("[INFO] Terminating process...")
                self.process.kill()

    # --- QProcess Handlers ---
    def _on_process_stdout(self) -> None:
        # ... (sin cambios)
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.strip().splitlines():
            try:
                msg = json.loads(line)
                msg_type = msg.get("type", "").lower()
                if msg_type == "progress":
                    self.pipeline_tab.update_progress(msg.get("value", 0))
                    self.log_text.append(f"[PROGRESS] {msg.get('value', 0)}% - {msg.get('status', '')}")
                elif msg_type == "log":
                    self.log_text.append(f"[{msg.get('level', 'info').upper()}] {msg.get('message', '')}")
                elif msg_type == "success":
                    self.pipeline_tab.update_progress(100)
                    QMessageBox.information(self, "Success", msg.get("message", "Process completed."))
                elif msg_type == "error":
                    error_msg = msg.get('message', 'An unknown error occurred.')
                    traceback_info = "\n".join(msg.get('traceback_lines', []))
                    full_error = f"{error_msg}\n\nTraceback:\n{traceback_info}"
                    self.log_text.append(f"[ERROR] {full_error}")
                    QMessageBox.critical(self, "Pipeline Error", full_error)
                else:
                    self.log_text.append(f"[PROCESS] {line}")
            except json.JSONDecodeError:
                self.log_text.append(f"[PROCESS] {line}")

    def _on_process_stderr(self) -> None:
        # ... (sin cambios)
        error_data = self.process.readAllStandardError().data().decode("utf-8", errors="replace").strip()
        if error_data:
            self.log_text.append(f"[STDERR] {error_data}")

    def _on_process_finished(self) -> None:
        # ... (sin cambios)
        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus()
        self.log_text.append(f"[INFO] Process finished. Exit code: {exit_code}, Status: {exit_status.name}")
        self.pipeline_tab.set_running_state(is_running=False)
        self.process = None
        if self._last_temp_config_path and os.path.exists(self._last_temp_config_path):
            try:
                os.remove(self._last_temp_config_path)
                self.log_text.append(f"[INFO] Removed temporary config: {self._last_temp_config_path}")
                self._last_temp_config_path = None
            except Exception as e:
                self.log_text.append(f"[WARNING] Could not remove temp file: {e}")

    # --- SETTINGS & CONFIG MANAGEMENT ---

    def _get_full_pipeline_config(self) -> Dict[str, Any]:
        """Assembles the complete pipeline configuration from all UI tabs."""
        base_config = self.pipeline_tab.get_config()
        
        full_config = {
            "input_path": base_config.get("input_path"),
            "output_dir": base_config.get("output_dir"),
            "style": base_config.get("style"),
            "entrega": None,
            "cfg_overrides": base_config.get("cfg_overrides", {})
        }

        # [CORRECCIÓN] Usar la configuración centralizada que se actualiza con las señales.
        if self.pipeline_config.get("PO_CONFIG"):
            full_config["cfg_overrides"]["PO_CONFIG"] = self.pipeline_config.get("PO_CONFIG")
        if self.pipeline_config.get("CAPAS_EXCLUSION"):
            full_config["cfg_overrides"]["CAPAS_EXCLUSION"] = self.pipeline_config.get("CAPAS_EXCLUSION")

        return full_config

    def _export_config(self) -> None:
        # ... (sin cambios)
        config_to_export = self._get_full_pipeline_config()
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Pipeline Config", "", "JSON Files (*.json);;All Files (*)")
        if not file_path:
            self.log_text.append("[INFO] Export cancelled by user.")
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_export, f, indent=4, ensure_ascii=False)
            self.log_text.append(f"[SUCCESS] Configuration successfully exported to: {file_path}")
            QMessageBox.information(self, "Export Successful", f"Configuration saved to:\n{file_path}")
        except Exception as e:
            self.log_text.append(f"[ERROR] Failed to export configuration: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Could not save the configuration file.\n\nError: {e}")

    def _import_config(self) -> None:
        # ... (sin cambios)
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Pipeline Config", "", "JSON Files (*.json);;All Files (*)")
        if not file_path:
            self.log_text.append("[INFO] Import cancelled by user.")
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if "input_path" not in config or "style" not in config:
                raise KeyError("Imported file is missing required keys ('input_path', 'style').")
            cfg_overrides = config.get("cfg_overrides", {})
            custom_params = {
                "intensity": cfg_overrides.get("INTENSIDAD"), "min_parcels": cfg_overrides.get("MIN_PARCELAS"),
                "max_parcels": cfg_overrides.get("MAX_PARCELAS"), "min_area": cfg_overrides.get("AREA_MINIMA_HA"),
                "buffer_distance": cfg_overrides.get("BUFFER_DISTANCE"), "min_distance": cfg_overrides.get("MIN_DISTANCE")}
            pipeline_config = {"input_path": config.get("input_path"), "output_dir": config.get("output_dir"), "style": config.get("style"), "custom_params": custom_params}
            po_config = cfg_overrides.get("PO_CONFIG", {})
            exclusion_config = cfg_overrides.get("CAPAS_EXCLUSION", [])
            self.pipeline_tab.set_config(pipeline_config)
            self.po_tab.set_config(po_config)
            self.exclusion_tab.set_config(exclusion_config)
            self.log_text.append(f"[SUCCESS] Configuration successfully imported from: {file_path}")
            QMessageBox.information(self, "Import Successful", f"Configuration loaded from:\n{file_path}")
        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_message = f"Failed to import configuration from {os.path.basename(file_path)}."
            self.log_text.append(f"[ERROR] {error_message}\nDetails: {e}")
            QMessageBox.critical(self, "Import Error", f"{error_message}\n\nPlease check the file format.\n\nError: {e}")

    def _save_gui_settings(self) -> None:
        # ... (sin cambios)
        pipeline_settings = self.pipeline_tab.get_config()
        custom_params = {"intensity": self.pipeline_tab.intensity_spin.value(), "min_parcels": self.pipeline_tab.min_parcels_spin.value(), "max_parcels": self.pipeline_tab.max_parcels_spin.value(), "min_area": self.pipeline_tab.min_area_spin.value(), "buffer_distance": self.pipeline_tab.buffer_spin.value(), "min_distance": self.pipeline_tab.min_distance_spin.value()}
        full_settings = {"input_path": pipeline_settings.get("input_path"), "output_dir": pipeline_settings.get("output_dir"), "style": pipeline_settings.get("style"), "custom_params": custom_params, "po_config": self.po_tab.get_config(), "exclusion_list": self.exclusion_tab.get_config()}
        save_gui_settings(full_settings)
        self.log_text.append("[INFO] GUI settings saved successfully.")

    def _restore_gui_settings(self) -> None:
        settings = load_gui_settings()
        
        pipeline_config = {"input_path": settings.get("input_path"), "output_dir": settings.get("output_dir"), "style": settings.get("style"), "custom_params": settings.get("custom_params")}
        po_config = settings.get("po_config", {})
        exclusion_config = settings.get("exclusion_list", [])

        self.pipeline_tab.set_config(pipeline_config)
        self.po_tab.set_config(po_config)
        self.exclusion_tab.set_config(exclusion_config)
        
        # [CORRECCIÓN] Después de cargar, actualizar el estado central.
        self._on_po_config_changed(self.po_tab.get_config())
        self._on_exclusions_changed(self.exclusion_tab.get_config())
        
        self.log_text.append("[INFO] GUI settings loaded successfully.")
        
    def closeEvent(self, event) -> None:
        # ... (sin cambios)
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            reply = QMessageBox.question(self, 'Process Still Running', "A pipeline process is still running. Are you sure you want to close? The process will be terminated.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_pipeline()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()