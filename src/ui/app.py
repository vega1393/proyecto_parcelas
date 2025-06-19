# src/ui/app.py

import os
import sys
import json
import tempfile
import shutil
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
from src.utils.dialog_utils import EnhancedFileDialog

class ParcelGeneratorApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Parcel Generator - Enhanced")
        self.setMinimumSize(800, 600)  # Aumentado para acomodar nuevos tabs

        self.process: Optional[QProcess] = None
        self._last_temp_config_path: Optional[str] = None
        self.pipeline_config: Dict[str, Any] = {}
        
        # Configuración de logging UI (por defecto INFO)
        self.ui_log_level = "INFO"

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
        
        # Initialize all tabs
        self.pipeline_tab = PipelineTab()
        self.sampling_tab = SamplingTab()
        self.po_tab = POTab()
        self.exclusion_tab = ExclusionTab()
        self.config_tab = ConfigTab()
        self.gridcode_tab = GridCodeTab()
        self.delivery_tab = DeliveryTab()
        self.column_order_tab = ColumnOrderTab()
        self.help_tab = HelpTab()
        
        # Add tabs in logical order
        tabs.addTab(self.pipeline_tab, "Pipeline")
        tabs.addTab(self.sampling_tab, "Sampling Method")
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
        
        # Additional signals
        self.sampling_tab.configChanged.connect(self._on_sampling_config_changed)
        self.gridcode_tab.configChanged.connect(self._on_gridcode_config_changed)
        self.delivery_tab.configChanged.connect(self._on_delivery_config_changed)
        self.column_order_tab.configChanged.connect(self._on_column_order_config_changed)
        
        # Señales de configuración
        self.config_tab.findChild(QPushButton, "export_config_btn").clicked.connect(self._export_config)
        self.config_tab.findChild(QPushButton, "import_config_btn").clicked.connect(self._import_config)
        self.config_tab.findChild(QPushButton, "save_settings_btn").clicked.connect(self._save_gui_settings)
        self.config_tab.findChild(QPushButton, "load_settings_btn").clicked.connect(self._restore_gui_settings)
        
        # Conectar señal del combo de log level
        log_level_combo = self.config_tab.findChild(QComboBox, "log_level_combo")
        if log_level_combo:
            log_level_combo.currentTextChanged.connect(self._on_log_level_changed)

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
        """Execute the pipeline with robust signal handling."""
        try:
            if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
                QMessageBox.warning(self, "Warning", "Pipeline is already running.")
                return

            pipeline_config = self._get_full_pipeline_config()
            
            if not pipeline_config.get("input_path") or not pipeline_config.get("output_dir"):
                QMessageBox.warning(self, "Configuration Error", 
                                  "Please specify both input file and output directory.")
                return

            # Crear archivo temporal de configuración
            import tempfile
            fd, temp_config_path = tempfile.mkstemp(suffix=".json", prefix="tmp", 
                                                   dir=os.path.join(os.path.dirname(__file__), "..", "json_config"))
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
                    json.dump(pipeline_config, tmp, indent=2, ensure_ascii=False)
                
                self._last_temp_config_path = temp_config_path
                self.log_text.append(f"[INFO] Starting enhanced pipeline with config: {temp_config_path}")
                
                # Crear proceso con configuración robusta
                try:
                    if self.process:
                        # Limpiar proceso anterior si existe
                        try:
                            self.process.finished.disconnect()
                            self.process.readyReadStandardOutput.disconnect()
                            self.process.readyReadStandardError.disconnect()
                        except Exception:
                            pass
                        self.process.deleteLater()
                        self.process = None
                        
                    self.process = QProcess(self)
                    
                    # Conectar señales de forma segura
                    try:
                        self.process.readyReadStandardOutput.connect(self._on_process_stdout)
                        self.process.readyReadStandardError.connect(self._on_process_stderr)
                        self.process.finished.connect(self._on_process_finished)
                    except Exception as e:
                        self.log_text.append(f"[ERROR] Error connecting process signals: {e}")
                        return
                    
                    # Configurar entorno
                    env = QProcessEnvironment.systemEnvironment()
                    env.insert("PYTHONPATH", os.pathsep.join(sys.path))
                    
                    # Configurar el nivel de logging para el proceso hijo
                    if self.ui_log_level == "DEBUG":
                        env.insert("PIPELINE_LOG_LEVEL", "DEBUG")
                    else:
                        env.insert("PIPELINE_LOG_LEVEL", "INFO")
                    
                    self.process.setProcessEnvironment(env)
                    
                    # Ejecutar
                    script_path = os.path.join(os.path.dirname(__file__), "..", "run_pipeline.py")
                    self.process.start(sys.executable, [script_path, temp_config_path])
                    
                    if not self.process.waitForStarted(5000):
                        raise Exception("Process failed to start within 5 seconds")
                    
                    self._set_running_state(is_running=True)
                    
                except Exception as e:
                    self.log_text.append(f"[ERROR] Failed to start pipeline process: {e}")
                    QMessageBox.critical(self, "Process Error", f"Failed to start pipeline:\n{e}")
                    self._set_running_state(is_running=False)
                    if self.process:
                        self.process.deleteLater()
                        self.process = None
                    return
                    
            except Exception as e:
                self.log_text.append(f"[ERROR] Failed to create temporary config: {e}")
                QMessageBox.critical(self, "Configuration Error", f"Failed to prepare pipeline configuration:\n{e}")
                try:
                    os.close(fd)
                    if os.path.exists(temp_config_path):
                        os.remove(temp_config_path)
                except Exception:
                    pass
                return
                
        except Exception as e:
            self.log_text.append(f"[ERROR] Critical error in _run_pipeline: {e}")
            QMessageBox.critical(self, "Critical Error", f"An unexpected error occurred:\n{e}")
            self._set_running_state(is_running=False)

    def _set_running_state(self, is_running: bool):
        """Updates UI state when pipeline is running/stopped with error protection."""
        try:
            # Actualizar controles principales
            try:
                self.main_run_btn.setEnabled(not is_running)
                self.main_stop_btn.setEnabled(is_running)
            except Exception as e:
                self._log_message(f"Error updating main buttons: {e}", "DEBUG")
            
            try:
                self.main_progress_bar.setVisible(is_running)
                if not is_running:
                    self.main_progress_bar.setValue(0)
            except Exception as e:
                self._log_message(f"Error updating progress bar: {e}", "DEBUG")
            
            # Actualizar controles del pipeline tab
            try:
                if hasattr(self.pipeline_tab, 'set_running_state'):
                    self.pipeline_tab.set_running_state(is_running)
            except Exception as e:
                self._log_message(f"Error updating pipeline tab state: {e}", "DEBUG")
                
        except Exception as e:
            self.log_text.append(f"[ERROR] Critical error in _set_running_state: {e}")
            # Intentar al menos actualizar los botones principales
            try:
                if hasattr(self, 'main_run_btn'):
                    self.main_run_btn.setEnabled(not is_running)
                if hasattr(self, 'main_stop_btn'):
                    self.main_stop_btn.setEnabled(is_running)
            except Exception:
                pass  # Si falla todo, al menos no crashear

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
        """Handles process stdout with robust error protection and intelligent filtering."""
        try:
            if not self.process:
                return
                
            try:
                data = self.process.readAllStandardOutput()
                text = data.data().decode('utf-8', errors='replace')  # Usar 'replace' para evitar errores de decodificación
            except Exception as e:
                self._log_message(f"Error reading stdout: {e}", "DEBUG")
                return
            
            if not text.strip():
                return
                
            try:
                lines = text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Procesar líneas JSON del pipeline de forma inteligente
                    try:
                        if line.startswith('{"type":'):
                            # Parsear línea JSON del pipeline
                            import json
                            try:
                                json_data = json.loads(line)
                                json_type = json_data.get("type", "")
                                
                                if json_type == "progress":
                                    # Actualizar barra de progreso
                                    value = json_data.get("value", 0)
                                    status = json_data.get("status", "")
                                    if 0 <= value <= 100:
                                        self.main_progress_bar.setValue(value)
                                    # Solo mostrar progreso importantes o cada 10%
                                    if value % 10 == 0 or value >= 95:
                                        self._log_message(f"Progreso: {value}% - {status}", "INFO")
                                
                                elif json_type == "log":
                                    # Procesar mensajes de log del pipeline
                                    level = json_data.get("level", "info").upper()
                                    message = json_data.get("message", "")
                                    logger = json_data.get("logger", "")
                                    
                                    # Filtrar mensajes muy verbosos
                                    if any(skip_phrase in message for skip_phrase in [
                                        "Created ", " records",  # pyogrio messages
                                        "GridCode ", ": ", " registros",  # Detailed gridcode stats
                                        "Registros antes de filtrar",
                                        "Registros después de filtrar"
                                    ]) and level == "INFO":
                                        # Solo mostrar estos mensajes en modo DEBUG
                                        self._log_message(f"[{logger}] {message}", "DEBUG")
                                    else:
                                        # Mostrar mensajes importantes
                                        if level in ["WARNING", "ERROR", "CRITICAL"]:
                                            self._log_message(f"[{logger}] {message}", level)
                                        else:
                                            self._log_message(f"[{logger}] {message}", "INFO")
                                
                                elif json_type == "success":
                                    # Mensaje de éxito
                                    message = json_data.get("message", "")
                                    self._log_message(f"✓ {message}", "INFO")
                                
                                elif json_type == "error":
                                    # Mensaje de error
                                    message = json_data.get("message", "")
                                    self._log_message(f"✗ {message}", "ERROR")
                                
                                # No añadir la línea JSON cruda al log
                                continue
                                
                            except json.JSONDecodeError:
                                # Si no es JSON válido, procesar como línea normal
                                pass
                    except Exception:
                        # Si hay error procesando JSON, procesar como línea normal
                        pass
                        
                    # Procesar líneas de progreso legacy de forma segura
                    try:
                        if line.startswith('[PROGRESS]'):
                            parts = line.split(' - ', 1)
                            if len(parts) >= 2:
                                progress_part = parts[0].replace('[PROGRESS]', '').strip()
                                if progress_part.endswith('%'):
                                    try:
                                        value = int(progress_part.replace('%', ''))
                                        if 0 <= value <= 100:
                                            self.main_progress_bar.setValue(value)
                                    except (ValueError, AttributeError):
                                        pass  # Ignorar errores de conversión
                    except Exception:
                        pass  # Ignorar errores de procesamiento de progreso
                    
                    # Añadir líneas no-JSON al log de forma segura
                    try:
                        # Filtrar líneas muy técnicas/verbosas
                        if not any(skip_phrase in line for skip_phrase in [
                            '{"type":',  # Ya procesadas arriba
                            'Created ', ' records'  # pyogrio verbose messages
                        ]):
                            self.log_text.append(line)
                    except Exception as e:
                        # Si falla, intentar añadir una versión simplificada
                        try:
                            self.log_text.append(f"[LOG] {str(line)[:200]}")  # Truncar a 200 caracteres
                        except Exception:
                            pass  # Si falla completamente, ignorar esta línea
                            
            except Exception as e:
                self._log_message(f"Error processing stdout lines: {e}", "DEBUG")
                
        except Exception as e:
            # Error crítico en el manejo de stdout
            try:
                self.log_text.append(f"[ERROR] Critical error in stdout handler: {e}")
            except Exception:
                pass  # Si ni siquiera podemos escribir al log, ignorar

    def _on_process_stderr(self):
        error_data = self.process.readAllStandardError().data().decode("utf-8", errors="replace").strip()
        if error_data:
            self.log_text.append(f"[STDERR] {error_data}")
        
    def _on_process_finished(self):
        """Maneja la finalización del proceso con protección robusta contra crashes."""
        try:
            exit_code = self.process.exitCode() if self.process else -1
            exit_status = self.process.exitStatus() if self.process else None
            self.log_text.append(f"[INFO] Process finished. Exit code: {exit_code}, Status: {exit_status.name if exit_status else 'Unknown'}")
            
            # Limpiar conexiones de señales antes de procesar
            try:
                if self.process:
                    # Desconectar señales de forma segura
                    self.process.readyReadStandardOutput.disconnect()
                    self.process.readyReadStandardError.disconnect()
                    self.process.finished.disconnect()
            except Exception as e:
                self._log_message(f"Signal disconnection warning: {e}", "DEBUG")
            
            # Actualizar estado de la interfaz
            try:
                self._set_running_state(is_running=False)
            except Exception as e:
                self._log_message(f"UI state update warning: {e}", "DEBUG")
            
            # Mostrar mensajes de error al usuario solo si hay problemas
            try:
                if exit_code != 0:
                    self._handle_process_error(exit_code)
            except Exception as e:
                self._log_message(f"Error handling warning: {e}", "DEBUG")
            
            # Manejar archivo temporal de forma segura
            try:
                self._handle_temp_config_cleanup()
            except Exception as e:
                self._log_message(f"Temp file cleanup warning: {e}", "DEBUG")
            
            # Limpiar proceso de forma robusta sin usar deleteLater
            try:
                if self.process:
                    # Siempre usar limpieza inmediata para evitar problemas de thread
                    self._cleanup_process_resources()
            except Exception as e:
                self._log_message(f"Process cleanup warning: {e}", "DEBUG")
                self.process = None
                
        except Exception as e:
            # Captura cualquier error inesperado para evitar crashes
            self.log_text.append(f"[ERROR] Unexpected error in process finished handler: {e}")
            try:
                self._set_running_state(is_running=False)
                self._cleanup_process_resources()
            except Exception as cleanup_error:
                self.log_text.append(f"[ERROR] Critical cleanup error: {cleanup_error}")
                # Forzar limpieza mínima
                self.process = None
                self.main_run_btn.setEnabled(True)
                self.main_stop_btn.setEnabled(False)
                self.main_progress_bar.setVisible(False)
    
    def _handle_process_error(self, exit_code: int) -> None:
        """Maneja errores del proceso mostrando mensajes apropiados al usuario."""
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
    
    def _handle_temp_config_cleanup(self) -> None:
        """Maneja la limpieza del archivo temporal de configuración."""
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
    
    def _cleanup_process_resources(self) -> None:
        """Limpia recursos del proceso de forma robusta sin usar deleteLater."""
        if self.process:
            try:
                # Esperar a que el proceso termine completamente
                if self.process.state() != QProcess.ProcessState.NotRunning:
                    if not self.process.waitForFinished(1000):  # Esperar máximo 1 segundo
                        self._log_message("Process did not finish gracefully, forcing cleanup", "DEBUG")
                
                # Cerrar canales de comunicación de forma segura
                try:
                    self.process.closeReadChannel(QProcess.ProcessChannel.StandardOutput)
                    self.process.closeReadChannel(QProcess.ProcessChannel.StandardError)
                except Exception:
                    pass  # Ignorar errores de cierre de canales
                
                # Desconectar todas las señales antes de eliminar
                try:
                    self.process.finished.disconnect()
                    self.process.readyReadStandardOutput.disconnect()
                    self.process.readyReadStandardError.disconnect()
                except Exception:
                    pass  # Ignorar si las señales ya fueron desconectadas
                
                # Limpiar el proceso sin usar deleteLater para evitar problemas de thread
                try:
                    if self.process.state() != QProcess.ProcessState.NotRunning:
                        # Si aún está ejecutándose, forzar terminación
                        self.process.kill()
                        self.process.waitForFinished(500)
                    
                    # Limpieza inmediata sin deleteLater
                    self.process = None
                    self._log_message("Process resources cleaned up successfully", "DEBUG")
                    
                except Exception as e:
                    self._log_message(f"Process cleanup error: {e}", "DEBUG")
                    # Forzar limpieza inmediata
                    self.process = None
                
            except Exception as e:
                self._log_message(f"Process cleanup error: {e}", "DEBUG")
                # Forzar limpieza inmediata en caso de error
                self.process = None

    # --- SETTINGS & CONFIG MANAGEMENT ---

    def _get_full_pipeline_config(self) -> Dict[str, Any]:
        """Genera la configuración completa del pipeline."""
        # Configuración base del pipeline
        pipeline_config = self.pipeline_tab.get_config()
        
        # Configuraciones adicionales
        po_config = self.po_tab.get_config()
        exclusion_config = self.exclusion_tab.get_config()
        sampling_config = self.sampling_tab.get_config()
        gridcode_config = self.gridcode_tab.get_config()
        delivery_config = self.delivery_tab.get_config()
        column_order_config = self.column_order_tab.get_config()
        
        # Construir cfg_overrides con todas las configuraciones
        cfg_overrides = pipeline_config.get("cfg_overrides", {}).copy()
        
        # Agregar configuración de PO si está disponible
        if po_config:
            cfg_overrides["PO_CONFIG"] = po_config
        
        # Agregar configuración de exclusiones (siempre, aunque esté vacía)
        cfg_overrides["CAPAS_EXCLUSION"] = exclusion_config
        
        # Agregar configuración de muestreo
        if sampling_config.get("use_csv"):
            cfg_overrides["count_column_csv"] = sampling_config.get("count_column_csv")
            cfg_overrides["field_mappings"] = sampling_config.get("field_mappings", [])
            gridcode_column_csv = sampling_config.get("gridcode_column_csv")
            if gridcode_column_csv:
                cfg_overrides["gridcode_column_csv"] = gridcode_column_csv
        
        # Agregar configuración de intensidad
        cfg_overrides["INTENSIDAD"] = sampling_config.get("base_intensity", 80)
        cfg_overrides["USE_INTENSIDAD_ESPECIFICA"] = sampling_config.get("use_specific_intensity", False)
        cfg_overrides["INTENSIDAD_POR_CAMPO"] = sampling_config.get("specific_intensities", {})
        
        # Agregar configuración de GridCode
        if gridcode_config.get("enabled"):
            cfg_overrides["USE_GRIDCODE"] = True
            cfg_overrides["GRIDCODE_PARAMS"] = gridcode_config.get("gridcode_params", {})
            
            # Auto-incluir 'gridcode' en campos de agrupación cuando GridCode está habilitado
            grouping_fields = list(pipeline_config.get("grouping_fields", []))
            if "gridcode" not in grouping_fields:
                grouping_fields.append("gridcode")
                pipeline_config["grouping_fields"] = grouping_fields
                self._log_message("GridCode enabled: automatically added 'gridcode' to grouping fields", "INFO")
        else:
            # Remover 'gridcode' de campos de agrupación cuando GridCode está deshabilitado
            grouping_fields = list(pipeline_config.get("grouping_fields", []))
            if "gridcode" in grouping_fields:
                grouping_fields.remove("gridcode")
                pipeline_config["grouping_fields"] = grouping_fields
                self._log_message("GridCode disabled: automatically removed 'gridcode' from grouping fields", "INFO")
        
        # Configuración completa
        full_config = {
            # Configuración básica
            "input_path": pipeline_config.get("input_path"),
            "output_dir": pipeline_config.get("output_dir"),
            "style": pipeline_config.get("style", "calibration"),
            "estilo": pipeline_config.get("style", "calibration"),  # Compatibilidad
            "grouping_fields": pipeline_config.get("grouping_fields", []),
            "cfg_overrides": cfg_overrides,
            
            # Configuración de muestreo para compatibilidad
            "use_csv": sampling_config.get("use_csv", False),
            "csv_path": sampling_config.get("csv_path"),
            "count_column_csv": sampling_config.get("count_column_csv"),
            "gridcode_column_csv": sampling_config.get("gridcode_column_csv"),
            "field_mappings": sampling_config.get("field_mappings", []),
            
            # Configuración de entrega
            "delivery_config": delivery_config,
            "delivery_code": delivery_config.get("delivery_code"),
            "date_today": delivery_config.get("date_today"),
            "delivery_metadata": delivery_config.get("metadata", {}),
            
            # Metadatos
            "generated_at": datetime.now().isoformat(),
            "version": "enhanced_v1.1"
        }
        
        return full_config

    def _export_config(self):
        config_to_export = self._get_full_pipeline_config()
        file_path, _ = EnhancedFileDialog.get_save_file_name(
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
        file_path, _ = EnhancedFileDialog.get_open_file_name(
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
            
            # Actualizar configuraciones internas
            self._on_po_config_changed(self.po_tab.get_config())
            self._on_exclusions_changed(self.exclusion_tab.get_config())
            self._on_sampling_config_changed(self.sampling_tab.get_config())
            self._on_gridcode_config_changed(self.gridcode_tab.get_config())
            self._on_delivery_config_changed(self.delivery_tab.get_config())
            
            self.log_text.append(f"[SUCCESS] Enhanced configuration successfully imported from: {file_path}")
            QMessageBox.information(self, "Import Successful", f"Configuration loaded from:\n{file_path}")
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_message = f"Failed to import configuration from {os.path.basename(file_path)}."
            self.log_text.append(f"[ERROR] {error_message}\nDetails: {e}")
            QMessageBox.critical(self, "Import Error", f"{error_message}\n\nPlease check the file format.\n\nError: {e}")

    def _save_gui_settings(self) -> None:
        """Guarda la configuración actual de la GUI en un archivo JSON."""
        try:
            settings = {
                "pipeline_config": self.pipeline_tab.get_config(),
                "sampling_config": self.sampling_tab.get_config(),
                "po_config": self.po_tab.get_config(),
                "exclusion_config": self.exclusion_tab.get_config(),
                "gridcode_config": self.gridcode_tab.get_config(),
                "delivery_config": self.delivery_tab.get_config(),
                "column_order_config": self.column_order_tab.get_config(),
                "ui_log_level": self.ui_log_level  # Guardar nivel de logging
            }
            
            save_gui_settings(settings)
            self.log_text.append("[SUCCESS] GUI settings saved successfully.")
            
        except Exception as e:
            self.log_text.append(f"[ERROR] Failed to save GUI settings: {e}")

    def _restore_gui_settings(self) -> None:
        """Restaura la configuración de la GUI desde el archivo JSON."""
        try:
            settings = load_gui_settings()
            if not settings:
                self.log_text.append("[INFO] No saved GUI settings found, using defaults.")
                return

            # Extraer configuraciones individuales con valores por defecto
            pipeline_config = settings.get("pipeline_config", {})
            sampling_config = settings.get("sampling_config", {})
            po_config = settings.get("po_config", {})
            exclusion_config = settings.get("exclusion_config", {})
            gridcode_config = settings.get("gridcode_config", {})
            delivery_config = settings.get("delivery_config", {})
            column_order_config = settings.get("column_order_config", {})
            
            # Restaurar nivel de logging
            self.ui_log_level = settings.get("ui_log_level", "INFO")
            log_level_combo = self.config_tab.findChild(QComboBox, "log_level_combo")
            if log_level_combo:
                log_level_combo.setCurrentText(self.ui_log_level)

            self.pipeline_tab.set_config(pipeline_config)
            self.sampling_tab.set_config(sampling_config)
            self.po_tab.set_config(po_config)
            self.exclusion_tab.set_config(exclusion_config)
            self.gridcode_tab.set_config(gridcode_config)
            self.delivery_tab.set_config(delivery_config)
            self.column_order_tab.set_config(column_order_config)
            
            # Actualizar configuraciones internas
            self._on_po_config_changed(self.po_tab.get_config())
            self._on_exclusions_changed(self.exclusion_tab.get_config())
            self._on_sampling_config_changed(self.sampling_tab.get_config())
            self._on_gridcode_config_changed(self.gridcode_tab.get_config())
            self._on_delivery_config_changed(self.delivery_tab.get_config())
            
            self.log_text.append("[INFO] Enhanced GUI settings loaded successfully.")
            
        except Exception as e:
            self.log_text.append(f"[ERROR] Failed to restore GUI settings: {e}")

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
        """Clean up resources before closing with robust error handling."""
        try:
            # Verificar si hay proceso ejecutándose
            process_running = False
            try:
                process_running = self.process and self.process.state() != QProcess.ProcessState.NotRunning
            except Exception:
                process_running = False  # Asumir que no está ejecutándose si hay error
            
            if process_running:
                try:
                    reply = QMessageBox.question(
                        self, 'Process Still Running', 
                        "A pipeline process is still running. Are you sure you want to close? The process will be terminated.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        event.ignore()
                        return
                    
                    # Terminación robusta del proceso
                    try:
                        if self.process:
                            self.log_text.append("[INFO] Terminating process before application close...")
                            # Desconectar señales para evitar callbacks durante la terminación
                            try:
                                self.process.finished.disconnect()
                                self.process.readyReadStandardOutput.disconnect()
                                self.process.readyReadStandardError.disconnect()
                            except Exception:
                                pass
                            
                            self.process.terminate()
                            if not self.process.waitForFinished(3000):  # Esperar 3 segundos
                                self.log_text.append("[WARNING] Process did not terminate gracefully, killing...")
                                self.process.kill()
                                self.process.waitForFinished(1000)
                            
                            # Desconectar señales antes de deleteLater
                            try:
                                self.process.finished.disconnect()
                                self.process.readyReadStandardOutput.disconnect()
                                self.process.readyReadStandardError.disconnect()
                            except Exception:
                                pass
                            
                            # Limpieza inmediata sin deleteLater
                            self.process = None
                            self._log_message("Process terminated and cleaned up", "DEBUG")
                            
                    except Exception as e:
                        self._log_message(f"Process termination during close: {e}", "DEBUG")
                        self.process = None
                        
                except Exception as e:
                    self.log_text.append(f"[ERROR] Error handling process termination dialog: {e}")
                    # Continuar con el cierre de todas formas
            
            # Limpiar archivos temporales de forma segura
            try:
                self._cleanup_temp_files()
            except Exception as e:
                self._log_message(f"Temp file cleanup error during close: {e}", "DEBUG")
            
            # Guardar configuración de forma segura
            try:
                self._save_gui_settings()
            except Exception as e:
                self._log_message(f"Settings save error during close: {e}", "DEBUG")
            
            # Limpieza final de recursos
            try:
                if self.process:
                    self.process = None
            except Exception:
                pass
                
            # Aceptar el cierre
            event.accept()
            
        except Exception as e:
            # En caso de error crítico, aceptar el cierre de todas formas para evitar que la app quede colgada
            try:
                self.log_text.append(f"[ERROR] Critical error during application close: {e}")
            except Exception:
                pass  # Si ni siquiera podemos escribir al log, solo cerrar
            
            # Limpieza mínima de emergencia
            try:
                if hasattr(self, 'process') and self.process:
                    self.process.kill()
                    self.process = None
            except Exception:
                pass
                
            event.accept()  # Forzar cierre para evitar que la app quede colgada

    def _on_log_level_changed(self, level: str):
        """Maneja cambios en el nivel de logging de la UI."""
        self.ui_log_level = level
        self._log_message(f"UI log level changed to: {level}", "INFO")

    def _log_message(self, message: str, level: str = "INFO"):
        """
        Añade un mensaje al log respetando el nivel de logging configurado.
        
        Args:
            message: El mensaje a mostrar
            level: Nivel del mensaje (DEBUG, INFO, WARNING, ERROR)
        """
        # Solo mostrar mensajes DEBUG si el nivel está configurado como DEBUG
        if level == "DEBUG" and self.ui_log_level != "DEBUG":
            return
            
        # Formatear el mensaje con el nivel apropiado
        formatted_message = f"[{level}] {message}"
        self.log_text.append(formatted_message)