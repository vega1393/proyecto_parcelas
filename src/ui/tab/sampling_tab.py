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
from src.utils.dialog_utils import EnhancedFileDialog, create_csv_file_filter
from src.pipeline.distribucion_total import generar_preview_distribucion, _calcular_areas_por_grupo


class SamplingTab(QWidget):
    """
    Tab para configurar el método de muestreo y sus parámetros específicos.
    """
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._field_mappings: List[List[str]] = []
        self._grouping_fields: List[str] = []
        self.gdf_fields: List[str] = []
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
        self.total_radio = QRadioButton("Total-based (Proportional Distribution)")
        
        self.intensity_radio.setToolTip("Generate parcels based on intensity per hectare")
        self.csv_radio.setToolTip("Generate parcels based on counts from CSV file")
        self.total_radio.setToolTip("Distribute total number of parcels proportionally by area")
        
        # Por defecto, intensidad seleccionada
        self.intensity_radio.setChecked(True)
        
        self.method_button_group.addButton(self.intensity_radio, 0)
        self.method_button_group.addButton(self.csv_radio, 1)
        self.method_button_group.addButton(self.total_radio, 2)
        
        method_layout.addWidget(self.intensity_radio)
        method_layout.addWidget(self.csv_radio)
        method_layout.addWidget(self.total_radio)
        
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
        
        # --- Configuración de Total-based Distribution ---
        self.total_section = QGroupBox("🎯 Total-based Configuration")
        # Cambiar a un layout vertical principal
        total_main_layout = QVBoxLayout(self.total_section)
        
        # ===== Primera fila: Configuración básica =====
        basic_config_layout = QHBoxLayout()
        
        # Columna izquierda: Total de parcelas
        total_col_layout = QVBoxLayout()
        total_label = QLabel("Total Parcels:")
        total_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.total_parcels_spin = QSpinBox()
        self.total_parcels_spin.setRange(1, 100000)
        self.total_parcels_spin.setValue(230)
        self.total_parcels_spin.setSuffix(" parcels")
        self.total_parcels_spin.setToolTip("Total number of parcels to distribute")
        self.total_parcels_spin.setMinimumWidth(120)
        total_col_layout.addWidget(total_label)
        total_col_layout.addWidget(self.total_parcels_spin)
        
        # Columna derecha: Opciones principales
        options_col_layout = QVBoxLayout()
        options_label = QLabel("Options:")
        options_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.use_original_area_check = QCheckBox("Use original area (before filters)")
        self.use_original_area_check.setChecked(True)
        self.use_original_area_check.setToolTip("Calculate proportions based on original area before applying filters")
        self.show_preview_check = QCheckBox("Show distribution preview")
        self.show_preview_check.setChecked(True)
        self.show_preview_check.setToolTip("Display how parcels will be distributed before execution")
        options_col_layout.addWidget(options_label)
        options_col_layout.addWidget(self.use_original_area_check)
        options_col_layout.addWidget(self.show_preview_check)
        
        basic_config_layout.addLayout(total_col_layout)
        basic_config_layout.addStretch()
        basic_config_layout.addLayout(options_col_layout)
        total_main_layout.addLayout(basic_config_layout)
        
        # ===== Segunda fila: Campos de agrupamiento =====
        grouping_group = QGroupBox("Grouping Fields")
        grouping_layout = QVBoxLayout(grouping_group)
        
        # Tabla simple para campos de agrupamiento
        self.grouping_table = QTableWidget()
        self.grouping_table.setColumnCount(1)
        self.grouping_table.setHorizontalHeaderLabels(["Grouping Field"])
        self.grouping_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.grouping_table.setMinimumHeight(140)
        self.grouping_table.setToolTip("Fields used to create groups for proportional distribution")
        grouping_layout.addWidget(self.grouping_table)
        
        # Botones simples
        grouping_btn_layout = QHBoxLayout()
        self.add_grouping_btn = QPushButton("Add Field")
        self.remove_grouping_btn = QPushButton("Remove Selected")
        self.auto_grouping_btn = QPushButton("Add Default (tipouso)")
        
        grouping_btn_layout.addWidget(self.add_grouping_btn)
        grouping_btn_layout.addWidget(self.remove_grouping_btn)
        grouping_btn_layout.addWidget(self.auto_grouping_btn)
        grouping_btn_layout.addStretch()
        grouping_layout.addLayout(grouping_btn_layout)
        
        total_main_layout.addWidget(grouping_group)
        
        # ===== Tercera fila: Configuración de mínimos =====
        minimum_frame = QFrame()
        minimum_frame.setFrameStyle(QFrame.Shape.Box)
        minimum_frame.setLineWidth(1)
        minimum_frame.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 5px; padding: 5px; }")
        minimum_main_layout = QVBoxLayout(minimum_frame)
        
        minimum_header = QLabel("🔧 Minimum Parcels per Group")
        minimum_header.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        minimum_main_layout.addWidget(minimum_header)
        
        # Organizar opciones de mínimo en dos columnas
        minimum_options_layout = QHBoxLayout()
        
        # Columna izquierda: Opciones básicas
        left_min_layout = QVBoxLayout()
        self.minimum_button_group = QButtonGroup()
        
        self.no_minimum_radio = QRadioButton("No minimum (pure proportional)")
        self.no_minimum_radio.setToolTip("Some groups may get 0 parcels based on proportional distribution")
        self.no_minimum_radio.setChecked(True)
        
        self.min_one_radio = QRadioButton("Minimum 1 per group")
        self.min_one_radio.setToolTip("Every group gets at least 1 parcel")
        
        left_min_layout.addWidget(self.no_minimum_radio)
        left_min_layout.addWidget(self.min_one_radio)
        
        # Columna derecha: Opciones avanzadas
        right_min_layout = QVBoxLayout()
        
        # Mínimo personalizado
        min_custom_layout = QHBoxLayout()
        self.min_custom_radio = QRadioButton("Custom minimum:")
        self.min_custom_spin = QSpinBox()
        self.min_custom_spin.setRange(1, 100)
        self.min_custom_spin.setValue(2)
        self.min_custom_spin.setSuffix(" parcels")
        self.min_custom_spin.setEnabled(False)
        self.min_custom_spin.setMaximumWidth(100)
        min_custom_layout.addWidget(self.min_custom_radio)
        min_custom_layout.addWidget(self.min_custom_spin)
        min_custom_layout.addStretch()
        
        # Mínimo porcentual
        min_percent_layout = QHBoxLayout()
        self.min_percent_radio = QRadioButton("Percentage minimum:")
        self.min_percent_spin = QDoubleSpinBox()
        self.min_percent_spin.setRange(0.1, 50.0)
        self.min_percent_spin.setValue(0.5)
        self.min_percent_spin.setSuffix("%")
        self.min_percent_spin.setSingleStep(0.1)
        self.min_percent_spin.setDecimals(1)
        self.min_percent_spin.setEnabled(False)
        self.min_percent_spin.setMaximumWidth(100)
        min_percent_layout.addWidget(self.min_percent_radio)
        min_percent_layout.addWidget(self.min_percent_spin)
        min_percent_layout.addStretch()
        
        right_min_layout.addLayout(min_custom_layout)
        right_min_layout.addLayout(min_percent_layout)
        
        self.minimum_button_group.addButton(self.no_minimum_radio, 0)
        self.minimum_button_group.addButton(self.min_one_radio, 1)
        self.minimum_button_group.addButton(self.min_custom_radio, 2)
        self.minimum_button_group.addButton(self.min_percent_radio, 3)
        
        minimum_options_layout.addLayout(left_min_layout)
        minimum_options_layout.addLayout(right_min_layout)
        minimum_main_layout.addLayout(minimum_options_layout)
        
        total_main_layout.addWidget(minimum_frame)
        
        # ===== Cuarta fila: Vista previa de distribución =====
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.Shape.Box)
        preview_frame.setLineWidth(1)
        preview_frame.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 5px; padding: 5px; }")
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_header_layout = QHBoxLayout()
        preview_header = QLabel("📊 Distribution Preview")
        preview_header.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        
        # Botón para generar preview (más compacto)
        self.generate_preview_btn = QPushButton("Generate Preview")
        self.generate_preview_btn.setToolTip("Generate distribution preview based on current Plan Operativo")
        self.generate_preview_btn.setMaximumWidth(150)
        self.generate_preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """)
        
        preview_header_layout.addWidget(preview_header)
        preview_header_layout.addStretch()
        preview_header_layout.addWidget(self.generate_preview_btn)
        preview_layout.addLayout(preview_header_layout)
        
        # Área de texto para preview
        self.distribution_preview = QTextEdit()
        self.distribution_preview.setReadOnly(True)
        self.distribution_preview.setMaximumHeight(120)
        self.distribution_preview.setMinimumHeight(100)
        self.distribution_preview.setPlaceholderText("Click 'Generate Preview' to see parcel distribution...")
        self.distribution_preview.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                color: #495057;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                padding: 6px;
            }
        """)
        preview_layout.addWidget(self.distribution_preview)
        
        total_main_layout.addWidget(preview_frame)
        
        form_layout.addWidget(self.total_section)
        
        # Inicialmente ocultar secciones CSV y Total
        self.csv_section.setVisible(False)
        self.total_section.setVisible(False)
        
        # Agregar campo por defecto para Total-based
        self._add_default_grouping()

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
        
        # Total-based
        self.total_parcels_spin.valueChanged.connect(self._emit_config_changed)
        self.minimum_button_group.buttonToggled.connect(self._on_minimum_type_changed)
        self.min_custom_spin.valueChanged.connect(self._emit_config_changed)
        self.min_percent_spin.valueChanged.connect(self._emit_config_changed)
        self.use_original_area_check.toggled.connect(self._emit_config_changed)
        self.show_preview_check.toggled.connect(self._generate_distribution_preview)
        self.generate_preview_btn.clicked.connect(self._generate_distribution_preview)
        self.add_grouping_btn.clicked.connect(self._add_grouping_field)
        self.remove_grouping_btn.clicked.connect(self._remove_grouping_field)
        self.auto_grouping_btn.clicked.connect(self._add_default_grouping)
        self.grouping_table.cellChanged.connect(self._on_grouping_changed)

    def _on_method_changed(self, button, checked: bool) -> None:
        """Maneja el cambio de método de muestreo."""
        if not checked:
            return
            
        # Mostrar/ocultar secciones según el método seleccionado
        self.intensity_section.setVisible(button == self.intensity_radio)
        self.csv_section.setVisible(button == self.csv_radio)
        self.total_section.setVisible(button == self.total_radio)
        
        self._emit_config_changed()

    def _on_minimum_type_changed(self, button, checked: bool) -> None:
        """Maneja el cambio de tipo de mínimo para distribución total."""
        if not checked:
            return
            
        # Habilitar/deshabilitar controles según el tipo seleccionado
        self.min_custom_spin.setEnabled(button == self.min_custom_radio)
        self.min_percent_spin.setEnabled(button == self.min_percent_radio)
        
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
        field_combo.addItems(self.gdf_fields)
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
        """
        Returns the list of available GDF fields.
        This list is now updated externally via update_gdf_fields.
        """
        return self.gdf_fields

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
                            pass  # Error silenciado - no crítico para la funcionalidad
        
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
                            pass  # Error silenciado - no crítico para la funcionalidad
        
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
                            pass  # Error silenciado - no crítico para la funcionalidad
        
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
        file_path, _ = EnhancedFileDialog.get_open_file_name(
            self, "Select CSV File", 
            "", create_csv_file_filter()
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

    def _add_grouping_field(self) -> None:
        """Agrega un campo de agrupamiento a la tabla."""
        row = self.grouping_table.rowCount()
        self.grouping_table.insertRow(row)
        
        # ComboBox para el campo
        field_combo = QComboBox()
        field_combo.setEditable(True)
        field_combo.addItems(self._get_available_fields())
        field_combo.setCurrentText("tipouso")  # Valor por defecto
        field_combo.currentTextChanged.connect(self._on_grouping_changed)
        self.grouping_table.setCellWidget(row, 0, field_combo)
        
        self._emit_config_changed()

    def _remove_grouping_field(self) -> None:
        """Remueve el campo de agrupamiento seleccionado."""
        current_row = self.grouping_table.currentRow()
        if current_row >= 0:
            self.grouping_table.removeRow(current_row)
            self._on_grouping_changed()

    def _add_default_grouping(self) -> None:
        """Agrega el campo por defecto (tipouso) si no existe."""
        # Verificar si ya existe tipouso
        for row in range(self.grouping_table.rowCount()):
            widget = self.grouping_table.cellWidget(row, 0)
            if isinstance(widget, QComboBox) and widget.currentText() == "tipouso":
                return  # Ya existe
        
        # Agregar tipouso
        self._add_grouping_field()

    def _on_grouping_changed(self) -> None:
        """Maneja cambios en los campos de agrupamiento."""
        # Actualizar la lista interna
        self._grouping_fields = []
        for row in range(self.grouping_table.rowCount()):
            widget = self.grouping_table.cellWidget(row, 0)
            if isinstance(widget, QComboBox):
                field_name = widget.currentText().strip()
                if field_name and field_name not in self._grouping_fields:
                    self._grouping_fields.append(field_name)
        
        self._emit_config_changed()
    
    def _get_minimum_type(self) -> str:
        """Obtiene el tipo de mínimo seleccionado."""
        if self.no_minimum_radio.isChecked():
            return "none"
        elif self.min_one_radio.isChecked():
            return "one"
        elif self.min_custom_radio.isChecked():
            return "custom"
        elif self.min_percent_radio.isChecked():
            return "percent"
        return "none"
    
    def _get_minimum_value(self) -> float:
        """Obtiene el valor del mínimo según el tipo seleccionado."""
        if self.min_custom_radio.isChecked():
            return float(self.min_custom_spin.value())
        elif self.min_percent_radio.isChecked():
            return self.min_percent_spin.value()
        return 0.0

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual del sampling."""
        config = {
            "use_csv": self.csv_radio.isChecked(),
            "use_total": self.total_radio.isChecked(),
            "csv_path": self.csv_path_line.text().strip() if self.csv_radio.isChecked() else None,
            "base_intensity": self.base_intensity_spin.value(),
            "use_specific_intensity": self.specific_intensity_radio.isChecked(),
            "specific_intensities": {},
            "count_column_csv": self.count_column_combo.currentText(),
            "gridcode_column_csv": self.gridcode_column_combo.currentText(),
            "field_mappings": self._field_mappings.copy(),
            # Total-based configuration
            "total_parcels": self.total_parcels_spin.value(),
            "grouping_fields": self._grouping_fields.copy(),
            "minimum_type": self._get_minimum_type(),
            "minimum_value": self._get_minimum_value(),
            "use_original_area": self.use_original_area_check.isChecked(),
            "show_preview": self.show_preview_check.isChecked()
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
        self.total_parcels_spin.blockSignals(True)
        self.minimum_button_group.blockSignals(True)
        
        try:
            # Método de muestreo
            use_csv = config.get("use_csv", False)
            use_total = config.get("use_total", False)
            if use_csv:
                self.csv_radio.setChecked(True)
            elif use_total:
                self.total_radio.setChecked(True)
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
            
            # Configuración Total-based
            total_parcels = config.get("total_parcels", 800)
            self.total_parcels_spin.setValue(total_parcels)
            
            # Campos de agrupamiento
            grouping_fields = config.get("grouping_fields", [])
            self.grouping_table.setRowCount(0)
            self._grouping_fields = []
            for field_name in grouping_fields:
                row = self.grouping_table.rowCount()
                self.grouping_table.insertRow(row)
                
                # ComboBox para el campo
                field_combo = QComboBox()
                field_combo.setEditable(True)
                field_combo.addItems(self._get_available_fields())
                field_combo.setCurrentText(field_name)
                field_combo.currentTextChanged.connect(self._on_grouping_changed)
                self.grouping_table.setCellWidget(row, 0, field_combo)
                
                self._grouping_fields.append(field_name)
            
            minimum_type = config.get("minimum_type", "none")
            if minimum_type == "none":
                self.no_minimum_radio.setChecked(True)
            elif minimum_type == "one":
                self.min_one_radio.setChecked(True)
            elif minimum_type == "custom":
                self.min_custom_radio.setChecked(True)
            elif minimum_type == "percent":
                self.min_percent_radio.setChecked(True)
            
            minimum_value = config.get("minimum_value", 0.0)
            if minimum_type == "custom":
                self.min_custom_spin.setValue(int(minimum_value))
            elif minimum_type == "percent":
                self.min_percent_spin.setValue(minimum_value)
            
            self.use_original_area_check.setChecked(config.get("use_original_area", True))
            self.show_preview_check.setChecked(config.get("show_preview", True))
            
            # Actualizar visibilidad de secciones
            if use_csv:
                selected_button = self.csv_radio
            elif use_total:
                selected_button = self.total_radio
            else:
                selected_button = self.intensity_radio
            self._on_method_changed(selected_button, True)
            
        finally:
            # Restaurar señales
            self.method_button_group.blockSignals(False)
            self.base_intensity_spin.blockSignals(False)
            self.intensity_button_group.blockSignals(False)
            self.csv_path_line.blockSignals(False)
            self.total_parcels_spin.blockSignals(False)
            self.minimum_button_group.blockSignals(False)
            
            # Actualizar estados
            self._on_intensity_type_changed(
                self.specific_intensity_radio if use_specific else self.base_intensity_radio, 
                True
            )
            
            # Actualizar estado de controles de mínimo
            if use_total:
                minimum_type = config.get("minimum_type", "none")
                if minimum_type == "custom":
                    self._on_minimum_type_changed(self.min_custom_radio, True)
                elif minimum_type == "percent":
                    self._on_minimum_type_changed(self.min_percent_radio, True)
                else:
                    self._on_minimum_type_changed(self.no_minimum_radio, True)
            
            # Actualizar estadísticas CSV si estamos en modo CSV
            if use_csv:
                self._update_csv_statistics()

    def _generate_distribution_preview(self) -> None:
        """Genera y muestra el preview de distribución de parcelas total-based."""
        try:
            # Obtener información del archivo PO
            po_file_path, po_layer = self._get_po_file_info()
            if not po_file_path or not po_layer:
                self.distribution_preview.setText("❌ Error: No Plan Operativo file configured.")
                return
            
            if not os.path.exists(po_file_path):
                self.distribution_preview.setText(f"❌ Error: Plan Operativo file not found: {po_file_path}")
                return
            
            # Deshabilitar botón mientras genera preview
            self.generate_preview_btn.setEnabled(False)
            self.generate_preview_btn.setText("Generating...")
            
            # Leer datos del Plan Operativo
            gdf = gpd.read_file(po_file_path, layer=po_layer, engine='pyogrio')
            
            if gdf.empty:
                self.distribution_preview.setText("❌ Error: Plan Operativo file is empty.")
                return
            
            # Obtener configuración actual
            total_parcels = self.total_parcels_spin.value()
            minimum_type = self._get_minimum_type()
            minimum_value = self._get_minimum_value()
            use_original_area = self.use_original_area_check.isChecked()
            
            # Preparar configuración de mínimo
            minimum_config = {
                "type": minimum_type,
                "value": minimum_value
            }
            
            # Verificar que haya campos de agrupamiento configurados
            if not self._grouping_fields:
                self.distribution_preview.setText("❌ Error: No grouping fields configured. Please add at least one field.")
                return
            
            # Verificar que los campos existen en el GeoDataFrame
            missing_fields = [field for field in self._grouping_fields if field not in gdf.columns]
            if missing_fields:
                self.distribution_preview.setText(f"❌ Error: Fields not found in Plan Operativo: {', '.join(missing_fields)}")
                return
            
            # Calcular áreas por grupo usando los campos seleccionados
            areas_df = _calcular_areas_por_grupo(
                gdf=gdf,
                grouping_fields=self._grouping_fields,
                use_original_area=use_original_area
            )
            
            # Generar preview usando la función de distribucion_total.py
            preview_text = generar_preview_distribucion(
                areas_df=areas_df,
                total_parcels=total_parcels,
                minimum_config=minimum_config,
                max_groups=15  # Mostrar hasta 15 grupos en el preview
            )
            
            if preview_text:
                self.distribution_preview.setText(preview_text)
            else:
                self.distribution_preview.setText("❌ Error: Could not generate distribution preview.")
                
        except Exception as e:
            error_msg = f"❌ Error generating preview: {str(e)}"
            self.distribution_preview.setText(error_msg)
            print(f"Error in _generate_distribution_preview: {e}")
            
        finally:
            # Rehabilitar botón
            self.generate_preview_btn.setEnabled(True)
            self.generate_preview_btn.setText("Generate Preview")

    def update_gdf_fields(self, gdf_fields: List[str]) -> None:
        """
        Updates the list of available GDF fields from the main input layer.
        """
        self.gdf_fields = gdf_fields
        self._update_field_mapping_combos()
        self._update_grouping_fields_combos()
        self._update_intensity_fields_combos()

    def _update_combo_box_items(self, combo: QComboBox, items: List[str]) -> None:
        """Helper to update QComboBox items, preserving selection."""
        current_selection = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        if current_selection in items:
            combo.setCurrentText(current_selection)
        combo.blockSignals(False)

    def _update_field_mapping_combos(self) -> None:
        """Update the GDF Field dropdown in the mapping table."""
        for row in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                self._update_combo_box_items(combo, self.gdf_fields)

    def _update_grouping_fields_combos(self) -> None:
        """Update the Grouping Field dropdown in the grouping table."""
        for row in range(self.grouping_table.rowCount()):
            combo = self.grouping_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                self._update_combo_box_items(combo, self.gdf_fields)

    def _update_intensity_fields_combos(self) -> None:
        """Update the Field dropdown in the intensity table."""
        for row in range(self.intensity_table.rowCount()):
            combo = self.intensity_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                self._update_combo_box_items(combo, self.gdf_fields) 