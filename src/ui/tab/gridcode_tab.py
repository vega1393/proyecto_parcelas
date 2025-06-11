# src/ui/tab/gridcode_tab.py

import os
import json
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QScrollArea, QFrame,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QCheckBox, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from src.utils.gpkg_helpers import list_fields

class GridCodeTab(QWidget):
    """
    Tab para configurar la generación de GridCode con bins personalizables.
    """
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._gridcode_config: Dict[str, Any] = {}
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Inicializa la interfaz de usuario del tab de GridCode."""
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QVBoxLayout(content_widget)

        # --- Título y Activación ---
        title_group = QGroupBox("GridCode Configuration")
        title_layout = QFormLayout(title_group)
        
        self.enable_gridcode_checkbox = QCheckBox("Enable GridCode Calculation")
        self.enable_gridcode_checkbox.setToolTip("Enable automatic gridcode calculation based on field bins")
        title_layout.addRow(self.enable_gridcode_checkbox)
        
        form_layout.addWidget(title_group)

        # --- Configuración de Campos ---
        fields_group = QGroupBox("Field Configuration")
        fields_layout = QFormLayout(fields_group)
        
        # Campo 1 (ej: cov)
        self.field1_name_line = QLineEdit()
        self.field1_name_line.setPlaceholderText("e.g., cov, canopy_cover")
        fields_layout.addRow("Field 1 Name:", self.field1_name_line)
        
        # Campo 2 (ej: p95)
        self.field2_name_line = QLineEdit()
        self.field2_name_line.setPlaceholderText("e.g., p95, height")
        fields_layout.addRow("Field 2 Name:", self.field2_name_line)
        
        form_layout.addWidget(fields_group)

        # --- Bins Field 1 ---
        field1_group = QGroupBox("Field 1 Bins Configuration")
        field1_layout = QVBoxLayout(field1_group)
        
        # Botones para Field 1
        field1_btn_layout = QHBoxLayout()
        self.add_bin1_btn = QPushButton("Add Bin")
        self.remove_bin1_btn = QPushButton("Remove Selected")
        self.load_preset1_btn = QPushButton("Load Preset")
        field1_btn_layout.addWidget(self.add_bin1_btn)
        field1_btn_layout.addWidget(self.remove_bin1_btn)
        field1_btn_layout.addWidget(self.load_preset1_btn)
        field1_btn_layout.addStretch()
        field1_layout.addLayout(field1_btn_layout)
        
        # Tabla Field 1
        self.field1_table = QTableWidget()
        self.field1_table.setColumnCount(3)
        self.field1_table.setHorizontalHeaderLabels(["Min Value", "Max Value", "ID"])
        self.field1_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.field1_table.setMinimumHeight(150)
        field1_layout.addWidget(self.field1_table)
        
        form_layout.addWidget(field1_group)

        # --- Bins Field 2 ---
        field2_group = QGroupBox("Field 2 Bins Configuration")
        field2_layout = QVBoxLayout(field2_group)
        
        # Botones para Field 2
        field2_btn_layout = QHBoxLayout()
        self.add_bin2_btn = QPushButton("Add Bin")
        self.remove_bin2_btn = QPushButton("Remove Selected")
        self.load_preset2_btn = QPushButton("Load Preset")
        field2_btn_layout.addWidget(self.add_bin2_btn)
        field2_btn_layout.addWidget(self.remove_bin2_btn)
        field2_btn_layout.addWidget(self.load_preset2_btn)
        field2_btn_layout.addStretch()
        field2_layout.addLayout(field2_btn_layout)
        
        # Tabla Field 2
        self.field2_table = QTableWidget()
        self.field2_table.setColumnCount(3)
        self.field2_table.setHorizontalHeaderLabels(["Min Value", "Max Value", "ID"])
        self.field2_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.field2_table.setMinimumHeight(150)
        field2_layout.addWidget(self.field2_table)
        
        form_layout.addWidget(field2_group)

        # --- Presets y Export/Import ---
        presets_group = QGroupBox("Presets & Configuration")
        presets_layout = QHBoxLayout(presets_group)
        
        self.export_config_btn = QPushButton("Export GridCode Config")
        self.import_config_btn = QPushButton("Import GridCode Config")
        self.load_cov_preset_btn = QPushButton("Load COV Preset")
        self.load_p95_preset_btn = QPushButton("Load P95 Preset")
        
        presets_layout.addWidget(self.export_config_btn)
        presets_layout.addWidget(self.import_config_btn)
        presets_layout.addWidget(self.load_cov_preset_btn)
        presets_layout.addWidget(self.load_p95_preset_btn)
        presets_layout.addStretch()
        
        form_layout.addWidget(presets_group)

        # --- Preview ---
        preview_group = QGroupBox("Configuration Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QLabel("GridCode configuration will appear here...")
        self.preview_text.setWordWrap(True)
        self.preview_text.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        preview_layout.addWidget(self.preview_text)
        
        form_layout.addWidget(preview_group)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Configuración inicial
        self._load_default_presets()
        self._update_enabled_state()

    def _connect_signals(self) -> None:
        """Conecta las señales de los widgets."""
        # Enable/disable
        self.enable_gridcode_checkbox.stateChanged.connect(self._update_enabled_state)
        self.enable_gridcode_checkbox.stateChanged.connect(self._emit_config_changed)
        
        # Field names
        self.field1_name_line.textChanged.connect(self._emit_config_changed)
        self.field2_name_line.textChanged.connect(self._emit_config_changed)
        
        # Botones Field 1
        self.add_bin1_btn.clicked.connect(lambda: self._add_bin_row(self.field1_table))
        self.remove_bin1_btn.clicked.connect(lambda: self._remove_selected_bin(self.field1_table))
        self.load_preset1_btn.clicked.connect(self._load_field1_preset)
        
        # Botones Field 2
        self.add_bin2_btn.clicked.connect(lambda: self._add_bin_row(self.field2_table))
        self.remove_bin2_btn.clicked.connect(lambda: self._remove_selected_bin(self.field2_table))
        self.load_preset2_btn.clicked.connect(self._load_field2_preset)
        
        # Presets y Export/Import
        self.export_config_btn.clicked.connect(self._export_config)
        self.import_config_btn.clicked.connect(self._import_config)
        self.load_cov_preset_btn.clicked.connect(self._load_cov_preset)
        self.load_p95_preset_btn.clicked.connect(self._load_p95_preset)
        
        # Table changes
        self.field1_table.cellChanged.connect(self._emit_config_changed)
        self.field2_table.cellChanged.connect(self._emit_config_changed)

    def _update_enabled_state(self) -> None:
        """Actualiza el estado habilitado/deshabilitado de los controles."""
        enabled = self.enable_gridcode_checkbox.isChecked()
        
        widgets_to_enable = [
            self.field1_name_line, self.field2_name_line,
            self.add_bin1_btn, self.remove_bin1_btn, self.load_preset1_btn,
            self.add_bin2_btn, self.remove_bin2_btn, self.load_preset2_btn,
            self.field1_table, self.field2_table,
            self.export_config_btn, self.import_config_btn,
            self.load_cov_preset_btn, self.load_p95_preset_btn
        ]
        
        for widget in widgets_to_enable:
            widget.setEnabled(enabled)

    def _add_bin_row(self, table: QTableWidget) -> None:
        """Agrega una nueva fila a la tabla de bins."""
        row = table.rowCount()
        table.insertRow(row)
        
        # Valores por defecto
        table.setItem(row, 0, QTableWidgetItem("0"))      # Min
        table.setItem(row, 1, QTableWidgetItem("100"))    # Max
        table.setItem(row, 2, QTableWidgetItem(str(row + 1)))  # ID
        
        self._emit_config_changed()

    def _remove_selected_bin(self, table: QTableWidget) -> None:
        """Remueve la fila seleccionada de la tabla de bins."""
        current_row = table.currentRow()
        if current_row >= 0:
            table.removeRow(current_row)
            self._emit_config_changed()

    def _load_field1_preset(self) -> None:
        """Carga preset para el campo 1."""
        field_name = self.field1_name_line.text().lower()
        if 'cov' in field_name:
            self._load_cov_preset()
        elif 'p95' in field_name or 'height' in field_name:
            self._load_p95_preset()
        else:
            QMessageBox.information(self, "Preset", "No preset available for this field name. Use generic presets.")

    def _load_field2_preset(self) -> None:
        """Carga preset para el campo 2."""
        field_name = self.field2_name_line.text().lower()
        if 'cov' in field_name:
            self._load_cov_preset()
        elif 'p95' in field_name or 'height' in field_name:
            self._load_p95_preset()
        else:
            QMessageBox.information(self, "Preset", "No preset available for this field name. Use generic presets.")

    def _load_cov_preset(self) -> None:
        """Carga preset para cobertura (COV)."""
        bins_data = [
            {"min": "", "max": "50", "id": "1"},
            {"min": "50", "max": "70", "id": "2"},
            {"min": "70", "max": "", "id": "3"}
        ]
        self._populate_table_with_data(self.field1_table, bins_data)
        self.field1_name_line.setText("cov")
        self._emit_config_changed()

    def _load_p95_preset(self) -> None:
        """Carga preset para altura (P95)."""
        bins_data = [
            {"min": "", "max": "12", "id": "1"},
            {"min": "12", "max": "16", "id": "2"},
            {"min": "16", "max": "20", "id": "3"},
            {"min": "20", "max": "24", "id": "4"},
            {"min": "24", "max": "", "id": "5"}
        ]
        self._populate_table_with_data(self.field2_table, bins_data)
        self.field2_name_line.setText("p95")
        self._emit_config_changed()

    def _populate_table_with_data(self, table: QTableWidget, bins_data: List[Dict[str, str]]) -> None:
        """Llena una tabla con datos de bins."""
        table.setRowCount(len(bins_data))
        for row, bin_data in enumerate(bins_data):
            table.setItem(row, 0, QTableWidgetItem(bin_data.get("min", "")))
            table.setItem(row, 1, QTableWidgetItem(bin_data.get("max", "")))
            table.setItem(row, 2, QTableWidgetItem(bin_data.get("id", "")))

    def _load_default_presets(self) -> None:
        """Carga los presets por defecto."""
        self.field1_name_line.setText("cov")
        self.field2_name_line.setText("p95")
        self._load_cov_preset()
        self._load_p95_preset()

    def _export_config(self) -> None:
        """Exporta la configuración de GridCode a un archivo JSON."""
        config = self.get_config()
        if not config.get("enabled"):
            QMessageBox.warning(self, "Export Warning", "GridCode is not enabled. Enable it first.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export GridCode Config", 
            "gridcode_config.json", 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Export Success", f"GridCode configuration exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export configuration:\n{e}")

    def _import_config(self) -> None:
        """Importa la configuración de GridCode desde un archivo JSON."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import GridCode Config", 
            "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.set_config(config)
                QMessageBox.information(self, "Import Success", f"GridCode configuration imported from:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import configuration:\n{e}")

    def _get_table_bins(self, table: QTableWidget) -> List[Dict[str, Any]]:
        """Extrae los bins de una tabla."""
        bins = []
        for row in range(table.rowCount()):
            min_item = table.item(row, 0)
            max_item = table.item(row, 1)
            id_item = table.item(row, 2)
            
            bin_def = {}
            
            # Min value
            if min_item and min_item.text().strip():
                try:
                    bin_def["min"] = float(min_item.text())
                except ValueError:
                    continue
                    
            # Max value
            if max_item and max_item.text().strip():
                try:
                    bin_def["max"] = float(max_item.text())
                except ValueError:
                    continue
                    
            # ID
            if id_item and id_item.text().strip():
                try:
                    bin_def["id"] = int(id_item.text())
                except ValueError:
                    continue
            
            if bin_def:  # Solo agregar si tiene al menos un valor válido
                bins.append(bin_def)
                
        return bins

    def _emit_config_changed(self) -> None:
        """Emite la señal de cambio de configuración y actualiza el preview."""
        config = self.get_config()
        self._update_preview(config)
        self.configChanged.emit(config)

    def _update_preview(self, config: Dict[str, Any]) -> None:
        """Actualiza el preview de la configuración."""
        if not config.get("enabled"):
            self.preview_text.setText("GridCode calculation is disabled.")
            return
            
        preview_text = "GridCode Configuration:\n\n"
        
        gridcode_params = config.get("gridcode_params", {})
        for field_name, field_config in gridcode_params.items():
            preview_text += f"Field: {field_name}\n"
            preview_text += f"  Source Field: {field_config.get('field', 'N/A')}\n"
            preview_text += f"  Bins:\n"
            
            for bin_def in field_config.get("bins", []):
                min_val = bin_def.get("min", "-∞")
                max_val = bin_def.get("max", "+∞")
                bin_id = bin_def.get("id", "?")
                preview_text += f"    {min_val} to {max_val} → ID {bin_id}\n"
            preview_text += "\n"
            
        self.preview_text.setText(preview_text)

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual del GridCode."""
        if not self.enable_gridcode_checkbox.isChecked():
            return {"enabled": False}
            
        field1_name = self.field1_name_line.text().strip()
        field2_name = self.field2_name_line.text().strip()
        
        config = {
            "enabled": True,
            "gridcode_params": {}
        }
        
        # Campo 1
        if field1_name:
            field1_bins = self._get_table_bins(self.field1_table)
            if field1_bins:
                config["gridcode_params"]["field1"] = {
                    "field": field1_name,
                    "bins": field1_bins
                }
        
        # Campo 2
        if field2_name:
            field2_bins = self._get_table_bins(self.field2_table)
            if field2_bins:
                config["gridcode_params"]["field2"] = {
                    "field": field2_name,
                    "bins": field2_bins
                }
        
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración al tab."""
        # Bloquear señales temporalmente
        self.enable_gridcode_checkbox.blockSignals(True)
        self.field1_name_line.blockSignals(True)
        self.field2_name_line.blockSignals(True)
        
        # Configurar enable/disable
        enabled = config.get("enabled", False)
        self.enable_gridcode_checkbox.setChecked(enabled)
        
        if enabled:
            gridcode_params = config.get("gridcode_params", {})
            
            # Campo 1
            field1_config = gridcode_params.get("field1", {})
            if field1_config:
                self.field1_name_line.setText(field1_config.get("field", ""))
                bins1 = [{"min": str(b.get("min", "")), "max": str(b.get("max", "")), "id": str(b.get("id", ""))} 
                        for b in field1_config.get("bins", [])]
                self._populate_table_with_data(self.field1_table, bins1)
            
            # Campo 2
            field2_config = gridcode_params.get("field2", {})
            if field2_config:
                self.field2_name_line.setText(field2_config.get("field", ""))
                bins2 = [{"min": str(b.get("min", "")), "max": str(b.get("max", "")), "id": str(b.get("id", ""))} 
                        for b in field2_config.get("bins", [])]
                self._populate_table_with_data(self.field2_table, bins2)
        
        # Restaurar señales
        self.enable_gridcode_checkbox.blockSignals(False)
        self.field1_name_line.blockSignals(False)
        self.field2_name_line.blockSignals(False)
        
        # Actualizar estado y emitir cambio
        self._update_enabled_state()
        self._emit_config_changed() 