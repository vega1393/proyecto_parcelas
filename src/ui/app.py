# src/ui/app.py

import os
import sys
import json
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QMessageBox, QTabWidget, QSplitter, QPushButton, QFileDialog,
    QComboBox, QProgressBar
)
from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment

from src.utils.settings import load_gui_settings, save_gui_settings
from src.ui.tab.pipeline_tab import PipelineTab
from src.ui.tab.sampling_tab import SamplingTab
from src.ui.tab.po_tab import POTab
from src.ui.tab.exclusion_tab import ExclusionTab
from src.ui.tab.config_tab import ConfigTab
from src.ui.tab.gridcode_tab import GridCodeTab
from src.ui.tab.delivery_tab import DeliveryTab
from src.ui.tab.column_order_tab import ColumnOrderTab
from src.ui.tab.help_tab import HelpTab

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
        self.sampling_tab = SamplingTab()  # NUEVO
        self.po_tab = POTab()
        self.exclusion_tab = ExclusionTab()
        self.config_tab = ConfigTab()
        
        # Nuevos tabs
        self.gridcode_tab = GridCodeTab()
        self.delivery_tab = DeliveryTab()
        self.column_order_tab = ColumnOrderTab()
        self.help_tab = HelpTab()
        
        # Agregar tabs en orden lógico
        tabs.addTab(self.pipeline_tab, "Pipeline")
        tabs.addTab(self.sampling_tab, "Sampling Method")  # NUEVO
        tabs.addTab(self.gridcode_tab, "GridCode")
        tabs.addTab(self.po_tab, "Plan Operative (PO)")
        tabs.addTab(self.exclusion_tab, "Exclusion Layers")
        tabs.addTab(self.delivery_tab, "Delivery")
        tabs.addTab(self.column_order_tab, "Column Order")
        tabs.addTab(self.config_tab, "Configuration")
        tabs.addTab(self.help_tab, "Help")
        
        # --- CONTROLES PRINCIPALES DE EJECUCIÓN ---
        # Crear una barra de herramientas prominente para los controles de ejecución
        execution_toolbar = QWidget()
        execution_layout = QHBoxLayout(execution_toolbar)
        execution_layout.setContentsMargins(10, 8, 10, 8)
        
        # Botones de ejecución prominentes
        self.main_run_btn = QPushButton("🚀 Run Pipeline")
        self.main_run_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 140px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #dee2e6;
            }
        """)
        
        self.main_stop_btn = QPushButton("⏹️ Stop")
        self.main_stop_btn.setEnabled(False)
        self.main_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #dee2e6;
            }
        """)
        
        # Barra de progreso principal
        self.main_progress_bar = QProgressBar()
        self.main_progress_bar.setVisible(False)
        self.main_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #007acc;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                height: 24px;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 4px;
            }
        """)
        
        # Agregar widgets a la barra de herramientas
        execution_layout.addWidget(self.main_run_btn)
        execution_layout.addWidget(self.main_stop_btn)
        execution_layout.addWidget(self.main_progress_bar, 1)  # Expandir para llenar espacio
        execution_layout.addStretch()
        
        # Agregar la barra de herramientas al layout principal
        main_layout.addWidget(execution_toolbar)
        
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
        # Señales de los controles principales de ejecución
        self.main_run_btn.clicked.connect(self._run_pipeline)
        self.main_stop_btn.clicked.connect(self._stop_pipeline)
        
        # Señales existentes (mantener compatibilidad)
        self.pipeline_tab.runRequested.connect(self._run_pipeline)
        self.clear_log_btn.clicked.connect(self.log_text.clear)
        self.po_tab.configChanged.connect(self._on_po_config_changed)
        self.exclusion_tab.configChanged.connect(self._on_exclusions_changed)
        
        # Nuevas señales
        self.sampling_tab.configChanged.connect(self._on_sampling_config_changed)  # NUEVO
        self.gridcode_tab.configChanged.connect(self._on_gridcode_config_changed)
        self.delivery_tab.configChanged.connect(self._on_delivery_config_changed)
        self.column_order_tab.configChanged.connect(self._on_column_order_config_changed)
        
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

    def _on_sampling_config_changed(self, sampling_config: Dict[str, Any]):
        """Maneja cambios en la configuración de muestreo."""
        self.pipeline_config['SAMPLING_CONFIG'] = sampling_config
        method = "CSV-based" if sampling_config.get("use_csv") else "Intensity-based"
        self.log_text.append(f"[INFO] Sampling method updated: {method}")

    def _on_gridcode_config_changed(self, gridcode_config: Dict[str, Any]):
        """Maneja cambios en la configuración de GridCode."""
        # Solo actualizar si realmente cambió para evitar mensajes duplicados
        previous_config = self.pipeline_config.get('GRIDCODE_CONFIG', {})
        if previous_config != gridcode_config:
            self.pipeline_config['GRIDCODE_CONFIG'] = gridcode_config
            if gridcode_config.get('enabled'):
                self.log_text.append("[INFO] GridCode configuration enabled and updated.")
            else:
                self.log_text.append("[INFO] GridCode configuration disabled.")

    def _on_delivery_config_changed(self, delivery_config: Dict[str, Any]):
        """Maneja cambios en la configuración de entrega."""
        # Solo actualizar si realmente cambió para evitar mensajes duplicados
        previous_config = self.pipeline_config.get('DELIVERY_CONFIG', {})
        if previous_config != delivery_config:
            self.pipeline_config['DELIVERY_CONFIG'] = delivery_config
            self.log_text.append(f"[INFO] Delivery configuration updated: {delivery_config.get('delivery_code', 'N/A')}")

    def _on_column_order_config_changed(self, column_order_config: Dict[str, Any]):
        """Maneja cambios en la configuración de orden de columnas."""
        if column_order_config.get("action") == "request_pipeline_output":
            # Obtener la ruta de salida final del pipeline
            pipeline_config = self.pipeline_tab.get_config()
            output_dir = pipeline_config.get("output_dir")
            
            if output_dir:
                # Construir la ruta del archivo final usando la configuración de delivery
                delivery_config = self.pipeline_config.get("DELIVERY_CONFIG", {})
                date_str = delivery_config.get("date_today", "20250617")
                delivery_code = delivery_config.get("delivery_code", "d01")
                base_prefix = delivery_config.get("base_prefix", "")
                custom_suffix = delivery_config.get("custom_suffix", "")
                
                # Construir nombre base
                name_parts = []
                if base_prefix:
                    name_parts.append(base_prefix)
                if delivery_code:
                    name_parts.append(delivery_code.upper())
                
                base_name = "_".join(name_parts) if name_parts else "E02"
                if custom_suffix:
                    base_name += custom_suffix
                
                final_file_path = os.path.join(output_dir, "results", f"{date_str}_{base_name}_PARCELAS_FINALES.gpkg")
                
                # Enviar la ruta al tab de column order
                self.column_order_tab.set_pipeline_output_path(final_file_path)
                self.log_text.append(f"[INFO] Set pipeline output path for column ordering: {final_file_path}")
            else:
                self.log_text.append("[WARNING] No output directory configured in pipeline.")
                QMessageBox.warning(self, "Warning", "Please configure an output directory in the Pipeline tab first.")
        else:
            self.pipeline_config['COLUMN_ORDER_CONFIG'] = column_order_config
            self.log_text.append(f"[INFO] Column order configuration updated.")

    def _run_pipeline(self):
        full_config = self._get_full_pipeline_config()
        if not full_config.get("input_path") or not os.path.exists(full_config.get("input_path")):
            QMessageBox.warning(self, "Input Error", "Please select a valid input file.")
            return
        if not full_config.get("output_dir"):
            QMessageBox.warning(self, "Output Error", "Please select an output directory.")
            return
        
        try:
            # Crear archivo temporal para el pipeline
            json_config_dir = os.path.join(os.path.dirname(__file__), "..", "json_config")
            os.makedirs(json_config_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json", dir=json_config_dir, encoding="utf-8") as tmp:
                json.dump(full_config, tmp, indent=4)
                self._last_temp_config_path = tmp.name
                
        except Exception as e:
            QMessageBox.critical(self, "Config Error", f"Failed to create temporary config file: {e}")
            return
        
        self.log_text.append(f"[INFO] Starting enhanced pipeline with config: {self._last_temp_config_path}")
        self._set_running_state(is_running=True)
        
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

    def _set_running_state(self, is_running: bool):
        """Actualiza el estado de los controles de ejecución."""
        # Controles principales
        self.main_run_btn.setEnabled(not is_running)
        self.main_stop_btn.setEnabled(is_running)
        self.main_progress_bar.setVisible(is_running)
        if not is_running:
            self.main_progress_bar.setValue(0)
        
        # Controles del pipeline tab (mantener compatibilidad)
        self.pipeline_tab.set_running_state(is_running)

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
                
                try:
                    # Intentar terminación suave primero
                    self.process.terminate()
                    
                    # Esperar hasta 3 segundos para terminación suave
                    if not self.process.waitForFinished(3000):
                        self.log_text.append("[INFO] Process did not terminate gracefully, forcing termination...")
                        self.process.kill()
                        self.process.waitForFinished(1000)
                    
                    self.log_text.append("[INFO] Process terminated successfully")
                    
                except Exception as e:
                    self.log_text.append(f"[WARNING] Error during process termination: {e}")
                    # Forzar limpieza del proceso
                    self.process = None
                    self._set_running_state(is_running=False)

    def _on_process_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        log_level = self.config_tab.findChild(QComboBox, "log_level_combo").currentText()
        
        for line in data.strip().splitlines():
            try:
                msg = json.loads(line)
                msg_type = msg.get("type", "").lower()
                if msg_type == "progress":
                    progress_value = msg.get("value", 0)
                    self.main_progress_bar.setValue(progress_value)
                    self.pipeline_tab.update_progress(progress_value)
                    self.log_text.append(f"[PROGRESS] {progress_value}% - {msg.get('status', '')}")
                elif msg_type == "log":
                    level = msg.get('level', 'info').upper()
                    message = msg.get('message', '')
                    
                    # Filtrar logs según el nivel seleccionado
                    if log_level == "INFO":
                        # Solo mostrar INFO, WARNING, ERROR en modo INFO
                        if level in ["INFO", "WARNING", "ERROR"]:
                            # Filtrar mensajes muy técnicos incluso en INFO
                            if not any(skip_phrase in message.lower() for skip_phrase in [
                                "columnas disponibles:", "primeras 3 filas", "resultado del merge:",
                                "columnas extra del csv eliminadas", "harmonizando tipos",
                                "performing spatial join", "columns after join", "renamed columns",
                                "final columns after cleanup", "parcels before join", "parcels after join",
                                "field '", "': ", "non-null values", "dropped columns"
                            ]):
                                self.log_text.append(f"[{level}] {message}")
                    else:
                        # Mostrar todos los logs en modo DEBUG
                        self.log_text.append(f"[{level}] {message}")
                elif msg_type == "success":
                    self.main_progress_bar.setValue(100)
                    self.pipeline_tab.update_progress(100)
                    self.log_text.append(f"[SUCCESS] {msg.get('message', 'Process completed successfully.')}")
                    QMessageBox.information(self, "Success", msg.get("message", "Process completed successfully."))
                elif msg_type == "error":
                    error_msg = msg.get('message', 'An unknown error occurred.')
                    traceback_info = "\n".join(msg.get('traceback_lines', []))
                    full_error = f"{error_msg}\n\nTraceback:\n{traceback_info}"
                    self.log_text.append(f"[ERROR] {full_error}")
                    QMessageBox.critical(self, "Pipeline Error", full_error)
                else:
                    # Solo mostrar logs de proceso no-JSON en modo DEBUG
                    if log_level == "DEBUG":
                        self.log_text.append(f"[PROCESS] {line}")
            except json.JSONDecodeError:
                # Solo mostrar logs de proceso no-JSON en modo DEBUG
                if log_level == "DEBUG":
                    self.log_text.append(f"[PROCESS] {line}")

    def _on_process_stderr(self):
        error_data = self.process.readAllStandardError().data().decode("utf-8", errors="replace").strip()
        if error_data:
            self.log_text.append(f"[STDERR] {error_data}")
        
    def _on_process_finished(self):
        exit_code = self.process.exitCode()
        exit_status = self.process.exitStatus()
        self.log_text.append(f"[INFO] Process finished. Exit code: {exit_code}, Status: {exit_status.name}")
        
        # Limpiar conexiones de señales antes de procesar
        if self.process:
            self.process.readyReadStandardOutput.disconnect()
            self.process.readyReadStandardError.disconnect()
            self.process.finished.disconnect()
        
        self._set_running_state(is_running=False)
        
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
        
        # Manejar archivo temporal
        if self._last_temp_config_path and os.path.exists(self._last_temp_config_path):
            try:
                # Copiar archivo temporal al directorio de salida antes de eliminarlo
                pipeline_config = self._get_full_pipeline_config()
                output_dir = pipeline_config.get("output_dir")
                if output_dir and os.path.exists(output_dir):
                    # Crear directorio de configuraciones si no existe
                    config_history_dir = os.path.join(output_dir, "config")
                    os.makedirs(config_history_dir, exist_ok=True)
                    
                    # Generar nombre descriptivo para el archivo de configuración
                    temp_filename = os.path.basename(self._last_temp_config_path)
                    delivery_config = self.pipeline_config.get("DELIVERY_CONFIG", {})
                    date_str = delivery_config.get("date_today", "")
                    delivery_code = delivery_config.get("delivery_code", "")
                    
                    if date_str and delivery_code:
                        config_filename = f"{date_str}_{delivery_code.upper()}_pipeline_config_executed.json"
                    else:
                        config_filename = f"pipeline_config_executed_{temp_filename}"
                    
                    config_dest_path = os.path.join(config_history_dir, config_filename)
                    
                    # Copiar archivo temporal al directorio de salida
                    import shutil
                    shutil.copy2(self._last_temp_config_path, config_dest_path)
                    self.log_text.append(f"[INFO] Configuration saved to output directory: {config_dest_path}")
                
                # Ahora eliminar el archivo temporal
                os.remove(self._last_temp_config_path)
                self.log_text.append(f"[INFO] Removed temporary config: {self._last_temp_config_path}")
                self._last_temp_config_path = None
            except Exception as e:
                self.log_text.append(f"[WARNING] Could not process temp file: {e}")
        
        # Limpiar proceso de forma robusta
        if self.process:
            try:
                # Esperar a que el proceso termine completamente
                if self.process.state() != QProcess.ProcessState.NotRunning:
                    self.process.waitForFinished(1000)  # Esperar máximo 1 segundo
                
                # Cerrar canales de comunicación
                self.process.closeReadChannel(QProcess.ProcessChannel.StandardOutput)
                self.process.closeReadChannel(QProcess.ProcessChannel.StandardError)
                
                # Eliminar referencia al proceso
                self.process.deleteLater()
                self.process = None
                
            except Exception as e:
                self.log_text.append(f"[DEBUG] Process cleanup warning: {e}")
                self.process = None

    # --- SETTINGS & CONFIG MANAGEMENT ---

    def _get_full_pipeline_config(self) -> Dict[str, Any]:
        """Genera la configuración completa del pipeline incluyendo las nuevas funcionalidades."""
        base_config = self.pipeline_tab.get_config()
        sampling_config = self.sampling_tab.get_config()
        
        # Configuración base
        full_config = {
            "input_path": base_config.get("input_path"),
            "output_dir": base_config.get("output_dir"),
            "style": base_config.get("style"),
            "use_csv": sampling_config.get("use_csv", False),
            "csv_path": sampling_config.get("csv_path"),
            "grouping_fields": base_config.get("grouping_fields"),
            "entrega": None,
            "cfg_overrides": base_config.get("cfg_overrides", {})
        }
        
        # Agregar configuraciones de muestreo
        if sampling_config.get("use_csv"):
            full_config["count_column_csv"] = sampling_config.get("count_column_csv")
            full_config["field_mappings"] = sampling_config.get("field_mappings", [])
            
            # NUEVO: Agregar configuración de gridcode del CSV
            gridcode_column_csv = sampling_config.get("gridcode_column_csv")
            if gridcode_column_csv:
                full_config["gridcode_column_csv"] = gridcode_column_csv
        
        # Agregar configuración de intensidad al cfg_overrides
        full_config["cfg_overrides"]["INTENSIDAD"] = sampling_config.get("base_intensity", 80)
        full_config["cfg_overrides"]["USE_INTENSIDAD_ESPECIFICA"] = sampling_config.get("use_specific_intensity", False)
        full_config["cfg_overrides"]["INTENSIDAD_POR_CAMPO"] = sampling_config.get("specific_intensities", {})
        
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
                pipeline_config["gridcode_column_csv"] = config.get("gridcode_column_csv")
            
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
            
            # NUEVOS
            column_order_config = config.get("column_order_config", {})
            
            # Aplicar configuraciones
            self.pipeline_tab.set_config(pipeline_config)
            self.po_tab.set_config(po_config)
            self.exclusion_tab.set_config(exclusion_config)
            self.gridcode_tab.set_config(gridcode_config)
            self.delivery_tab.set_config(delivery_config)
            self.column_order_tab.set_config(column_order_config)
            
            self.log_text.append(f"[SUCCESS] Enhanced configuration successfully imported from: {file_path}")
            QMessageBox.information(self, "Import Successful", f"Configuration loaded from:\n{file_path}")
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_message = f"Failed to import configuration from {os.path.basename(file_path)}."
            self.log_text.append(f"[ERROR] {error_message}\nDetails: {e}")
            QMessageBox.critical(self, "Import Error", f"{error_message}\n\nPlease check the file format.\n\nError: {e}")

    def _save_gui_settings(self) -> None:
        """Guarda todas las configuraciones de la GUI incluyendo las nuevas."""
        pipeline_settings = self.pipeline_tab.get_config()
        sampling_settings = self.sampling_tab.get_config()
        
        full_settings = {
            "input_path": pipeline_settings.get("input_path"),
            "output_dir": pipeline_settings.get("output_dir"),
            "style": pipeline_settings.get("style"),
            "grouping_fields": pipeline_settings.get("grouping_fields", []),
            "cfg_overrides": pipeline_settings.get("cfg_overrides", {}),
            "po_config": self.po_tab.get_config(),
            "exclusion_list": self.exclusion_tab.get_config(),
            "gridcode_config": self.gridcode_tab.get_config(),
            "delivery_config": self.delivery_tab.get_config(),
            "column_order_config": self.column_order_tab.get_config(),
            "sampling_config": sampling_settings
        }
        
        # Agregar configuración de muestreo directamente al nivel superior para compatibilidad
        full_settings["use_csv"] = sampling_settings.get("use_csv", False)
        full_settings["csv_path"] = sampling_settings.get("csv_path")
        full_settings["count_column_csv"] = sampling_settings.get("count_column_csv")
        full_settings["gridcode_column_csv"] = sampling_settings.get("gridcode_column_csv")
        full_settings["field_mappings"] = sampling_settings.get("field_mappings", [])
        
        # Configuración de intensidad (campos individuales para compatibilidad)
        full_settings["base_intensity"] = sampling_settings.get("base_intensity", 12)
        full_settings["use_specific_intensity"] = sampling_settings.get("use_specific_intensity", False)
        full_settings["specific_intensities"] = sampling_settings.get("specific_intensities", {})
        
        # Configuración legacy
        full_settings["custom_params"] = {
            "intensity": sampling_settings.get("base_intensity", 12)
        }
        
        save_gui_settings(full_settings)
        self.log_text.append("[INFO] Enhanced GUI settings saved successfully.")

    def _restore_gui_settings(self) -> None:
        """Carga configuraciones incluyendo las nuevas funcionalidades."""
        settings = load_gui_settings()

        pipeline_config = {
            "input_path": settings.get("input_path"),
            "output_dir": settings.get("output_dir"),
            "style": settings.get("style"),
            "grouping_fields": settings.get("grouping_fields", []),
            "cfg_overrides": settings.get("cfg_overrides", {})
        }
        
        # Configuración de muestreo (puede venir del nuevo formato o del legacy)
        sampling_config = settings.get("sampling_config", {})
        if not sampling_config:
            # Formato legacy o campos individuales - migrar desde configuración antigua
            custom_params = settings.get("custom_params", {})
            sampling_config = {
                "use_csv": settings.get("use_csv", False),
                "csv_path": settings.get("csv_path"),
                "base_intensity": settings.get("base_intensity", custom_params.get("intensity", 12)),
                "use_specific_intensity": settings.get("use_specific_intensity", False),
                "specific_intensities": settings.get("specific_intensities", {}),
                "count_column_csv": settings.get("count_column_csv"),
                "gridcode_column_csv": settings.get("gridcode_column_csv"),
                "field_mappings": settings.get("field_mappings", [])
            }
        
        po_config = settings.get("po_config", {})
        exclusion_config = settings.get("exclusion_list", [])
        
        # NUEVOS
        gridcode_config = settings.get("gridcode_config", {"enabled": False})
        delivery_config = settings.get("delivery_config", {})
        column_order_config = settings.get("column_order_config", {})

        self.pipeline_tab.set_config(pipeline_config)
        self.sampling_tab.set_config(sampling_config)
        self.po_tab.set_config(po_config)
        self.exclusion_tab.set_config(exclusion_config)
        self.gridcode_tab.set_config(gridcode_config)
        self.delivery_tab.set_config(delivery_config)
        self.column_order_tab.set_config(column_order_config)
        
        self._on_po_config_changed(self.po_tab.get_config())
        self._on_exclusions_changed(self.exclusion_tab.get_config())
        self._on_sampling_config_changed(self.sampling_tab.get_config())
        self._on_gridcode_config_changed(self.gridcode_tab.get_config())
        self._on_delivery_config_changed(self.delivery_tab.get_config())
        
        self.log_text.append("[INFO] Enhanced GUI settings loaded successfully.")

    def _cleanup_temp_files(self) -> None:
        """Clean up all temporary configuration files."""
        # Clean specific temp file
        if self._last_temp_config_path and os.path.exists(self._last_temp_config_path):
            try:
                # Copiar archivo temporal al directorio de salida antes de eliminarlo
                pipeline_config = self._get_full_pipeline_config()
                output_dir = pipeline_config.get("output_dir")
                if output_dir and os.path.exists(output_dir):
                    # Crear directorio de configuraciones si no existe
                    config_history_dir = os.path.join(output_dir, "config")
                    os.makedirs(config_history_dir, exist_ok=True)
                    
                    # Generar nombre descriptivo para el archivo de configuración
                    temp_filename = os.path.basename(self._last_temp_config_path)
                    delivery_config = self.pipeline_config.get("DELIVERY_CONFIG", {})
                    date_str = delivery_config.get("date_today", "")
                    delivery_code = delivery_config.get("delivery_code", "")
                    
                    if date_str and delivery_code:
                        config_filename = f"{date_str}_{delivery_code.upper()}_pipeline_config_cleanup.json"
                    else:
                        config_filename = f"pipeline_config_cleanup_{temp_filename}"
                    
                    config_dest_path = os.path.join(config_history_dir, config_filename)
                    
                    # Copiar archivo temporal al directorio de salida
                    import shutil
                    shutil.copy2(self._last_temp_config_path, config_dest_path)
                    self.log_text.append(f"[INFO] Configuration saved during cleanup: {config_dest_path}")
                
                # Ahora eliminar el archivo temporal
                os.remove(self._last_temp_config_path)
                self.log_text.append(f"[INFO] Removed temporary config: {self._last_temp_config_path}")
                self._last_temp_config_path = None
            except Exception as e:
                self.log_text.append(f"[WARNING] Could not process temp file: {e}")
        
        # Clean up any orphaned temp files in json_config directory
        json_config_dir = os.path.join(os.path.dirname(__file__), "..", "json_config")
        if os.path.exists(json_config_dir):
            try:
                import glob
                temp_files = glob.glob(os.path.join(json_config_dir, "tmp*.json"))
                for temp_file in temp_files:
                    try:
                        # Intentar copiar archivos huérfanos también si hay un directorio de salida válido
                        try:
                            pipeline_config = self._get_full_pipeline_config()
                            output_dir = pipeline_config.get("output_dir")
                            if output_dir and os.path.exists(output_dir):
                                config_history_dir = os.path.join(output_dir, "config")
                                os.makedirs(config_history_dir, exist_ok=True)
                                
                                temp_filename = os.path.basename(temp_file)
                                config_dest_path = os.path.join(config_history_dir, f"orphaned_{temp_filename}")
                                
                                import shutil
                                shutil.copy2(temp_file, config_dest_path)
                                self.log_text.append(f"[INFO] Orphaned config saved: {config_dest_path}")
                        except Exception:
                            pass  # Si no se puede copiar, solo eliminar
                        
                        os.remove(temp_file)
                        self.log_text.append(f"[INFO] Cleaned up orphaned temp file: {os.path.basename(temp_file)}")
                    except Exception as e:
                        self.log_text.append(f"[WARNING] Could not remove orphaned temp file {temp_file}: {e}")
            except Exception as e:
                self.log_text.append(f"[WARNING] Error during temp files cleanup: {e}")

    def closeEvent(self, event):
        """Clean up resources before closing."""
        try:
            if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
                reply = QMessageBox.question(
                    self, 'Process Still Running', 
                    "A pipeline process is still running. Are you sure you want to close? The process will be terminated.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    # Terminación robusta del proceso
                    try:
                        if self.process:
                            self.process.terminate()
                            if not self.process.waitForFinished(2000):
                                self.process.kill()
                                self.process.waitForFinished(1000)
                    except Exception as e:
                        self.log_text.append(f"[DEBUG] Process termination during close: {e}")
                    
                    self._cleanup_temp_files()
                    self._save_gui_settings()
                    event.accept()
                else:
                    event.ignore()
                    return
            else:
                self._cleanup_temp_files()
                self._save_gui_settings()
                event.accept()
            
            # Limpieza final de recursos
            if self.process:
                try:
                    self.process.deleteLater()
                    self.process = None
                except Exception:
                    pass
                    
        except Exception as e:
            # En caso de error, aceptar el cierre de todas formas
            self.log_text.append(f"[DEBUG] Error during application close: {e}")
            event.accept()