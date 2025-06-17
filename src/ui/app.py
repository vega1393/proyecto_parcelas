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
from src.ui.tab.gridcode_tab import GridCodeTab
from src.ui.tab.delivery_tab import DeliveryTab

class ParcelGeneratorApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Parcel Generator - Enhanced")
        self.setMinimumSize(800, 600)  # Aumentado para acomodar nuevos tabs

        self.process: Optional[QProcess] = None
        self._last_temp_config_path: Optional[str] = None
        self.pipeline_config: Dict[str, Any] = {}

        self._init_ui()
        self._connect_signals()
        self._restore_gui_settings()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Tabs principales
        tabs = QTabWidget()
        
        # Tabs existentes
        self.pipeline_tab = PipelineTab()
        self.po_tab = POTab()
        self.exclusion_tab = ExclusionTab()
        self.config_tab = ConfigTab()
        
        # Nuevos tabs
        self.gridcode_tab = GridCodeTab()
        self.delivery_tab = DeliveryTab()
        
        # Agregar tabs en orden lógico
        tabs.addTab(self.pipeline_tab, "Pipeline")
        tabs.addTab(self.gridcode_tab, "GridCode")  # NUEVO
        tabs.addTab(self.po_tab, "Plan Operative (PO)")
        tabs.addTab(self.exclusion_tab, "Exclusion Layers")
        tabs.addTab(self.delivery_tab, "Delivery")  # NUEVO
        tabs.addTab(self.config_tab, "Configuration")
        
        # Log widget
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_btn_layout = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("Clear Logs")
        log_btn_layout.addWidget(self.clear_log_btn)
        log_btn_layout.addStretch(1)
        log_layout.addLayout(log_btn_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Logs and messages will appear here...")
        log_layout.addWidget(self.log_text)
        log_widget.setLayout(log_layout)
        
        splitter.addWidget(tabs)
        splitter.addWidget(log_widget)
        splitter.setSizes([500, 300])  # Más espacio para tabs
        main_layout.addWidget(splitter)

    def _connect_signals(self):
        # Señales existentes
        self.pipeline_tab.runRequested.connect(self._run_pipeline)
        self.pipeline_tab.stop_btn.clicked.connect(self._stop_pipeline)
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        self.po_tab.configChanged.connect(self._on_po_config_changed)
        self.exclusion_tab.configChanged.connect(self._on_exclusions_changed)
        
        # Nuevas señales
        self.gridcode_tab.configChanged.connect(self._on_gridcode_config_changed)
        self.delivery_tab.configChanged.connect(self._on_delivery_config_changed)
        
        # Señales de configuración
        self.config_tab.findChild(QPushButton, "export_config_btn").clicked.connect(self._export_config)
        self.config_tab.findChild(QPushButton, "import_config_btn").clicked.connect(self._import_config)
        self.config_tab.findChild(QPushButton, "save_settings_btn").clicked.connect(self._save_gui_settings)
        self.config_tab.findChild(QPushButton, "load_settings_btn").clicked.connect(self._restore_gui_settings)

    def _on_po_config_changed(self, po_config: Dict[str, Any]):
        self.pipeline_config['PO_CONFIG'] = po_config
        self.log_text.append("[INFO] PO configuration updated.")

    def _on_exclusions_changed(self, exclusion_list: List[Dict[str, Any]]):
        self.pipeline_config['CAPAS_EXCLUSION'] = exclusion_list
        self.log_text.append(f"[INFO] Exclusion list updated.")

    def _on_gridcode_config_changed(self, gridcode_config: Dict[str, Any]):
        """Maneja cambios en la configuración de GridCode."""
        self.pipeline_config['GRIDCODE_CONFIG'] = gridcode_config
        if gridcode_config.get('enabled'):
            self.log_text.append("[INFO] GridCode configuration enabled and updated.")
        else:
            self.log_text.append("[INFO] GridCode configuration disabled.")

    def _on_delivery_config_changed(self, delivery_config: Dict[str, Any]):
        """Maneja cambios en la configuración de entrega."""
        self.pipeline_config['DELIVERY_CONFIG'] = delivery_config
        self.log_text.append(f"[INFO] Delivery configuration updated: {delivery_config.get('delivery_code', 'N/A')}")

    def _run_pipeline(self):
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
        
        self.log_text.append(f"[INFO] Starting enhanced pipeline with config: {self._last_temp_config_path}")
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

    def _stop_pipeline(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            reply = QMessageBox.question(
                self, "Confirm Stop", 
                "Are you sure you want to stop the process?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.log_text.append("[INFO] Terminating process...")
                self.process.kill()

    def _on_process_stdout(self):
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
                    QMessageBox.information(self, "Success", msg.get("message", "Process completed successfully."))
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

    def _on_process_stderr(self):
        error_data = self.process.readAllStandardError().data().decode("utf-8", errors="replace").strip()
        if error_data:
            self.log_text.append(f"[STDERR] {error_data}")
        
    def _on_process_finished(self):
        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus()
        self.log_text.append(f"[INFO] Process finished. Exit code: {exit_code}, Status: {exit_status.name}")
        self.pipeline_tab.set_running_state(is_running=False)
        self.process = None
        
        # Show user-friendly error messages for common issues
        if exit_code != 0:
            # Check for common configuration errors in the log
            log_content = self.log_text.toPlainText()
            
            if "No quedan registros después de filtrar" in log_content or "Error en filtros iniciales" in log_content:
                QMessageBox.warning(self, "Configuration Error - No Data After Filters", 
                                  "The pipeline failed because no data remained after applying filters.\n\n"
                                  "POSSIBLE SOLUTIONS:\n"
                                  "• Check that the land use types in your configuration match the actual data\n"
                                  "• Use 'Load Types from Plan Operativo' to automatically load correct types\n"
                                  "• Review the filter configuration in the Pipeline tab\n"
                                  "• Ensure the Plan Operativo is correctly configured\n\n"
                                  "Check the log for detailed information about which values were found in your data.")
            elif "DataSourceError" in log_content or "No such file or directory" in log_content:
                QMessageBox.critical(self, "File Access Error", 
                                   "The pipeline failed because it could not access required files.\n\n"
                                   "POSSIBLE SOLUTIONS:\n"
                                   "• Check that all input files exist and are accessible\n"
                                   "• Verify file paths in your configuration\n"
                                   "• Ensure you have read/write permissions for the specified directories\n"
                                   "• Check that the Plan Operativo file and layer are correctly configured")
            elif "ImportError" in log_content or "ModuleNotFoundError" in log_content:
                QMessageBox.critical(self, "Dependency Error", 
                                   "The pipeline failed due to missing dependencies.\n\n"
                                   "POSSIBLE SOLUTIONS:\n"
                                   "• Ensure all required Python packages are installed\n"
                                   "• Check that your environment has geopandas, pyogrio, and other dependencies\n"
                                   "• Try reinstalling the requirements: pip install -r requirements.txt")
            else:
                QMessageBox.critical(self, "Pipeline Error", 
                                   f"The pipeline failed with exit code {exit_code}.\n\n"
                                   "Please check the log for detailed error information.\n"
                                   "Common issues include:\n"
                                   "• Incorrect file paths or permissions\n"
                                   "• Mismatched data types or field names\n"
                                   "• Invalid configuration parameters")
        
        if self._last_temp_config_path and os.path.exists(self._last_temp_config_path):
            try:
                os.remove(self._last_temp_config_path)
                self.log_text.append(f"[INFO] Removed temporary config: {self._last_temp_config_path}")
                self._last_temp_config_path = None
            except Exception as e:
                self.log_text.append(f"[WARNING] Could not remove temp file: {e}")

    # --- SETTINGS & CONFIG MANAGEMENT ---

    def _get_full_pipeline_config(self) -> Dict[str, Any]:
        """Genera la configuración completa del pipeline incluyendo las nuevas funcionalidades."""
        base_config = self.pipeline_tab.get_config()
        
        # Configuración base
        full_config = {
            "input_path": base_config.get("input_path"),
            "output_dir": base_config.get("output_dir"),
            "style": base_config.get("style"),
            "use_csv": base_config.get("use_csv"),
            "csv_path": base_config.get("csv_path"),
            "grouping_fields": base_config.get("grouping_fields"),
            "entrega": None,
            "cfg_overrides": base_config.get("cfg_overrides", {})
        }
        
        # Agregar configuraciones de CSV avanzado
        if base_config.get("use_csv"):
            full_config["count_column_csv"] = base_config.get("count_column_csv")
            full_config["field_mappings"] = base_config.get("field_mappings", [])
        
        # Agregar configuraciones adicionales
        if self.pipeline_config.get("PO_CONFIG"):
            full_config["cfg_overrides"]["PO_CONFIG"] = self.pipeline_config.get("PO_CONFIG")
        
        # CRITICAL FIX: Always include CAPAS_EXCLUSION to override defaults
        # If no exclusion layers are configured, send empty list to override base config
        exclusion_layers = self.pipeline_config.get("CAPAS_EXCLUSION", [])
        full_config["cfg_overrides"]["CAPAS_EXCLUSION"] = exclusion_layers
        
        # NUEVO: Agregar configuración de GridCode
        gridcode_config = self.pipeline_config.get("GRIDCODE_CONFIG", {})
        if gridcode_config.get("enabled"):
            full_config["cfg_overrides"]["USE_GRIDCODE"] = True
            full_config["cfg_overrides"]["GRIDCODE_PARAMS"] = gridcode_config.get("gridcode_params", {})
            
            # CRITICAL FIX: Auto-include 'gridcode' in grouping fields when GridCode is enabled
            grouping_fields = list(full_config.get("grouping_fields", []))
            if "gridcode" not in grouping_fields:
                grouping_fields.append("gridcode")
                full_config["grouping_fields"] = grouping_fields
                self.log_text.append("[INFO] GridCode enabled: automatically added 'gridcode' to grouping fields")
        else:
            # Remove 'gridcode' from grouping fields when GridCode is disabled
            grouping_fields = list(full_config.get("grouping_fields", []))
            if "gridcode" in grouping_fields:
                grouping_fields.remove("gridcode")
                full_config["grouping_fields"] = grouping_fields
                self.log_text.append("[INFO] GridCode disabled: automatically removed 'gridcode' from grouping fields")
        
        # NUEVO: Agregar configuración de entrega
        delivery_config = self.pipeline_config.get("DELIVERY_CONFIG", {})
        if delivery_config:
            full_config["delivery_code"] = delivery_config.get("delivery_code")
            full_config["date_today"] = delivery_config.get("date_today")
            full_config["delivery_metadata"] = delivery_config.get("metadata", {})
        
        return full_config

    def _export_config(self):
        config_to_export = self._get_full_pipeline_config()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Pipeline Config", 
            "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            self.log_text.append("[INFO] Export cancelled by user.")
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_export, f, indent=4, ensure_ascii=False)
            self.log_text.append(f"[SUCCESS] Enhanced configuration successfully exported to: {file_path}")
            QMessageBox.information(self, "Export Successful", f"Configuration saved to:\n{file_path}")
        except Exception as e:
            self.log_text.append(f"[ERROR] Failed to export configuration: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Could not save the configuration file.\n\nError: {e}")
    
    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Pipeline Config", 
            "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            self.log_text.append("[INFO] Import cancelled by user.")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if "input_path" not in config or "style" not in config:
                raise KeyError("Imported file is missing required keys ('input_path', 'style').")
            
            # Configuración del pipeline
            pipeline_config = {
                "input_path": config.get("input_path"),
                "output_dir": config.get("output_dir"),
                "style": config.get("style"),
                "use_csv": config.get("use_csv", False),
                "csv_path": config.get("csv_path"),
                "grouping_fields": config.get("grouping_fields", []),
                "custom_params": config.get("cfg_overrides", {})
            }
            
            # Agregar mapeo CSV avanzado
            if config.get("use_csv"):
                pipeline_config["count_column_csv"] = config.get("count_column_csv")
                pipeline_config["field_mappings"] = config.get("field_mappings", [])
            
            cfg_overrides = config.get("cfg_overrides", {})
            po_config = cfg_overrides.get("PO_CONFIG", {})
            exclusion_config = cfg_overrides.get("CAPAS_EXCLUSION", [])
            
            # NUEVO: Configuración de GridCode
            gridcode_config = {
                "enabled": cfg_overrides.get("USE_GRIDCODE", False),
                "gridcode_params": cfg_overrides.get("GRIDCODE_PARAMS", {})
            }
            
            # NUEVO: Configuración de entrega
            delivery_config = {
                "delivery_code": config.get("delivery_code", ""),
                "date_today": config.get("date_today", ""),
                "metadata": config.get("delivery_metadata", {})
            }
            
            # Aplicar configuraciones
            self.pipeline_tab.set_config(pipeline_config)
            self.po_tab.set_config(po_config)
            self.exclusion_tab.set_config(exclusion_config)
            self.gridcode_tab.set_config(gridcode_config)
            self.delivery_tab.set_config(delivery_config)
            
            self.log_text.append(f"[SUCCESS] Enhanced configuration successfully imported from: {file_path}")
            QMessageBox.information(self, "Import Successful", f"Configuration loaded from:\n{file_path}")
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_message = f"Failed to import configuration from {os.path.basename(file_path)}."
            self.log_text.append(f"[ERROR] {error_message}\nDetails: {e}")
            QMessageBox.critical(self, "Import Error", f"{error_message}\n\nPlease check the file format.\n\nError: {e}")

    def _save_gui_settings(self) -> None:
        """Guarda todas las configuraciones de la GUI incluyendo las nuevas."""
        pipeline_settings = self.pipeline_tab.get_config()
        
        full_settings = {
            "input_path": pipeline_settings.get("input_path"),
            "output_dir": pipeline_settings.get("output_dir"),
            "style": pipeline_settings.get("style"),
            "use_csv": pipeline_settings.get("use_csv"),
            "csv_path": pipeline_settings.get("csv_path"),
            "grouping_fields": pipeline_settings.get("grouping_fields", []),
            "cfg_overrides": pipeline_settings.get("cfg_overrides", {}),
            "custom_params": {"intensity": self.pipeline_tab.intensity_spin.value()},
            "po_config": self.po_tab.get_config(),
            "exclusion_list": self.exclusion_tab.get_config(),
            "gridcode_config": self.gridcode_tab.get_config(),
            "delivery_config": self.delivery_tab.get_config()
        }
        
        # Agregar mapeo CSV si está activo
        if pipeline_settings.get("use_csv"):
            full_settings["count_column_csv"] = pipeline_settings.get("count_column_csv")
            full_settings["field_mappings"] = pipeline_settings.get("field_mappings", [])
        
        save_gui_settings(full_settings)
        self.log_text.append("[INFO] Enhanced GUI settings saved successfully.")

    def _restore_gui_settings(self) -> None:
        """Carga configuraciones incluyendo las nuevas funcionalidades."""
        settings = load_gui_settings()
        
        use_csv_value = bool(settings.get("use_csv", False))

        pipeline_config = {
            "input_path": settings.get("input_path"),
            "output_dir": settings.get("output_dir"),
            "style": settings.get("style"),
            "use_csv": use_csv_value,
            "csv_path": settings.get("csv_path"),
            "grouping_fields": settings.get("grouping_fields", []),
            "cfg_overrides": settings.get("cfg_overrides", {}),
            "custom_params": settings.get("custom_params")
        }
        
        # Agregar mapeo CSV si existe
        if use_csv_value:
            pipeline_config["count_column_csv"] = settings.get("count_column_csv")
            pipeline_config["field_mappings"] = settings.get("field_mappings", [])
        
        po_config = settings.get("po_config", {})
        exclusion_config = settings.get("exclusion_list", [])
        
        # NUEVOS
        gridcode_config = settings.get("gridcode_config", {"enabled": False})
        delivery_config = settings.get("delivery_config", {})

        self.pipeline_tab.set_config(pipeline_config)
        self.po_tab.set_config(po_config)
        self.exclusion_tab.set_config(exclusion_config)
        self.gridcode_tab.set_config(gridcode_config)
        self.delivery_tab.set_config(delivery_config)
        
        self._on_po_config_changed(self.po_tab.get_config())
        self._on_exclusions_changed(self.exclusion_tab.get_config())
        self._on_gridcode_config_changed(self.gridcode_tab.get_config())
        self._on_delivery_config_changed(self.delivery_tab.get_config())
        
        self.log_text.append("[INFO] Enhanced GUI settings loaded successfully.")

    def _cleanup_temp_files(self) -> None:
        """Clean up all temporary configuration files."""
        # Clean specific temp file
        if self._last_temp_config_path and os.path.exists(self._last_temp_config_path):
            try:
                os.remove(self._last_temp_config_path)
                self.log_text.append(f"[INFO] Removed temporary config: {self._last_temp_config_path}")
                self._last_temp_config_path = None
            except Exception as e:
                self.log_text.append(f"[WARNING] Could not remove temp file: {e}")
        
        # Clean up any orphaned temp files in json_config directory
        json_config_dir = os.path.join(os.path.dirname(__file__), "..", "json_config")
        if os.path.exists(json_config_dir):
            try:
                import glob
                temp_files = glob.glob(os.path.join(json_config_dir, "tmp*.json"))
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                        self.log_text.append(f"[INFO] Cleaned up orphaned temp file: {os.path.basename(temp_file)}")
                    except Exception as e:
                        self.log_text.append(f"[WARNING] Could not remove orphaned temp file {temp_file}: {e}")
            except Exception as e:
                self.log_text.append(f"[WARNING] Error during temp files cleanup: {e}")
        
    def closeEvent(self, event):
        """Clean up resources before closing."""
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            reply = QMessageBox.question(
                self, 'Process Still Running', 
                "A pipeline process is still running. Are you sure you want to close? The process will be terminated.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_pipeline()
                self._cleanup_temp_files()
                self._save_gui_settings()
                event.accept()
            else:
                event.ignore()
        else:
            self._cleanup_temp_files()
            self._save_gui_settings()
            event.accept()