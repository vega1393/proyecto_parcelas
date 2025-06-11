# src/ui/tab/delivery_tab.py

import os
from datetime import datetime
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QLabel, QScrollArea, QGroupBox, QDateEdit, QComboBox,
    QHBoxLayout, QMessageBox, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, QDate

class DeliveryTab(QWidget):
    """
    Tab para configurar parámetros de entrega como códigos y fechas.
    """
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Inicializa la interfaz de usuario del tab de entrega."""
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QVBoxLayout(content_widget)

        # --- Información de Entrega ---
        delivery_group = QGroupBox("Delivery Information")
        delivery_layout = QFormLayout(delivery_group)
        
        # Código de entrega
        self.delivery_code_line = QLineEdit()
        self.delivery_code_line.setPlaceholderText("e.g., d01, d02, E02_v1")
        self.delivery_code_line.setToolTip("Unique code for this delivery/batch")
        delivery_layout.addRow("Delivery Code:", self.delivery_code_line)
        
        # Fecha de entrega
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setToolTip("Date for this processing run")
        
        # Botón para fecha actual
        date_layout = QHBoxLayout()
        date_layout.addWidget(self.date_edit)
        self.today_btn = QPushButton("Today")
        self.today_btn.clicked.connect(lambda: self.date_edit.setDate(QDate.currentDate()))
        date_layout.addWidget(self.today_btn)
        
        delivery_layout.addRow("Processing Date:", date_layout)
        
        form_layout.addWidget(delivery_group)

        # --- Configuración de Archivos ---
        files_group = QGroupBox("File Naming Configuration")
        files_layout = QFormLayout(files_group)
        
        # Prefijo base
        self.base_prefix_line = QLineEdit()
        self.base_prefix_line.setPlaceholderText("e.g., BRASIL2025, FASA2025")
        self.base_prefix_line.setToolTip("Base prefix for all output files")
        files_layout.addRow("Base Prefix:", self.base_prefix_line)
        
        # Sufijo personalizado
        self.custom_suffix_line = QLineEdit()
        self.custom_suffix_line.setPlaceholderText("e.g., _v1, _final, _test")
        self.custom_suffix_line.setToolTip("Additional suffix for output files")
        files_layout.addRow("Custom Suffix:", self.custom_suffix_line)
        
        form_layout.addWidget(files_group)

        # --- Configuración de Directorios ---
        dirs_group = QGroupBox("Directory Structure")
        dirs_layout = QFormLayout(dirs_group)
        
        # Directorio de resultados
        self.results_subdir_line = QLineEdit()
        self.results_subdir_line.setText("results")
        self.results_subdir_line.setToolTip("Subdirectory name for results")
        dirs_layout.addRow("Results Subdirectory:", self.results_subdir_line)
        
        # Directorio de logs
        self.logs_subdir_line = QLineEdit()
        self.logs_subdir_line.setText("logs")
        self.logs_subdir_line.setToolTip("Subdirectory name for logs")
        dirs_layout.addRow("Logs Subdirectory:", self.logs_subdir_line)
        
        # Directorio de resúmenes
        self.summary_subdir_line = QLineEdit()
        self.summary_subdir_line.setText("summary")
        self.summary_subdir_line.setToolTip("Subdirectory name for summary files")
        dirs_layout.addRow("Summary Subdirectory:", self.summary_subdir_line)
        
        form_layout.addWidget(dirs_group)

        # --- Preview de Nombres ---
        preview_group = QGroupBox("File Naming Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("File naming preview will appear here...")
        preview_layout.addWidget(self.preview_text)
        
        # Botón de actualizar preview
        self.update_preview_btn = QPushButton("Update Preview")
        self.update_preview_btn.clicked.connect(self._update_preview)
        preview_layout.addWidget(self.update_preview_btn)
        
        form_layout.addWidget(preview_group)

        # --- Configuración de Metadatos ---
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QFormLayout(metadata_group)
        
        # Descripción del proceso
        self.description_line = QLineEdit()
        self.description_line.setPlaceholderText("Brief description of this processing run")
        metadata_layout.addRow("Description:", self.description_line)
        
        # Versión
        self.version_line = QLineEdit()
        self.version_line.setPlaceholderText("e.g., 1.0, v2.1")
        metadata_layout.addRow("Version:", self.version_line)
        
        # Usuario/Operador
        self.operator_line = QLineEdit()
        self.operator_line.setPlaceholderText("Who is running this process")
        metadata_layout.addRow("Operator:", self.operator_line)
        
        form_layout.addWidget(metadata_group)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Configuración inicial
        self._set_default_values()

    def _connect_signals(self) -> None:
        """Conecta las señales de los widgets."""
        # Conectar todos los campos que afectan la configuración
        self.delivery_code_line.textChanged.connect(self._emit_config_changed)
        self.date_edit.dateChanged.connect(self._emit_config_changed)
        self.base_prefix_line.textChanged.connect(self._emit_config_changed)
        self.custom_suffix_line.textChanged.connect(self._emit_config_changed)
        self.results_subdir_line.textChanged.connect(self._emit_config_changed)
        self.logs_subdir_line.textChanged.connect(self._emit_config_changed)
        self.summary_subdir_line.textChanged.connect(self._emit_config_changed)
        self.description_line.textChanged.connect(self._emit_config_changed)
        self.version_line.textChanged.connect(self._emit_config_changed)
        self.operator_line.textChanged.connect(self._emit_config_changed)

        # Conectar cambios para actualizar preview automáticamente
        self.delivery_code_line.textChanged.connect(self._update_preview)
        self.date_edit.dateChanged.connect(self._update_preview)
        self.base_prefix_line.textChanged.connect(self._update_preview)
        self.custom_suffix_line.textChanged.connect(self._update_preview)

    def _set_default_values(self) -> None:
        """Establece valores por defecto."""
        # Generar código de entrega por defecto
        today = datetime.now()
        default_code = f"d{today.strftime('%m%d')}"
        self.delivery_code_line.setText(default_code)
        
        # Usuario actual (si está disponible)
        try:
            import getpass
            self.operator_line.setText(getpass.getuser())
        except:
            pass
        
        # Actualizar preview inicial
        self._update_preview()

    def _generate_filename_examples(self) -> Dict[str, str]:
        """Genera ejemplos de nombres de archivo basados en la configuración actual."""
        date_str = self.date_edit.date().toString("yyyyMMdd")
        delivery_code = self.delivery_code_line.text().strip()
        base_prefix = self.base_prefix_line.text().strip()
        custom_suffix = self.custom_suffix_line.text().strip()
        
        # Construir partes del nombre
        parts = []
        if base_prefix:
            parts.append(base_prefix)
        if delivery_code:
            parts.append(delivery_code)
        
        base_name = "_".join(parts) if parts else "output"
        if custom_suffix:
            base_name += custom_suffix
        
        examples = {
            "Gridcode calculation": f"{date_str}_{base_name}_gridcode_calculated.gpkg",
            "Dissolved & buffered": f"{date_str}_{base_name}_diss_buff.gpkg",
            "Generated parcels": f"{date_str}_{base_name}_generated_parcels.gpkg",
            "Summary file": f"summary_{base_name}_{date_str}.csv",
            "Log file": f"process_{base_name}_{date_str}.log"
        }
        
        return examples

    def _update_preview(self) -> None:
        """Actualiza el preview de nombres de archivos."""
        try:
            examples = self._generate_filename_examples()
            
            preview_text = "File naming examples:\n\n"
            for file_type, filename in examples.items():
                preview_text += f"{file_type}:\n  {filename}\n\n"
            
            # Agregar estructura de directorios
            results_dir = self.results_subdir_line.text().strip() or "results"
            logs_dir = self.logs_subdir_line.text().strip() or "logs"
            summary_dir = self.summary_subdir_line.text().strip() or "summary"
            
            preview_text += "Directory structure:\n"
            preview_text += f"  📁 {results_dir}/\n"
            preview_text += f"  📁 {logs_dir}/\n"
            preview_text += f"  📁 {summary_dir}/\n"
            
            self.preview_text.setPlainText(preview_text)
            
        except Exception as e:
            self.preview_text.setPlainText(f"Error generating preview: {e}")

    def _emit_config_changed(self) -> None:
        """Emite la señal de cambio de configuración."""
        config = self.get_config()
        self.configChanged.emit(config)

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual de entrega."""
        date_obj = self.date_edit.date().toPyDate()
        
        config = {
            "delivery_code": self.delivery_code_line.text().strip(),
            "date_today": date_obj.strftime("%Y%m%d"),
            "date_formatted": date_obj.strftime("%Y-%m-%d"),
            "base_prefix": self.base_prefix_line.text().strip(),
            "custom_suffix": self.custom_suffix_line.text().strip(),
            "subdirectories": {
                "results": self.results_subdir_line.text().strip() or "results",
                "logs": self.logs_subdir_line.text().strip() or "logs", 
                "summary": self.summary_subdir_line.text().strip() or "summary"
            },
            "metadata": {
                "description": self.description_line.text().strip(),
                "version": self.version_line.text().strip(),
                "operator": self.operator_line.text().strip(),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración al tab."""
        # Bloquear señales temporalmente
        self.delivery_code_line.blockSignals(True)
        self.date_edit.blockSignals(True)
        self.base_prefix_line.blockSignals(True)
        self.custom_suffix_line.blockSignals(True)
        
        # Aplicar configuración básica
        self.delivery_code_line.setText(config.get("delivery_code", ""))
        self.base_prefix_line.setText(config.get("base_prefix", ""))
        self.custom_suffix_line.setText(config.get("custom_suffix", ""))
        
        # Fecha
        date_str = config.get("date_today", "")
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                self.date_edit.setDate(QDate(date_obj.year, date_obj.month, date_obj.day))
            except ValueError:
                pass  # Mantener fecha actual si hay error
        
        # Subdirectorios
        subdirs = config.get("subdirectories", {})
        self.results_subdir_line.setText(subdirs.get("results", "results"))
        self.logs_subdir_line.setText(subdirs.get("logs", "logs"))
        self.summary_subdir_line.setText(subdirs.get("summary", "summary"))
        
        # Metadatos
        metadata = config.get("metadata", {})
        self.description_line.setText(metadata.get("description", ""))
        self.version_line.setText(metadata.get("version", ""))
        self.operator_line.setText(metadata.get("operator", ""))
        
        # Restaurar señales
        self.delivery_code_line.blockSignals(False)
        self.date_edit.blockSignals(False)
        self.base_prefix_line.blockSignals(False)
        self.custom_suffix_line.blockSignals(False)
        
        # Actualizar preview y emitir cambio
        self._update_preview()
        self._emit_config_changed() 