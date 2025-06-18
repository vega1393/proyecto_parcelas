"""
Tab para configurar el método de muestreo: Intensidad vs CSV.
"""

import os
import pandas as pd
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QScrollArea, QFrame,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QCheckBox, QFileDialog, QRadioButton, QButtonGroup, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class SamplingTab(QWidget):
    """
    Tab para configurar el método de muestreo y sus parámetros específicos.
    """
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._field_mappings: List[List[str]] = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Inicializa la interfaz de usuario del tab de muestreo."""
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QVBoxLayout(content_widget)

        # --- Selección de Método de Muestreo ---
        method_group = QGroupBox("🎯 Sampling Method Selection")
        method_layout = QVBoxLayout(method_group)
        
        # Radio buttons para seleccionar método
        self.method_button_group = QButtonGroup()
        self.intensity_radio = QRadioButton("Intensity-based Sampling")
        self.csv_radio = QRadioButton("CSV-based Sampling")
        
        self.intensity_radio.setToolTip("Generate parcels based on intensity per hectare")
        self.csv_radio.setToolTip("Generate parcels based on counts from CSV file")
        
        # Por defecto, intensidad seleccionada
        self.intensity_radio.setChecked(True)
        
        self.method_button_group.addButton(self.intensity_radio, 0)
        self.method_button_group.addButton(self.csv_radio, 1)
        
        method_layout.addWidget(self.intensity_radio)
        method_layout.addWidget(self.csv_radio)
        
        form_layout.addWidget(method_group)

        # --- Configuración de Intensidad ---
        self.intensity_section = QGroupBox("⚙️ Intensity Configuration")
        intensity_layout = QFormLayout(self.intensity_section)
        
        # Intensidad base
        self.base_intensity_spin = QSpinBox()
        self.base_intensity_spin.setRange(1, 1000)
        self.base_intensity_spin.setValue(80)
        self.base_intensity_spin.setSuffix(" parcels/1000ha")
        self.base_intensity_spin.setToolTip("Base intensity for parcel generation")
        intensity_layout.addRow("Base Intensity:", self.base_intensity_spin)
        
        # Checkbox para intensidad específica
        self.use_specific_intensity_checkbox = QCheckBox("Use Specific Intensity by Field")
        self.use_specific_intensity_checkbox.setToolTip("Enable field-specific intensity values")
        intensity_layout.addRow(self.use_specific_intensity_checkbox)
        
        # Tabla para intensidades específicas
        self.intensity_table = QTableWidget()
        self.intensity_table.setColumnCount(3)
        self.intensity_table.setHorizontalHeaderLabels(["Field", "Value", "Intensity"])
        self.intensity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.intensity_table.setMaximumHeight(150)
        self.intensity_table.setEnabled(False)  # Deshabilitada por defecto
        intensity_layout.addRow("Specific Intensities:", self.intensity_table)
        
        # Botones para manejar intensidades específicas
        intensity_btn_layout = QHBoxLayout()
        self.add_intensity_btn = QPushButton("Add Intensity")
        self.remove_intensity_btn = QPushButton("Remove Selected")
        self.add_intensity_btn.setEnabled(False)
        self.remove_intensity_btn.setEnabled(False)
        intensity_btn_layout.addWidget(self.add_intensity_btn)
        intensity_btn_layout.addWidget(self.remove_intensity_btn)
        intensity_btn_layout.addStretch()
        intensity_layout.addRow(intensity_btn_layout)
        
        form_layout.addWidget(self.intensity_section)

        # --- Configuración de CSV ---
        self.csv_section = QGroupBox("📊 CSV Configuration")
        csv_layout = QFormLayout(self.csv_section)
        
        # Selección de archivo CSV
        csv_file_layout = QHBoxLayout()
        self.csv_path_line = QLineEdit()
        self.csv_path_line.setPlaceholderText("Select CSV file with parcel counts...")
        self.csv_browse_btn = QPushButton("Browse...")
        csv_file_layout.addWidget(self.csv_path_line)
        csv_file_layout.addWidget(self.csv_browse_btn)
        csv_layout.addRow("CSV File:", csv_file_layout)
        
        # Selector de columna de conteo
        self.count_column_combo = QComboBox()
        self.count_column_combo.setToolTip("Column containing parcel counts")
        csv_layout.addRow("Count Column:", self.count_column_combo)
        
        # Selector de columna de gridcode
        self.gridcode_column_combo = QComboBox()
        self.gridcode_column_combo.setToolTip("Column containing gridcode values (optional)")
        csv_layout.addRow("GridCode Column:", self.gridcode_column_combo)
        
        # Mapeo de campos
        mapping_label = QLabel("Field Mappings:")
        mapping_label.setToolTip("Map GDF fields to CSV columns")
        csv_layout.addRow(mapping_label)
        
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(2)
        self.mapping_table.setHorizontalHeaderLabels(["GDF Field", "CSV Field"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.mapping_table.setMaximumHeight(120)
        csv_layout.addRow(self.mapping_table)
        
        # Botones para manejar mapeos
        mapping_btn_layout = QHBoxLayout()
        self.add_mapping_btn = QPushButton("Add Mapping")
        self.remove_mapping_btn = QPushButton("Remove Selected")
        self.auto_detect_btn = QPushButton("Auto-detect Fields")
        mapping_btn_layout.addWidget(self.add_mapping_btn)
        mapping_btn_layout.addWidget(self.remove_mapping_btn)
        mapping_btn_layout.addWidget(self.auto_detect_btn)
        mapping_btn_layout.addStretch()
        csv_layout.addRow(mapping_btn_layout)
        
        # Estadísticas del CSV
        self.csv_stats_label = QLabel("CSV Statistics will appear here...")
        self.csv_stats_label.setWordWrap(True)
        self.csv_stats_label.setStyleSheet("""
            background-color: #e8f5e8;
            padding: 10px;
            border: 1px solid #c3e6c3;
            border-radius: 5px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
        """)
        self.csv_stats_label.setMinimumHeight(70)
        csv_layout.addRow("📈 CSV Statistics:", self.csv_stats_label)
        
        form_layout.addWidget(self.csv_section)
        
        # Inicialmente ocultar sección CSV
        self.csv_section.setVisible(False)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        """Conecta las señales de los widgets."""
        # Cambio de método de muestreo
        self.method_button_group.buttonToggled.connect(self._on_method_changed)
        
        # Intensidad
        self.base_intensity_spin.valueChanged.connect(self._emit_config_changed)
        self.use_specific_intensity_checkbox.toggled.connect(self._on_specific_intensity_toggled)
        self.add_intensity_btn.clicked.connect(self._add_intensity_row)
        self.remove_intensity_btn.clicked.connect(self._remove_intensity_row)
        self.intensity_table.cellChanged.connect(self._emit_config_changed)
        
        # CSV
        self.csv_browse_btn.clicked.connect(self._browse_csv_file)
        self.csv_path_line.textChanged.connect(self._on_csv_path_changed)
        self.count_column_combo.currentTextChanged.connect(self._on_csv_config_changed)
        self.gridcode_column_combo.currentTextChanged.connect(self._on_csv_config_changed)
        self.add_mapping_btn.clicked.connect(self._add_mapping_row)
        self.remove_mapping_btn.clicked.connect(self._remove_mapping_row)
        self.auto_detect_btn.clicked.connect(self._auto_detect_fields)
        self.mapping_table.cellChanged.connect(self._on_mapping_changed)

    def _on_method_changed(self, button, checked: bool) -> None:
        """Maneja el cambio de método de muestreo."""
        if not checked:
            return
            
        is_intensity = button == self.intensity_radio
        
        # Mostrar/ocultar secciones según el método seleccionado
        self.intensity_section.setVisible(is_intensity)
        self.csv_section.setVisible(not is_intensity)
        
        self._emit_config_changed()

    def _on_specific_intensity_toggled(self, checked: bool) -> None:
        """Habilita/deshabilita controles de intensidad específica."""
        self.intensity_table.setEnabled(checked)
        self.add_intensity_btn.setEnabled(checked)
        self.remove_intensity_btn.setEnabled(checked)
        self._emit_config_changed()

    def _add_intensity_row(self) -> None:
        """Agrega una fila a la tabla de intensidades específicas."""
        row = self.intensity_table.rowCount()
        self.intensity_table.insertRow(row)
        
        # Valores por defecto
        self.intensity_table.setItem(row, 0, QTableWidgetItem("tipouso"))
        self.intensity_table.setItem(row, 1, QTableWidgetItem("EUGR"))
        self.intensity_table.setItem(row, 2, QTableWidgetItem("50"))
        
        self._emit_config_changed()

    def _remove_intensity_row(self) -> None:
        """Remueve la fila seleccionada de intensidades específicas."""
        current_row = self.intensity_table.currentRow()
        if current_row >= 0:
            self.intensity_table.removeRow(current_row)
            self._emit_config_changed()

    def _browse_csv_file(self) -> None:
        """Abre diálogo para seleccionar archivo CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", 
            "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_path_line.setText(file_path)

    def _on_csv_path_changed(self, path: str) -> None:
        """Maneja el cambio de ruta del CSV."""
        if path and os.path.exists(path):
            self._load_csv_columns(path)
        else:
            self._clear_csv_columns()
        
        self._emit_config_changed()

    def _load_csv_columns(self, csv_path: str) -> None:
        """Carga las columnas del CSV en los combos."""
        try:
            df = pd.read_csv(csv_path, nrows=0)  # Solo headers
            columns = list(df.columns)
            
            # Actualizar combos
            self.count_column_combo.clear()
            self.gridcode_column_combo.clear()
            
            # Columna de conteo - detectar automáticamente
            count_candidates = ['n', 'n_parcelas', 'count', 'parcelas']
            for col in columns:
                self.count_column_combo.addItem(col)
                if col.lower() in count_candidates:
                    self.count_column_combo.setCurrentText(col)
            
            # Columna de gridcode - detectar automáticamente
            self.gridcode_column_combo.addItem("")  # Opción vacía
            gridcode_candidates = ['gridcode', 'sup_ha', 'code', 'stratum']
            for col in columns:
                self.gridcode_column_combo.addItem(col)
                if col.lower() in gridcode_candidates:
                    self.gridcode_column_combo.setCurrentText(col)
                    
        except Exception as e:
            QMessageBox.warning(self, "CSV Error", f"Error reading CSV file:\n{e}")
            self._clear_csv_columns()

    def _clear_csv_columns(self) -> None:
        """Limpia los combos de columnas CSV."""
        self.count_column_combo.clear()
        self.gridcode_column_combo.clear()

    def _on_csv_config_changed(self) -> None:
        """Maneja cambios en la configuración del CSV."""
        self._update_csv_statistics()
        self._emit_config_changed()

    def _add_mapping_row(self) -> None:
        """Agrega una fila a la tabla de mapeos."""
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
        
        # Valores por defecto
        self.mapping_table.setItem(row, 0, QTableWidgetItem("tipouso"))
        self.mapping_table.setItem(row, 1, QTableWidgetItem("tipouso"))

    def _remove_mapping_row(self) -> None:
        """Remueve la fila seleccionada de mapeos."""
        current_row = self.mapping_table.currentRow()
        if current_row >= 0:
            self.mapping_table.removeRow(current_row)
            self._on_mapping_changed()

    def _auto_detect_fields(self) -> None:
        """Detecta automáticamente los campos comunes entre GDF y CSV."""
        csv_path = self.csv_path_line.text()
        if not csv_path or not os.path.exists(csv_path):
            QMessageBox.warning(self, "Auto-detect", "Please select a valid CSV file first.")
            return
            
        try:
            df = pd.read_csv(csv_path, nrows=0)
            csv_columns = [col.lower() for col in df.columns]
            
            # Campos comunes típicos
            common_fields = ['tipouso', 'tipomateri', 'predio', 'rodal']
            
            # Limpiar tabla actual
            self.mapping_table.setRowCount(0)
            
            # Agregar mapeos automáticos
            for field in common_fields:
                if field in csv_columns:
                    row = self.mapping_table.rowCount()
                    self.mapping_table.insertRow(row)
                    self.mapping_table.setItem(row, 0, QTableWidgetItem(field))
                    self.mapping_table.setItem(row, 1, QTableWidgetItem(field))
            
            self._on_mapping_changed()
            QMessageBox.information(self, "Auto-detect", f"Detected {self.mapping_table.rowCount()} common fields.")
            
        except Exception as e:
            QMessageBox.warning(self, "Auto-detect Error", f"Error auto-detecting fields:\n{e}")

    def _on_mapping_changed(self) -> None:
        """Maneja cambios en los mapeos de campos."""
        # Actualizar lista interna de mapeos
        self._field_mappings = []
        for row in range(self.mapping_table.rowCount()):
            gdf_field_item = self.mapping_table.item(row, 0)
            csv_field_item = self.mapping_table.item(row, 1)
            
            if gdf_field_item and csv_field_item:
                gdf_field = gdf_field_item.text().strip()
                csv_field = csv_field_item.text().strip()
                if gdf_field and csv_field:
                    self._field_mappings.append([gdf_field, csv_field])
        
        self._update_csv_statistics()
        self._emit_config_changed()

    def _update_csv_statistics(self) -> None:
        """Actualiza las estadísticas del CSV."""
        csv_path = self.csv_path_line.text()
        count_column = self.count_column_combo.currentText()
        
        if not csv_path or not os.path.exists(csv_path) or not count_column:
            self.csv_stats_label.setText("CSV Statistics will appear here...")
            return
            
        try:
            df = pd.read_csv(csv_path)
            
            if count_column not in df.columns:
                self.csv_stats_label.setText("Selected count column not found in CSV.")
                return
            
            # Estadísticas básicas
            df[count_column] = pd.to_numeric(df[count_column], errors='coerce').fillna(0)
            total_parcels = int(df[count_column].sum())
            total_groups = len(df)
            groups_with_parcels = len(df[df[count_column] > 0])
            
            if groups_with_parcels > 0:
                parcels_per_group = df[df[count_column] > 0][count_column]
                min_parcels = int(parcels_per_group.min())
                max_parcels = int(parcels_per_group.max())
                avg_parcels = parcels_per_group.mean()
                
                # Estadísticas de gridcode si está configurado
                gridcode_column = self.gridcode_column_combo.currentText()
                gridcode_stats = ""
                if gridcode_column and gridcode_column in df.columns:
                    unique_gridcodes = df[gridcode_column].nunique()
                    gridcode_stats = f"\nUnique gridcodes: {unique_gridcodes}"
                    
                    # Top 3 gridcodes
                    top_gridcodes = df[gridcode_column].value_counts().head(3)
                    if len(top_gridcodes) > 0:
                        gridcode_stats += "\nTop gridcodes:"
                        for gridcode, count in top_gridcodes.items():
                            gridcode_stats += f"\n  {gridcode}: {count} groups"
                
                stats_text = f"""Total parcels to generate: {total_parcels:,}
Groups with parcels: {groups_with_parcels}/{total_groups} ({groups_with_parcels/total_groups*100:.0f}%)
Parcels per group: {min_parcels}-{max_parcels} (avg: {avg_parcels:.1f}){gridcode_stats}"""
            else:
                stats_text = f"""Total parcels to generate: {total_parcels:,}
Groups with parcels: 0/{total_groups} (0%)
No groups have parcels assigned."""
            
            self.csv_stats_label.setText(stats_text)
            
        except Exception as e:
            self.csv_stats_label.setText(f"Error reading CSV statistics: {e}")

    def _emit_config_changed(self) -> None:
        """Emite la señal de cambio de configuración."""
        config = self.get_config()
        self.configChanged.emit(config)

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual del sampling."""
        config = {
            "use_csv": self.csv_radio.isChecked(),
            "csv_path": self.csv_path_line.text().strip() if self.csv_radio.isChecked() else None,
            "base_intensity": self.base_intensity_spin.value(),
            "use_specific_intensity": self.use_specific_intensity_checkbox.isChecked(),
            "specific_intensities": {},
            "count_column_csv": self.count_column_combo.currentText(),
            "gridcode_column_csv": self.gridcode_column_combo.currentText(),
            "field_mappings": self._field_mappings.copy()
        }
        
        # Obtener intensidades específicas
        if self.use_specific_intensity_checkbox.isChecked():
            for row in range(self.intensity_table.rowCount()):
                field_item = self.intensity_table.item(row, 0)
                value_item = self.intensity_table.item(row, 1)
                intensity_item = self.intensity_table.item(row, 2)
                
                if field_item and value_item and intensity_item:
                    field = field_item.text().strip()
                    value = value_item.text().strip()
                    try:
                        intensity = int(intensity_item.text())
                        if field not in config["specific_intensities"]:
                            config["specific_intensities"][field] = {}
                        config["specific_intensities"][field][value] = intensity
                    except ValueError:
                        continue
        
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración al tab."""
        # Bloquear señales temporalmente
        self.method_button_group.blockSignals(True)
        self.base_intensity_spin.blockSignals(True)
        self.use_specific_intensity_checkbox.blockSignals(True)
        self.csv_path_line.blockSignals(True)
        
        try:
            # Método de muestreo
            use_csv = config.get("use_csv", False)
            if use_csv:
                self.csv_radio.setChecked(True)
            else:
                self.intensity_radio.setChecked(True)
            
            # Configuración de intensidad
            self.base_intensity_spin.setValue(config.get("base_intensity", 80))
            self.use_specific_intensity_checkbox.setChecked(config.get("use_specific_intensity", False))
            
            # Intensidades específicas
            specific_intensities = config.get("specific_intensities", {})
            self.intensity_table.setRowCount(0)
            for field, values in specific_intensities.items():
                for value, intensity in values.items():
                    row = self.intensity_table.rowCount()
                    self.intensity_table.insertRow(row)
                    self.intensity_table.setItem(row, 0, QTableWidgetItem(field))
                    self.intensity_table.setItem(row, 1, QTableWidgetItem(value))
                    self.intensity_table.setItem(row, 2, QTableWidgetItem(str(intensity)))
            
            # Configuración de CSV
            csv_path = config.get("csv_path", "")
            if csv_path:
                self.csv_path_line.setText(csv_path)
            
            # Mapeos de campos
            field_mappings = config.get("field_mappings", [])
            self.mapping_table.setRowCount(0)
            for gdf_field, csv_field in field_mappings:
                row = self.mapping_table.rowCount()
                self.mapping_table.insertRow(row)
                self.mapping_table.setItem(row, 0, QTableWidgetItem(gdf_field))
                self.mapping_table.setItem(row, 1, QTableWidgetItem(csv_field))
            
            self._field_mappings = field_mappings.copy()
            
            # Actualizar visibilidad de secciones
            self._on_method_changed(self.csv_radio if use_csv else self.intensity_radio, True)
            
        finally:
            # Restaurar señales
            self.method_button_group.blockSignals(False)
            self.base_intensity_spin.blockSignals(False)
            self.use_specific_intensity_checkbox.blockSignals(False)
            self.csv_path_line.blockSignals(False)
            
            # Actualizar estados
            self._on_specific_intensity_toggled(self.use_specific_intensity_checkbox.isChecked())
            self._update_csv_statistics() 