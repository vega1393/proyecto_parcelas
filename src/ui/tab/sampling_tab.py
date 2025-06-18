"""
Tab para configurar el método de muestreo: Intensidad vs CSV.
"""

import os
import pandas as pd
import geopandas as gpd
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
        
        # Radio buttons para tipo de intensidad
        intensity_type_layout = QVBoxLayout()
        self.intensity_button_group = QButtonGroup()
        
        self.base_intensity_radio = QRadioButton("Use Base Intensity")
        self.specific_intensity_radio = QRadioButton("Use Specific Intensity by Field")
        
        self.base_intensity_radio.setChecked(True)  # Por defecto
        self.intensity_button_group.addButton(self.base_intensity_radio, 0)
        self.intensity_button_group.addButton(self.specific_intensity_radio, 1)
        
        intensity_type_layout.addWidget(self.base_intensity_radio)
        intensity_type_layout.addWidget(self.specific_intensity_radio)
        intensity_layout.addRow("Intensity Type:", intensity_type_layout)
        
        # Intensidad base
        self.base_intensity_spin = QSpinBox()
        self.base_intensity_spin.setRange(1, 1000)
        self.base_intensity_spin.setValue(12)  # 1 parcel per 12 hectares
        self.base_intensity_spin.setSuffix(" ha")
        self.base_intensity_spin.setToolTip("One parcel per X hectares")
        intensity_layout.addRow("Base Intensity:", self.base_intensity_spin)
        
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
        self.auto_intensity_btn = QPushButton("Auto-detect Common")
        self.add_intensity_btn.setEnabled(False)
        self.remove_intensity_btn.setEnabled(False)
        self.auto_intensity_btn.setEnabled(False)
        intensity_btn_layout.addWidget(self.add_intensity_btn)
        intensity_btn_layout.addWidget(self.remove_intensity_btn)
        intensity_btn_layout.addWidget(self.auto_intensity_btn)
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
            background-color: #e3f2fd;
            color: #0d47a1;
            padding: 12px;
            border: 2px solid #1976d2;
            border-radius: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
            font-weight: bold;
        """)
        self.csv_stats_label.setMinimumHeight(80)
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
        self.intensity_button_group.buttonToggled.connect(self._on_intensity_type_changed)
        self.add_intensity_btn.clicked.connect(self._add_intensity_row)
        self.remove_intensity_btn.clicked.connect(self._remove_intensity_row)
        self.auto_intensity_btn.clicked.connect(self._auto_detect_intensities)
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

    def _on_intensity_type_changed(self, button, checked: bool) -> None:
        """Maneja el cambio de tipo de intensidad."""
        if not checked:
            return
            
        is_specific = button == self.specific_intensity_radio
        
        # Habilitar/deshabilitar controles según el tipo seleccionado
        self.base_intensity_spin.setEnabled(not is_specific)
        self.intensity_table.setEnabled(is_specific)
        self.add_intensity_btn.setEnabled(is_specific)
        self.remove_intensity_btn.setEnabled(is_specific)
        self.auto_intensity_btn.setEnabled(is_specific)
        
        self._emit_config_changed()

    def _add_intensity_row(self) -> None:
        """Agrega una fila a la tabla de intensidades específicas."""
        row = self.intensity_table.rowCount()
        self.intensity_table.insertRow(row)
        
        # ComboBox para Field
        field_combo = QComboBox()
        field_combo.setEditable(True)
        field_combo.addItems(self._get_available_fields())
        field_combo.setCurrentText("tipouso")
        field_combo.currentTextChanged.connect(lambda text, r=row: self._on_field_changed(r, text))
        self.intensity_table.setCellWidget(row, 0, field_combo)
        
        # ComboBox para Value
        value_combo = QComboBox()
        value_combo.setEditable(True)
        value_combo.addItems(self._get_field_values("tipouso"))
        value_combo.setCurrentText("EUGR")
        value_combo.currentTextChanged.connect(self._emit_config_changed)
        self.intensity_table.setCellWidget(row, 1, value_combo)
        
        # SpinBox para Intensity
        intensity_spin = QSpinBox()
        intensity_spin.setRange(1, 1000)
        intensity_spin.setValue(20)  # 1 parcel per 20 hectares
        intensity_spin.setSuffix(" ha")
        intensity_spin.setToolTip("One parcel per X hectares")
        intensity_spin.valueChanged.connect(self._emit_config_changed)
        self.intensity_table.setCellWidget(row, 2, intensity_spin)
        
        self._emit_config_changed()

    def _get_available_fields(self) -> List[str]:
        """Obtiene los campos disponibles desde el archivo del Plan Operativo."""
        try:
            # Obtener la ruta y capa del archivo PO desde la aplicación principal
            po_file_path, po_layer = self._get_po_file_info()
            if po_file_path and po_layer:
                # Leer el archivo usando geopandas con pyogrio
                gdf = gpd.read_file(po_file_path, layer=po_layer, engine='pyogrio', rows=1)  # Solo 1 fila para obtener columnas
                # Filtrar campos útiles para intensidades (excluir geometry y campos técnicos)
                exclude_fields = ['geometry', 'fid', 'objectid', 'shape_length', 'shape_area', 'sup_ha']
                available_fields = [col for col in gdf.columns 
                                  if col.lower() not in [f.lower() for f in exclude_fields]]
                if available_fields:
                    return available_fields
        except Exception as e:
            print(f"Error reading PO file for fields: {e}")
        
        # Campos por defecto si no se pueden obtener dinámicamente
        return ["tipouso", "tipomateri", "predio", "rodal", "gridcode"]

    def _get_field_values(self, field_name: str) -> List[str]:
        """Obtiene los valores únicos para un campo específico desde el archivo del Plan Operativo."""
        try:
            # Obtener la ruta y capa del archivo PO desde la aplicación principal
            po_file_path, po_layer = self._get_po_file_info()
            if po_file_path and po_layer:
                # Leer el archivo usando geopandas con pyogrio
                gdf = gpd.read_file(po_file_path, layer=po_layer, engine='pyogrio')
                
                if field_name in gdf.columns:
                    # Obtener valores únicos, ordenados, excluyendo nulos
                    unique_values = (gdf[field_name]
                                   .dropna()
                                   .astype(str)
                                   .unique())
                    
                    # Ordenar y convertir a lista
                    unique_values = sorted([str(val) for val in unique_values if str(val).strip()])
                    
                    if unique_values:
                        return unique_values
        except Exception as e:
            print(f"Error reading PO file for field values '{field_name}': {e}")
        
        # Valores típicos por campo como fallback
        field_values = {
            "tipouso": ["EUGR", "EUCL", "EUGA", "PINO", "NATIVA", "MIXTO"],
            "tipomateri": ["NATIVA", "PLANTADA", "MIXTO"],
            "predio": ["FORESTAL", "AGRICOLA", "URBANO"],
            "rodal": ["R1", "R2", "R3", "R4", "R5"],
            "gridcode": ["1", "2", "3", "4", "5"]
        }
        
        return field_values.get(field_name, ["VALUE1", "VALUE2", "VALUE3"])

    def _get_csv_fields(self) -> List[str]:
        """Obtiene los campos disponibles desde el archivo CSV."""
        try:
            csv_path = self.csv_path_line.text().strip()
            if csv_path and os.path.exists(csv_path):
                df = pd.read_csv(csv_path, nrows=0)  # Solo headers
                return list(df.columns)
        except Exception as e:
            print(f"Error reading CSV fields: {e}")
        
        # Campos por defecto si no se pueden obtener
        return ["tipouso", "tipomateri", "predio", "rodal"]

    def _get_po_file_info(self) -> tuple[str, str]:
        """Obtiene la ruta y capa del archivo del Plan Operativo desde la aplicación principal."""
        try:
            # Buscar la aplicación principal y obtener la ruta del PO
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.allWidgets():
                    if hasattr(widget, 'po_tab') and widget.po_tab:
                        # Obtener ruta y capa del POTab
                        po_file_path = widget.po_tab.po_path_line.text().strip()
                        po_layer = widget.po_tab.po_layer_combo.currentText().strip()
                        
                        if (po_file_path and os.path.exists(po_file_path) and 
                            po_layer and not po_layer.startswith("[")):
                            return po_file_path, po_layer
                        break
        except Exception as e:
            print(f"Error getting PO file info: {e}")
        
        return "", ""

    def _get_po_file_path(self) -> str:
        """Obtiene solo la ruta del archivo del Plan Operativo (para compatibilidad)."""
        file_path, _ = self._get_po_file_info()
        return file_path

    def _get_default_intensities_for_field(self, field_name: str) -> Dict[str, int]:
        """Obtiene intensidades por defecto para un campo específico."""
        # Intensidades típicas por campo y valor
        default_intensities = {
            "tipouso": {
                "EUGR": 20, "EUCL": 16, "EUGA": 25, "PINO": 14,
                "NATIVA": 33, "MIXTO": 18, "ACACIA": 12
            },
            "tipomateri": {
                "NATIVA": 33, "PLANTADA": 12, "MIXTO": 20
            },
            "predio": {
                "FORESTAL": 15, "AGRICOLA": 25, "URBANO": 8
            },
            "rodal": {
                "R1": 10, "R2": 12, "R3": 14, "R4": 16, "R5": 18
            },
            "gridcode": {
                "1": 8, "2": 12, "3": 16, "4": 20, "5": 25
            }
        }
        
        return default_intensities.get(field_name.lower(), {})

    def _on_field_changed(self, row: int, field_name: str) -> None:
        """Maneja el cambio de campo en una fila específica."""
        # Actualizar el ComboBox de valores para el nuevo campo
        value_combo = self.intensity_table.cellWidget(row, 1)
        if isinstance(value_combo, QComboBox):
            value_combo.clear()
            value_combo.addItems(self._get_field_values(field_name))
            if self._get_field_values(field_name):
                value_combo.setCurrentText(self._get_field_values(field_name)[0])
        
        self._emit_config_changed()

    def refresh_po_data(self) -> None:
        """Refresca los datos del Plan Operativo cuando cambie el archivo."""
        # Actualizar todas las filas existentes de intensidad específica
        for row in range(self.intensity_table.rowCount()):
            field_widget = self.intensity_table.cellWidget(row, 0)
            if isinstance(field_widget, QComboBox):
                # Actualizar opciones de campo
                current_field = field_widget.currentText()
                field_widget.clear()
                field_widget.addItems(self._get_available_fields())
                if current_field in self._get_available_fields():
                    field_widget.setCurrentText(current_field)
                
                # Actualizar valores para el campo actual
                value_widget = self.intensity_table.cellWidget(row, 1)
                if isinstance(value_widget, QComboBox):
                    current_value = value_widget.currentText()
                    value_widget.clear()
                    value_widget.addItems(self._get_field_values(field_widget.currentText()))
                    if current_value in self._get_field_values(field_widget.currentText()):
                        value_widget.setCurrentText(current_value)

    def refresh_csv_mappings(self) -> None:
        """Refresca los ComboBoxes de mapeo cuando cambie el archivo CSV."""
        # Actualizar todas las filas existentes de mapeo
        for row in range(self.mapping_table.rowCount()):
            # Actualizar ComboBox de CSV Field
            csv_field_widget = self.mapping_table.cellWidget(row, 1)
            if isinstance(csv_field_widget, QComboBox):
                current_csv_field = csv_field_widget.currentText()
                csv_field_widget.clear()
                csv_fields = self._get_csv_fields()
                csv_field_widget.addItems(csv_fields)
                if current_csv_field in csv_fields:
                    csv_field_widget.setCurrentText(current_csv_field)

    def _remove_intensity_row(self) -> None:
        """Remueve la fila seleccionada de intensidades específicas."""
        current_row = self.intensity_table.currentRow()
        if current_row >= 0:
            self.intensity_table.removeRow(current_row)
            self._emit_config_changed()

    def _auto_detect_intensities(self) -> None:
        """Auto-detecta intensidades para un campo específico seleccionado por el usuario."""
        from PyQt6.QtWidgets import QInputDialog
        
        # Obtener campos disponibles
        available_fields = self._get_available_fields()
        
        if not available_fields:
            QMessageBox.warning(self, "No Fields", "No fields available for auto-mapping.")
            return
        
        # Preguntar al usuario qué campo usar
        field_name, ok = QInputDialog.getItem(
            self, 
            "Select Field for Auto-mapping",
            "Select the field to generate intensity mappings for:",
            available_fields,
            0,
            False
        )
        
        if not ok or not field_name:
            return
        
        # Obtener valores únicos para el campo seleccionado
        field_values = self._get_field_values(field_name)
        
        if not field_values:
            QMessageBox.warning(
                self, 
                "No Values", 
                f"No values found for field '{field_name}' in the Plan Operativo."
            )
            return
        
        # Limpiar tabla actual
        self.intensity_table.setRowCount(0)
        
        # Generar intensidades automáticas para cada valor
        default_intensities = self._get_default_intensities_for_field(field_name)
        
        for value in field_values:
            # Usar intensidad por defecto si existe, sino usar 15 ha
            intensity = default_intensities.get(value.upper(), 15)
            
            row = self.intensity_table.rowCount()
            self.intensity_table.insertRow(row)
            
            # ComboBox para Field
            field_combo = QComboBox()
            field_combo.setEditable(True)
            field_combo.addItems(available_fields)
            field_combo.setCurrentText(field_name)
            field_combo.currentTextChanged.connect(lambda text, r=row: self._on_field_changed(r, text))
            self.intensity_table.setCellWidget(row, 0, field_combo)
            
            # ComboBox para Value
            value_combo = QComboBox()
            value_combo.setEditable(True)
            value_combo.addItems(field_values)
            value_combo.setCurrentText(value)
            value_combo.currentTextChanged.connect(self._emit_config_changed)
            self.intensity_table.setCellWidget(row, 1, value_combo)
            
            # SpinBox para Intensity
            intensity_spin = QSpinBox()
            intensity_spin.setRange(1, 1000)
            intensity_spin.setValue(intensity)
            intensity_spin.setSuffix(" ha")
            intensity_spin.setToolTip("One parcel per X hectares")
            intensity_spin.valueChanged.connect(self._emit_config_changed)
            self.intensity_table.setCellWidget(row, 2, intensity_spin)
        
        self._emit_config_changed()
        QMessageBox.information(
            self, 
            "Auto-mapping Complete", 
            f"Generated {len(field_values)} intensity mappings for field '{field_name}'.\n"
            "You can modify these values as needed."
        )

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
            self.refresh_csv_mappings()  # Refrescar ComboBoxes de mapeo
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
            
            # Actualizar estadísticas después de cargar columnas
            self._update_csv_statistics()
                    
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
        
        # ComboBox para GDF Field (desde Plan Operativo)
        gdf_field_combo = QComboBox()
        gdf_field_combo.setEditable(True)
        gdf_fields = self._get_available_fields()
        gdf_field_combo.addItems(gdf_fields)
        if gdf_fields:
            gdf_field_combo.setCurrentText(gdf_fields[0])
        gdf_field_combo.currentTextChanged.connect(self._on_mapping_changed)
        self.mapping_table.setCellWidget(row, 0, gdf_field_combo)
        
        # ComboBox para CSV Field (desde archivo CSV)
        csv_field_combo = QComboBox()
        csv_field_combo.setEditable(True)
        csv_fields = self._get_csv_fields()
        csv_field_combo.addItems(csv_fields)
        if csv_fields:
            csv_field_combo.setCurrentText(csv_fields[0])
        csv_field_combo.currentTextChanged.connect(self._on_mapping_changed)
        self.mapping_table.setCellWidget(row, 1, csv_field_combo)

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
            # Obtener campos disponibles
            csv_fields = self._get_csv_fields()
            gdf_fields = self._get_available_fields()
            
            if not csv_fields or not gdf_fields:
                QMessageBox.warning(self, "Auto-detect", "Could not read fields from CSV or GDF files.")
                return
            
            csv_columns = [col.lower() for col in csv_fields]
            gdf_columns = [col.lower() for col in gdf_fields]
            
            # Limpiar tabla actual
            self.mapping_table.setRowCount(0)
            
            # Agregar mapeos automáticos para campos comunes
            matched_fields = []
            for gdf_field in gdf_fields:
                for csv_field in csv_fields:
                    if gdf_field.lower() == csv_field.lower():
                        matched_fields.append((gdf_field, csv_field))
                        break
            
            # Crear filas para los campos coincidentes
            for gdf_field, csv_field in matched_fields:
                row = self.mapping_table.rowCount()
                self.mapping_table.insertRow(row)
                
                # ComboBox para GDF Field
                gdf_field_combo = QComboBox()
                gdf_field_combo.setEditable(True)
                gdf_field_combo.addItems(gdf_fields)
                gdf_field_combo.setCurrentText(gdf_field)
                gdf_field_combo.currentTextChanged.connect(self._on_mapping_changed)
                self.mapping_table.setCellWidget(row, 0, gdf_field_combo)
                
                # ComboBox para CSV Field
                csv_field_combo = QComboBox()
                csv_field_combo.setEditable(True)
                csv_field_combo.addItems(csv_fields)
                csv_field_combo.setCurrentText(csv_field)
                csv_field_combo.currentTextChanged.connect(self._on_mapping_changed)
                self.mapping_table.setCellWidget(row, 1, csv_field_combo)
            
            self._on_mapping_changed()
            QMessageBox.information(self, "Auto-detect", f"Detected {len(matched_fields)} matching fields.")
            
        except Exception as e:
            QMessageBox.warning(self, "Auto-detect Error", f"Error auto-detecting fields:\n{e}")

    def _on_mapping_changed(self) -> None:
        """Maneja cambios en los mapeos de campos."""
        # Actualizar lista interna de mapeos
        self._field_mappings = []
        for row in range(self.mapping_table.rowCount()):
            gdf_field_widget = self.mapping_table.cellWidget(row, 0)
            csv_field_widget = self.mapping_table.cellWidget(row, 1)
            
            if (isinstance(gdf_field_widget, QComboBox) and 
                isinstance(csv_field_widget, QComboBox)):
                
                gdf_field = gdf_field_widget.currentText().strip()
                csv_field = csv_field_widget.currentText().strip()
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
            "use_specific_intensity": self.specific_intensity_radio.isChecked(),
            "specific_intensities": {},
            "count_column_csv": self.count_column_combo.currentText(),
            "gridcode_column_csv": self.gridcode_column_combo.currentText(),
            "field_mappings": self._field_mappings.copy()
        }
        
        # Obtener intensidades específicas
        if self.specific_intensity_radio.isChecked():
            for row in range(self.intensity_table.rowCount()):
                field_widget = self.intensity_table.cellWidget(row, 0)
                value_widget = self.intensity_table.cellWidget(row, 1)
                intensity_widget = self.intensity_table.cellWidget(row, 2)
                
                if (isinstance(field_widget, QComboBox) and 
                    isinstance(value_widget, QComboBox) and 
                    isinstance(intensity_widget, QSpinBox)):
                    
                    field = field_widget.currentText().strip()
                    value = value_widget.currentText().strip()
                    intensity = intensity_widget.value()
                    
                    if field and value:
                        if field not in config["specific_intensities"]:
                            config["specific_intensities"][field] = {}
                        config["specific_intensities"][field][value] = intensity
        
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración al tab."""
        # Bloquear señales temporalmente
        self.method_button_group.blockSignals(True)
        self.base_intensity_spin.blockSignals(True)
        self.intensity_button_group.blockSignals(True)
        self.csv_path_line.blockSignals(True)
        
        try:
            # Método de muestreo
            use_csv = config.get("use_csv", False)
            if use_csv:
                self.csv_radio.setChecked(True)
            else:
                self.intensity_radio.setChecked(True)
            
            # Configuración de intensidad
            self.base_intensity_spin.setValue(config.get("base_intensity", 12))
            use_specific = config.get("use_specific_intensity", False)
            if use_specific:
                self.specific_intensity_radio.setChecked(True)
            else:
                self.base_intensity_radio.setChecked(True)
            
            # Intensidades específicas
            specific_intensities = config.get("specific_intensities", {})
            self.intensity_table.setRowCount(0)
            for field, values in specific_intensities.items():
                for value, intensity in values.items():
                    row = self.intensity_table.rowCount()
                    self.intensity_table.insertRow(row)
                    
                    # ComboBox para Field
                    field_combo = QComboBox()
                    field_combo.setEditable(True)
                    field_combo.addItems(self._get_available_fields())
                    field_combo.setCurrentText(field)
                    field_combo.currentTextChanged.connect(lambda text, r=row: self._on_field_changed(r, text))
                    self.intensity_table.setCellWidget(row, 0, field_combo)
                    
                    # ComboBox para Value
                    value_combo = QComboBox()
                    value_combo.setEditable(True)
                    value_combo.addItems(self._get_field_values(field))
                    value_combo.setCurrentText(value)
                    value_combo.currentTextChanged.connect(self._emit_config_changed)
                    self.intensity_table.setCellWidget(row, 1, value_combo)
                    
                    # SpinBox para Intensity
                    intensity_spin = QSpinBox()
                    intensity_spin.setRange(1, 1000)
                    intensity_spin.setValue(intensity)
                    intensity_spin.setSuffix(" ha")
                    intensity_spin.setToolTip("One parcel per X hectares")
                    intensity_spin.valueChanged.connect(self._emit_config_changed)
                    self.intensity_table.setCellWidget(row, 2, intensity_spin)
            
            # Configuración de CSV
            csv_path = config.get("csv_path", "")
            if csv_path:
                self.csv_path_line.setText(csv_path)
                # Cargar columnas del CSV para habilitar los ComboBoxes
                self._load_csv_columns(csv_path)
            
            # Configurar columnas CSV
            count_column = config.get("count_column_csv", "")
            if count_column:
                self.count_column_combo.setCurrentText(count_column)
            
            gridcode_column = config.get("gridcode_column_csv", "")
            if gridcode_column:
                self.gridcode_column_combo.setCurrentText(gridcode_column)
            
            # Mapeos de campos
            field_mappings = config.get("field_mappings", [])
            self.mapping_table.setRowCount(0)
            for gdf_field, csv_field in field_mappings:
                row = self.mapping_table.rowCount()
                self.mapping_table.insertRow(row)
                
                # ComboBox para GDF Field
                gdf_field_combo = QComboBox()
                gdf_field_combo.setEditable(True)
                gdf_fields = self._get_available_fields()
                gdf_field_combo.addItems(gdf_fields)
                gdf_field_combo.setCurrentText(gdf_field)
                gdf_field_combo.currentTextChanged.connect(self._on_mapping_changed)
                self.mapping_table.setCellWidget(row, 0, gdf_field_combo)
                
                # ComboBox para CSV Field
                csv_field_combo = QComboBox()
                csv_field_combo.setEditable(True)
                csv_fields = self._get_csv_fields()
                csv_field_combo.addItems(csv_fields)
                csv_field_combo.setCurrentText(csv_field)
                csv_field_combo.currentTextChanged.connect(self._on_mapping_changed)
                self.mapping_table.setCellWidget(row, 1, csv_field_combo)
            
            self._field_mappings = field_mappings.copy()
            
            # Actualizar visibilidad de secciones
            self._on_method_changed(self.csv_radio if use_csv else self.intensity_radio, True)
            
        finally:
            # Restaurar señales
            self.method_button_group.blockSignals(False)
            self.base_intensity_spin.blockSignals(False)
            self.intensity_button_group.blockSignals(False)
            self.csv_path_line.blockSignals(False)
            
            # Actualizar estados
            self._on_intensity_type_changed(
                self.specific_intensity_radio if use_specific else self.base_intensity_radio, 
                True
            )
            
            # Actualizar estadísticas CSV si estamos en modo CSV
            if use_csv:
                self._update_csv_statistics() 