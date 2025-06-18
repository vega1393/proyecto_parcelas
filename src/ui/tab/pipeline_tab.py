# src/ui/tab/pipeline_tab.py

import os
import pandas as pd  # Movido al inicio para evitar imports repetidos
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox, 
    QSpinBox, QDoubleSpinBox, QHBoxLayout, QProgressBar, QFileDialog, 
    QScrollArea, QLabel, QCheckBox, QFrame, QMessageBox, QInputDialog, QDialog,
    QGroupBox, QTableWidget, QHeaderView, QTextEdit
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import Dict, Any, List

# Reutilizaremos el diálogo de selección de campos del PO, es perfecto para esto
from src.ui.dialogs.po_fields_dialog import POFieldsDialog
from src.utils.gpkg_helpers import list_layers, list_fields

class PipelineTab(QWidget):
    runRequested = pyqtSignal()
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        # Variable para guardar los campos de agrupación seleccionados
        self._grouping_fields: List[str] = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        main_vbox = QVBoxLayout(content_widget)
        self.form_layout = QFormLayout()
        main_vbox.addLayout(self.form_layout)

        # --- Input / Output ---
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Path to the input geographic file (e.g., .gpkg, .shp)")
        self.input_browse_btn = QPushButton("Browse...")
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(self.input_browse_btn)
        self.form_layout.addRow("Input File:", input_layout)
        
        # Sección para seleccionar campos de agrupación
        self.group_fields_label = QLabel("Using default fields from style config.")
        self.group_fields_label.setWordWrap(True)
        self.select_group_fields_btn = QPushButton("Select Fields...")
        group_fields_layout = QHBoxLayout()
        group_fields_layout.addWidget(self.group_fields_label, 1)
        group_fields_layout.addWidget(self.select_group_fields_btn)
        self.form_layout.addRow("Grouping Fields:", group_fields_layout)

        self.output_line = QLineEdit()
        self.output_line.setPlaceholderText("Path to the output directory")
        self.output_browse_btn = QPushButton("Browse...")
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(self.output_browse_btn)
        self.form_layout.addRow("Output Directory:", output_layout)
        
        # Style Selection
        self.style_combo = QComboBox()
        self.style_combo.addItems(["calibration", "control", "custom"])
        self.form_layout.addRow("Processing Style:", self.style_combo)
        
        # --- NUEVA SECCIÓN: Style Configuration Details ---
        self.style_config_group = QGroupBox("Style Configuration Details")
        style_config_layout = QVBoxLayout(self.style_config_group)
        
        # Información del estilo seleccionado
        self.style_info_text = QTextEdit()
        self.style_info_text.setMaximumHeight(120)
        self.style_info_text.setReadOnly(True)
        style_config_layout.addWidget(self.style_info_text)
        
        # --- SECCIÓN: Intensity Configuration ---
        intensity_group = QGroupBox("Intensity Configuration")
        intensity_layout = QVBoxLayout(intensity_group)
        
        # Base intensity
        base_intensity_layout = QFormLayout()
        self.base_intensity_spin = self._create_spinbox(10, 1000, 80)
        base_intensity_layout.addRow("Base Intensity (ha per parcel):", self.base_intensity_spin)
        intensity_layout.addLayout(base_intensity_layout)
        
        # Specific intensity toggle
        self.use_specific_intensity_checkbox = QCheckBox("Use specific intensity by land use type")
        self.use_specific_intensity_checkbox.setToolTip("Enable different intensities for different land use types")
        intensity_layout.addWidget(self.use_specific_intensity_checkbox)
        
        # Intensity by Type (dinámico según Plan Operativo)
        self.intensity_by_type_group = QGroupBox("Intensity by Land Use Type")
        self.intensity_by_type_layout = QFormLayout(self.intensity_by_type_group)
        
        # Botón para cargar tipos de uso desde PO
        load_po_types_layout = QHBoxLayout()
        self.load_po_types_btn = QPushButton("Load Types from Plan Operativo")
        self.load_po_types_btn.setToolTip("Load land use types from the configured Plan Operativo")
        self.manual_add_type_btn = QPushButton("Add Type Manually")
        self.clear_all_types_btn = QPushButton("Clear All")
        load_po_types_layout.addWidget(self.load_po_types_btn)
        load_po_types_layout.addWidget(self.manual_add_type_btn)
        load_po_types_layout.addWidget(self.clear_all_types_btn)
        load_po_types_layout.addStretch()
        self.intensity_by_type_layout.addRow(load_po_types_layout)
        
        # Contenedor dinámico para los tipos de uso
        self.land_use_scroll = QScrollArea()
        self.land_use_widget = QWidget()
        self.land_use_layout = QFormLayout(self.land_use_widget)
        self.land_use_scroll.setWidget(self.land_use_widget)
        self.land_use_scroll.setWidgetResizable(True)
        self.land_use_scroll.setMaximumHeight(200)
        
        # Diccionario para almacenar los spinboxes dinámicos
        self.intensity_spinboxes = {}
        
        self.intensity_by_type_layout.addRow(self.land_use_scroll)
        intensity_layout.addWidget(self.intensity_by_type_group)
        
        style_config_layout.addWidget(intensity_group)
        
        # Controles específicos por estilo
        style_params_group = QGroupBox("Style-Specific Parameters")
        self.style_params_layout = QFormLayout(style_params_group)
        
        # Status labels
        self.intensity_config_label = QLabel()
        self.style_params_layout.addRow("Current Config:", self.intensity_config_label)
        
        # Parcel Limits Configuration
        self.parcel_limits_group = QGroupBox("Parcel Count Limits")
        parcel_limits_layout = QFormLayout(self.parcel_limits_group)
        
        self.min_parcels_enabled_checkbox = QCheckBox("Enable minimum parcels limit")
        self.min_parcels_value_spin = self._create_spinbox(1, 100, 1)
        min_parcels_layout = QHBoxLayout()
        min_parcels_layout.addWidget(self.min_parcels_enabled_checkbox)
        min_parcels_layout.addWidget(self.min_parcels_value_spin)
        parcel_limits_layout.addRow("Minimum parcels:", min_parcels_layout)
        
        self.max_parcels_enabled_checkbox = QCheckBox("Enable maximum parcels limit")
        self.max_parcels_value_spin = self._create_spinbox(1, 1000, 20)
        max_parcels_layout = QHBoxLayout()
        max_parcels_layout.addWidget(self.max_parcels_enabled_checkbox)
        max_parcels_layout.addWidget(self.max_parcels_value_spin)
        parcel_limits_layout.addRow("Maximum parcels:", max_parcels_layout)
        
        style_config_layout.addWidget(self.parcel_limits_group)
        
        # Area and Distance Parameters
        self.area_distance_group = QGroupBox("Area and Distance Parameters")
        area_distance_layout = QFormLayout(self.area_distance_group)
        
        # EPSG/CRS Configuration
        self.projected_crs_spin = self._create_spinbox(1000, 99999, 32718)
        self.projected_crs_spin.setToolTip("EPSG code for the projected coordinate system (e.g., 32718 for UTM 18S)")
        area_distance_layout.addRow("Projected CRS (EPSG):", self.projected_crs_spin)
        
        self.min_area_value_spin = self._create_double_spinbox(0.01, 1000.0, 0.4, 0.01)
        area_distance_layout.addRow("Min area (ha):", self.min_area_value_spin)
        
        self.buffer_value_spin = self._create_spinbox(-1000, 0, -30)
        area_distance_layout.addRow("Buffer distance (m):", self.buffer_value_spin)
        
        self.min_distance_value_spin = self._create_double_spinbox(0.0, 1000.0, 80.0, 0.1)
        area_distance_layout.addRow("Min distance between parcels (m):", self.min_distance_value_spin)
        
        style_config_layout.addWidget(self.area_distance_group)
        
        # Parcel Identification Parameters
        self.parcel_id_group = QGroupBox("Parcel Identification")
        parcel_id_layout = QFormLayout(self.parcel_id_group)
        
        self.id_parcela_inicio_value_spin = self._create_spinbox(0, 999999, 0)
        parcel_id_layout.addRow("Starting Parcel ID:", self.id_parcela_inicio_value_spin)
        
        self.version_parcela_value_line = QLineEdit()
        self.version_parcela_value_line.setPlaceholderText("e.g., A, B, v1")
        parcel_id_layout.addRow("Parcel Version:", self.version_parcela_value_line)
        
        style_config_layout.addWidget(self.parcel_id_group)
        
        # Button to reset to default style values
        self.reset_style_btn = QPushButton("Reset to Style Defaults")
        self.reset_style_btn.setToolTip("Reset all parameters to the default values for the selected style")
        style_config_layout.addWidget(self.reset_style_btn)
        
        style_config_layout.addWidget(style_params_group)
        main_vbox.addWidget(self.style_config_group)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_vbox.addWidget(line)
        
        # CSV Mode Section - MEJORADO
        csv_group = QGroupBox("CSV Configuration for External Parcel Counts")
        csv_layout = QFormLayout(csv_group)
        
        self.use_csv_checkbox = QCheckBox("Use External CSV for Parcel Count")
        self.use_csv_checkbox.setToolTip("Enable to use a CSV file with predefined parcel counts per group")
        csv_layout.addRow(self.use_csv_checkbox)
        
        # CSV File Selection
        self.csv_path_line = QLineEdit()
        self.csv_path_line.setPlaceholderText("Path to the input CSV file")
        self.csv_browse_btn = QPushButton("Browse...")
        csv_file_layout = QHBoxLayout()
        csv_file_layout.addWidget(self.csv_path_line)
        csv_file_layout.addWidget(self.csv_browse_btn)
        self.csv_label = QLabel("CSV File:")
        csv_layout.addRow(self.csv_label, csv_file_layout)
        
        # CSV Field Mapping Section
        mapping_frame = QFrame()
        mapping_layout = QVBoxLayout(mapping_frame)
        
        # Count Column Selection
        count_layout = QHBoxLayout()
        self.count_column_combo = QComboBox()
        self.count_column_combo.setToolTip("Select the column in CSV that contains parcel counts")
        self.refresh_csv_fields_btn = QPushButton("Refresh Fields")
        count_layout.addWidget(self.count_column_combo)
        count_layout.addWidget(self.refresh_csv_fields_btn)
        csv_layout.addRow("Count Column (CSV):", count_layout)
        
        # GridCode Column Selection - NUEVO
        gridcode_layout = QHBoxLayout()
        self.gridcode_column_combo = QComboBox()
        self.gridcode_column_combo.setToolTip("Select the column in CSV that contains gridcode values (e.g., 'gridcode', 'sup_ha')")
        self.gridcode_column_combo.addItem("(Auto-detect 'gridcode')", "")
        gridcode_layout.addWidget(self.gridcode_column_combo)
        csv_layout.addRow("GridCode Column (CSV):", gridcode_layout)
        
        # Field Mapping Table
        mapping_label = QLabel("Field Mapping (GDF ↔ CSV):")
        mapping_label.setToolTip("Map fields between the input GDF and CSV for grouping")
        csv_layout.addRow(mapping_label)
        
        # Table for field mapping
        self.field_mapping_table = QTableWidget()
        self.field_mapping_table.setColumnCount(2)
        self.field_mapping_table.setHorizontalHeaderLabels(["GDF Field", "CSV Field"])
        self.field_mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.field_mapping_table.setMaximumHeight(120)
        mapping_layout.addWidget(self.field_mapping_table)
        
        # Buttons for mapping table
        mapping_btn_layout = QHBoxLayout()
        self.add_mapping_btn = QPushButton("Add Mapping")
        self.remove_mapping_btn = QPushButton("Remove Selected")
        self.auto_detect_mapping_btn = QPushButton("Auto-Detect")
        mapping_btn_layout.addWidget(self.add_mapping_btn)
        mapping_btn_layout.addWidget(self.remove_mapping_btn)
        mapping_btn_layout.addWidget(self.auto_detect_mapping_btn)
        mapping_btn_layout.addStretch()
        mapping_layout.addLayout(mapping_btn_layout)
        
        csv_layout.addRow(mapping_frame)
        
        # CSV Preview
        preview_label = QLabel("CSV Preview:")
        csv_layout.addRow(preview_label)
        
        self.csv_preview_text = QTextEdit()
        self.csv_preview_text.setMaximumHeight(80)
        self.csv_preview_text.setReadOnly(True)
        self.csv_preview_text.setPlaceholderText("CSV preview will appear here...")
        csv_layout.addRow(self.csv_preview_text)
        
        # NUEVO: CSV Statistics
        stats_label = QLabel("CSV Statistics:")
        csv_layout.addRow(stats_label)
        
        self.csv_stats_text = QTextEdit()
        self.csv_stats_text.setMaximumHeight(70)
        self.csv_stats_text.setReadOnly(True)
        self.csv_stats_text.setPlaceholderText("CSV statistics will appear here after selecting count column...")
        self.csv_stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #e8f5e8;
                border: 2px solid #28a745;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
                color: #155724;
            }
        """)
        csv_layout.addRow(self.csv_stats_text)
        
        main_vbox.addWidget(csv_group)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        main_vbox.addWidget(line2)
        
        # Legacy Parameters Section (for CSV mode compatibility)
        legacy_label = QLabel("<b>Legacy Parameters (for CSV mode):</b>")
        main_vbox.addWidget(legacy_label)
        
        # Intensity (for non-CSV mode)
        self.intensity_spin = self._create_spinbox(1, 1000, 80)
        self.intensity_label = QLabel("Base Intensity (ha per parcel):")
        self.form_layout.addRow(self.intensity_label, self.intensity_spin)
        
        # Run buttons and progress
        self.run_btn = QPushButton("Run Pipeline")
        self.stop_btn = QPushButton("Stop Process")
        self.stop_btn.setEnabled(False)
        run_stop_layout = QHBoxLayout()
        run_stop_layout.addWidget(self.run_btn)
        run_stop_layout.addWidget(self.stop_btn)
        main_vbox.addLayout(run_stop_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_vbox.addWidget(self.progress_bar)
        
        main_vbox.addStretch()
        main_layout.addWidget(scroll)

    def _create_spinbox(self, min_val, max_val, default):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        return spin
        
    def _create_double_spinbox(self, min_val, max_val, default, step):
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        return spin

    def _connect_signals(self) -> None:
        """Conecta todas las señales de los widgets."""
        # Señales básicas
        self.input_browse_btn.clicked.connect(self._select_input_file)
        self.select_group_fields_btn.clicked.connect(self._select_grouping_fields)
        self.output_browse_btn.clicked.connect(self._select_output_dir)
        self.run_btn.clicked.connect(self.runRequested.emit)
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        self.use_csv_checkbox.toggled.connect(self._toggle_generation_method)
        
        # Señales CSV
        self.csv_browse_btn.clicked.connect(self._select_csv_file)
        self.refresh_csv_fields_btn.clicked.connect(self._refresh_csv_fields)
        self.add_mapping_btn.clicked.connect(self._add_field_mapping)
        self.remove_mapping_btn.clicked.connect(self._remove_selected_mapping)
        self.auto_detect_mapping_btn.clicked.connect(self._auto_detect_field_mapping)
        self.csv_path_line.textChanged.connect(self._on_csv_path_changed)
        self.count_column_combo.currentTextChanged.connect(self._on_count_column_changed)
        self.gridcode_column_combo.currentTextChanged.connect(self._on_gridcode_column_changed)
        
        # Style signals
        self.reset_style_btn.clicked.connect(self._reset_to_style_defaults)
        
        # Intensity signals
        self.base_intensity_spin.valueChanged.connect(self._on_parameter_changed)
        self.use_specific_intensity_checkbox.toggled.connect(self._on_specific_intensity_toggled)
        
        # Land use type management signals
        self.load_po_types_btn.clicked.connect(self._load_po_land_use_types)
        self.manual_add_type_btn.clicked.connect(self._add_land_use_type_manually)
        self.clear_all_types_btn.clicked.connect(self._clear_all_land_use_types)
        
        # Parameter change signals (existing ones removed for dynamic spinboxes)
        self.min_parcels_enabled_checkbox.toggled.connect(self._on_parameter_changed)
        self.min_parcels_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.max_parcels_enabled_checkbox.toggled.connect(self._on_parameter_changed)
        self.max_parcels_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.projected_crs_spin.valueChanged.connect(self._on_parameter_changed)
        self.min_area_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.buffer_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.min_distance_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.id_parcela_inicio_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.version_parcela_value_line.textChanged.connect(self._on_parameter_changed)
        
        # Initialize style display
        self._on_style_changed(self.style_combo.currentText())

    def _select_grouping_fields(self):
        """Permite al usuario seleccionar campos de agrupación del archivo de entrada."""
        input_path = self.input_line.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Input File Needed", "Please select a valid input file first.")
            return

        try:
            layers = list_layers(input_path)
            if not layers:
                QMessageBox.warning(self, "No Layers Found", f"No layers found in {input_path}.")
                return
            
            layer_to_use = layers[0]
            if len(layers) > 1:
                layer, ok = QInputDialog.getItem(self, "Select Layer", "Select the layer to get fields from:", layers, 0, False)
                if not ok:
                    return
                layer_to_use = layer

            available_fields = list_fields(input_path, layer_to_use)
            if not available_fields:
                QMessageBox.information(self, "No Fields", f"No attribute fields found in layer '{layer_to_use}'.")
                return
            
            dialog = POFieldsDialog(available_fields, self._grouping_fields, self)
            dialog.setWindowTitle("Select Grouping Fields")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._grouping_fields = dialog.get_selected_fields()
                if self._grouping_fields:
                    self.group_fields_label.setText(", ".join(self._grouping_fields))
                else:
                    self.group_fields_label.setText("Using default fields from style config.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error Reading Fields", f"Could not list fields from the input file.\n\nError: {e}")

    def _select_input_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Input File", "", "Geo Files (*.shp *.gpkg *.geojson)")
        if path:
            self.input_line.setText(path)
            
    def _select_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_line.setText(path)
            
    def _select_csv_file(self):
        """Selecciona archivo CSV y actualiza campos disponibles."""
        path, _ = QFileDialog.getOpenFileName(self, "Select Input CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_path_line.setText(path)
            self._refresh_csv_fields()
            self._update_csv_preview()

    def _on_csv_path_changed(self):
        """Se ejecuta cuando cambia la ruta del CSV."""
        if os.path.exists(self.csv_path_line.text().strip()):
            self._refresh_csv_fields()
            self._update_csv_preview()
            self._update_csv_statistics()
        else:
            self.count_column_combo.clear()
            self.gridcode_column_combo.clear()
            self.gridcode_column_combo.addItem("(Auto-detect 'gridcode')", "")
            self.csv_preview_text.clear()
            self.csv_stats_text.clear()
    
    def _on_count_column_changed(self):
        """Se ejecuta cuando cambia la columna de conteo seleccionada."""
        self._update_csv_statistics()
        if hasattr(self, 'configChanged'):
            self.configChanged.emit(self.get_config())
    
    def _on_gridcode_column_changed(self):
        """Se ejecuta cuando cambia la columna de gridcode seleccionada."""
        self._update_csv_statistics()
        if hasattr(self, 'configChanged'):
            self.configChanged.emit(self.get_config())

    def _refresh_csv_fields(self):
        """Actualiza la lista de campos disponibles en el CSV."""
        csv_path = self.csv_path_line.text().strip()
        if not csv_path or not os.path.exists(csv_path):
            self.count_column_combo.clear()
            self.gridcode_column_combo.clear()
            self.gridcode_column_combo.addItem("(Auto-detect 'gridcode')", "")
            return
            
        try:
            df = pd.read_csv(csv_path, nrows=0)  # Solo headers
            df.columns = [str(col).lower() for col in df.columns]  # Normalizar
            
            # Actualizar combo de columna de conteo
            current_count = self.count_column_combo.currentText()
            self.count_column_combo.clear()
            self.count_column_combo.addItems(df.columns.tolist())
            
            # Tratar de restaurar selección o seleccionar por defecto
            if current_count and current_count in df.columns:
                self.count_column_combo.setCurrentText(current_count)
            else:
                # Autodetectar columna de conteo
                count_candidates = ['n', 'n_parcelas', 'count', 'num_parcels', 'parcels']
                for candidate in count_candidates:
                    if candidate in df.columns:
                        self.count_column_combo.setCurrentText(candidate)
                        break
            
            # NUEVO: Actualizar combo de columna de gridcode
            current_gridcode = self.gridcode_column_combo.currentData()
            self.gridcode_column_combo.clear()
            self.gridcode_column_combo.addItem("(Auto-detect 'gridcode')", "")
            
            # Agregar todas las columnas como opciones para gridcode
            for col in df.columns:
                self.gridcode_column_combo.addItem(col, col)
            
            # Tratar de restaurar selección o autodetectar
            if current_gridcode and current_gridcode in df.columns:
                index = self.gridcode_column_combo.findData(current_gridcode)
                if index >= 0:
                    self.gridcode_column_combo.setCurrentIndex(index)
            else:
                # Autodetectar columna de gridcode
                gridcode_candidates = ['gridcode', 'grid_code', 'sup_ha', 'code', 'stratum']
                for candidate in gridcode_candidates:
                    if candidate in df.columns:
                        index = self.gridcode_column_combo.findData(candidate)
                        if index >= 0:
                            self.gridcode_column_combo.setCurrentIndex(index)
                            break
                        
        except Exception as e:
            QMessageBox.warning(self, "CSV Error", f"Could not read CSV file:\n{e}")
            self.count_column_combo.clear()
            self.gridcode_column_combo.clear()
            self.gridcode_column_combo.addItem("(Auto-detect 'gridcode')", "")
            self.csv_stats_text.clear()

    def _update_csv_preview(self):
        """Actualiza el preview del CSV."""
        csv_path = self.csv_path_line.text().strip()
        if not csv_path or not os.path.exists(csv_path):
            self.csv_preview_text.clear()
            return
            
        try:
            df = pd.read_csv(csv_path, nrows=3)  # Solo 3 filas para preview
            df.columns = [str(col).lower() for col in df.columns]
            
            preview_text = f"CSV Preview ({len(df.columns)} columns, showing first 3 rows):\n\n"
            preview_text += df.to_string(index=False, max_cols=6)
            
            if len(df.columns) > 6:
                preview_text += f"\n... and {len(df.columns) - 6} more columns"
                
            self.csv_preview_text.setPlainText(preview_text)
            
        except Exception as e:
            self.csv_preview_text.setPlainText(f"Error reading CSV: {e}")
    
    def _update_csv_statistics(self):
        """Actualiza las estadísticas del CSV basándose en la columna de conteo seleccionada."""
        csv_path = self.csv_path_line.text().strip()
        count_column = self.count_column_combo.currentText()
        
        if not csv_path or not os.path.exists(csv_path) or not count_column:
            self.csv_stats_text.setPlainText("Select a valid CSV file and count column to see statistics.")
            return
            
        try:
            df = pd.read_csv(csv_path)
            df.columns = [str(col).lower() for col in df.columns]
            
            if count_column not in df.columns:
                self.csv_stats_text.setPlainText(f"Column '{count_column}' not found in CSV.")
                return
            
            # Convertir columna de conteo a numérico
            df[count_column] = pd.to_numeric(df[count_column], errors='coerce').fillna(0)
            
            # Calcular estadísticas básicas
            total_parcels = int(df[count_column].sum())
            groups_with_parcels = int((df[count_column] > 0).sum())
            total_groups = len(df)
            min_parcels = int(df[count_column].min())
            max_parcels = int(df[count_column].max())
            avg_parcels = df[count_column].mean()
            
            # Información adicional sobre gridcode si está configurado
            gridcode_column = self.gridcode_column_combo.currentData()
            gridcode_info = ""
            if gridcode_column and gridcode_column in df.columns:
                unique_gridcodes = df[gridcode_column].nunique()
                gridcode_info = f" | GridCodes únicos: {unique_gridcodes}"
            
            # Generar texto de estadísticas
            stats_text = f"📊 RESUMEN DEL CSV ({os.path.basename(csv_path)}):\n"
            stats_text += f"🎯 Total de parcelas a generar: {total_parcels:,}\n"
            stats_text += f"📦 Grupos con parcelas (≥1): {groups_with_parcels:,} de {total_groups:,} ({groups_with_parcels/total_groups*100:.1f}%){gridcode_info}\n"
            stats_text += f"📏 Rango por grupo: {min_parcels}-{max_parcels} parcelas (promedio: {avg_parcels:.1f})\n"
            
            # Agregar información sobre distribución por gridcode si existe
            if gridcode_column and gridcode_column in df.columns:
                stats_text += f"🔢 Distribución por GridCode: "
                gridcode_dist = df[df[count_column] > 0].groupby(gridcode_column)[count_column].sum().sort_values(ascending=False)
                dist_text = ", ".join([f"{k}({v})" for k, v in gridcode_dist.head(3).items()])
                stats_text += dist_text
                if len(gridcode_dist) > 3:
                    stats_text += f" +{len(gridcode_dist)-3} más"
            
            self.csv_stats_text.setPlainText(stats_text)
            
        except Exception as e:
            self.csv_stats_text.setPlainText(f"Error calculating statistics: {e}")

    def _add_field_mapping(self):
        """Agrega una nueva fila de mapeo de campos."""
        row = self.field_mapping_table.rowCount()
        self.field_mapping_table.insertRow(row)
        
        # Crear combos para GDF y CSV
        gdf_combo = QComboBox()
        csv_combo = QComboBox()
        
        # Llenar combo GDF
        input_path = self.input_line.text().strip()
        if input_path and os.path.exists(input_path):
            try:
                layers = list_layers(input_path)
                if layers:
                    fields = list_fields(input_path, layers[0])
                    gdf_combo.addItems([f.lower() for f in fields])
            except:
                pass
        
        # Llenar combo CSV
        if self.count_column_combo.count() > 0:
            csv_fields = [self.count_column_combo.itemText(i) for i in range(self.count_column_combo.count())]
            csv_combo.addItems(csv_fields)
        
        self.field_mapping_table.setCellWidget(row, 0, gdf_combo)
        self.field_mapping_table.setCellWidget(row, 1, csv_combo)

    def _remove_selected_mapping(self):
        """Remueve la fila de mapeo seleccionada."""
        current_row = self.field_mapping_table.currentRow()
        if current_row >= 0:
            self.field_mapping_table.removeRow(current_row)

    def _auto_detect_field_mapping(self):
        """Auto-detecta el mapeo de campos basado en nombres similares."""
        input_path = self.input_line.text().strip()
        csv_path = self.csv_path_line.text().strip()
        
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Auto-Detect", "Please select a valid input GDF file first.")
            return
            
        if not csv_path or not os.path.exists(csv_path):
            QMessageBox.warning(self, "Auto-Detect", "Please select a valid CSV file first.")
            return
        
        try:
            # Obtener campos de ambos archivos
            layers = list_layers(input_path)
            if not layers:
                return
                
            gdf_fields = [f.lower() for f in list_fields(input_path, layers[0])]
            
            df = pd.read_csv(csv_path, nrows=0)
            csv_fields = [str(col).lower() for col in df.columns]
            
            # Limpiar tabla actual
            self.field_mapping_table.setRowCount(0)
            
            # Buscar coincidencias
            matched_fields = []
            for gdf_field in gdf_fields:
                if gdf_field in csv_fields:
                    matched_fields.append((gdf_field, gdf_field))
            
            # Agregar mapeos detectados
            for gdf_field, csv_field in matched_fields:
                row = self.field_mapping_table.rowCount()
                self.field_mapping_table.insertRow(row)
                
                gdf_combo = QComboBox()
                csv_combo = QComboBox()
                
                gdf_combo.addItems(gdf_fields)
                csv_combo.addItems(csv_fields)
                
                gdf_combo.setCurrentText(gdf_field)
                csv_combo.setCurrentText(csv_field)
                
                self.field_mapping_table.setCellWidget(row, 0, gdf_combo)
                self.field_mapping_table.setCellWidget(row, 1, csv_combo)
            
            if matched_fields:
                QMessageBox.information(self, "Auto-Detect", f"Found {len(matched_fields)} matching field(s):\n" + 
                                      "\n".join([f"{gdf} ↔ {csv}" for gdf, csv in matched_fields]))
            else:
                QMessageBox.information(self, "Auto-Detect", "No matching fields found between GDF and CSV.")
                
        except Exception as e:
            QMessageBox.critical(self, "Auto-Detect Error", f"Error during auto-detection:\n{e}")

    def _get_field_mappings(self) -> List[tuple]:
        """Obtiene los mapeos de campos de la tabla."""
        mappings = []
        for row in range(self.field_mapping_table.rowCount()):
            gdf_combo = self.field_mapping_table.cellWidget(row, 0)
            csv_combo = self.field_mapping_table.cellWidget(row, 1)
            
            if gdf_combo and csv_combo:
                gdf_field = gdf_combo.currentText()
                csv_field = csv_combo.currentText()
                if gdf_field and csv_field:
                    mappings.append((gdf_field, csv_field))
        
        return mappings

    def _toggle_generation_method(self):
        """Maneja la visibilidad de controles según el modo CSV."""
        use_csv = self.use_csv_checkbox.isChecked()
        self.csv_label.setVisible(use_csv)
        self.csv_path_line.setVisible(use_csv)
        self.csv_browse_btn.setVisible(use_csv)
        
        # Legacy intensity control for CSV mode
        if hasattr(self, 'intensity_label') and hasattr(self, 'intensity_spin'):
            self.intensity_label.setVisible(not use_csv)
            self.intensity_spin.setVisible(not use_csv)

    def _on_style_changed(self, style: str) -> None:
        """Actualiza la información mostrada cuando cambia el estilo."""
        from src.config.config_base import get_config
        
        try:
            # Obtener la configuración del estilo
            config = get_config(style)
            
            # Actualizar información del estilo
            self._update_style_info(style, config)
            
            # Note: GridCode is now controlled exclusively from the GridCode Tab
            
            # Actualizar los controles con los valores del estilo (solo como referencia)
            self._load_style_configuration(config)
            
            # Actualizar visibilidad de controles
            self._update_controls_visibility(style, config)
            
        except Exception as e:
            self.style_info_text.setText(f"Error loading style configuration: {e}")
            
        # Mark that user may have changed gridcode manually after this point
        self._gridcode_user_set = True

    def _update_style_info(self, style: str, config: Dict[str, Any]) -> None:
        """Actualiza el texto informativo del estilo."""
        style_descriptions = {
            "calibration": {
                "title": "🎯 CALIBRATION Style",
                "purpose": "Optimized for LiDAR model calibration",
                "description": "Recommended to use GridCode stratification and specific intensities per land use type for scientific sampling."
            },
            "control": {
                "title": "🎮 CONTROL Style", 
                "purpose": "Controlled generation with strict limits",
                "description": "Uniform intensity with parcel count limits to ensure predictable results. GridCode optional."
            },
            "custom": {
                "title": "🔧 CUSTOM Style",
                "purpose": "Flexible configuration for specific needs", 
                "description": "Full flexibility - choose GridCode, intensity modes, and all parameters as needed."
            }
        }
        
        info = style_descriptions.get(style, {"title": "Unknown Style", "purpose": "", "description": ""})
        
        text = f"""<b>{info['title']}</b>
<i>{info['purpose']}</i>

{info['description']}

<b>Style Defaults:</b>
• Base Intensity: {config.get('INTENSIDAD', 'N/A')} ha/parcel
• Specific Intensities: {'✅ Enabled' if config.get('USE_INTENSIDAD_ESPECIFICA') else '❌ Disabled'}
• Min Parcels: {config.get('MIN_PARCELAS') if config.get('MIN_PARCELAS') is not None else 'No limit'}
• Max Parcels: {config.get('MAX_PARCELAS') if config.get('MAX_PARCELAS') is not None else 'No limit'}
• Min Area: {config.get('AREA_MINIMA_HA', 'N/A')} ha
• Buffer: {config.get('BUFFER_DISTANCE', 'N/A')} m
• Min Distance: {config.get('MIN_DISTANCE', 'N/A')} m

<b>Note:</b> GridCode and specific intensities can be configured independently above."""
        
        self.style_info_text.setHtml(text)

    def _load_style_configuration(self, config: Dict[str, Any]) -> None:
        """Carga los valores de configuración del estilo en los controles."""
        # Load base intensity
        base_intensity = config.get('INTENSIDAD', 80)
        self.base_intensity_spin.setValue(base_intensity)
        
        # Load specific intensity setting
        use_specific = config.get('USE_INTENSIDAD_ESPECIFICA', False)
        self.use_specific_intensity_checkbox.setChecked(use_specific)
        
        # Clear existing land use types and load from config
        self._clear_all_land_use_types()
        
        if use_specific:
            intensity_by_type = config.get('INTENSIDAD_POR_CAMPO', {}).get('tipouso', {})
            for land_type, intensity_value in intensity_by_type.items():
                self._add_land_use_type(land_type, intensity_value)
        
        # Update intensity configuration display
        if use_specific:
            intensity_by_type = config.get('INTENSIDAD_POR_CAMPO', {}).get('tipouso', {})
            if intensity_by_type:
                intensity_text = "✅ Specific by type: " + ", ".join([f"{k}:{v}" for k, v in intensity_by_type.items()])
            else:
                intensity_text = "✅ Enabled but no types defined"
        else:
            intensity_text = f"⚪ Uniform: {base_intensity} ha/parcel"
        self.intensity_config_label.setText(intensity_text)
        
        # Parcel limits
        min_parcels = config.get('MIN_PARCELAS')
        self.min_parcels_enabled_checkbox.setChecked(min_parcels is not None)
        self.min_parcels_value_spin.setValue(min_parcels if min_parcels is not None else 1)
        
        max_parcels = config.get('MAX_PARCELAS')
        self.max_parcels_enabled_checkbox.setChecked(max_parcels is not None)
        self.max_parcels_value_spin.setValue(max_parcels if max_parcels is not None else 20)
        
        # Area and distance parameters
        self.min_area_value_spin.setValue(config.get('AREA_MINIMA_HA', 0.4))
        self.buffer_value_spin.setValue(config.get('BUFFER_DISTANCE', -30))
        self.min_distance_value_spin.setValue(config.get('MIN_DISTANCE', 80.0))
        
        # Parcel identification
        self.id_parcela_inicio_value_spin.setValue(config.get('ID_PARCELA_INICIO', 0))
        self.version_parcela_value_line.setText(config.get('VERSION_PARCELA', ''))

    def _update_controls_visibility(self, style: str, config: Dict[str, Any]) -> None:
        """Actualiza la visibilidad y habilitación de controles según el estilo."""
        # GridCode is always available for any style
        # No restrictions here
        
        # Specific intensity is always configurable
        use_specific_intensity = self.use_specific_intensity_checkbox.isChecked()
        self.intensity_by_type_group.setVisible(use_specific_intensity)
        
        # Enable/disable controls based on style
        is_custom = (style == "custom")
        
        # In custom, most controls are editable; in others, some have restrictions
        self.parcel_limits_group.setEnabled(is_custom or style == "control")
        self.area_distance_group.setEnabled(is_custom)
        self.parcel_id_group.setEnabled(is_custom)
        
        # Intensity controls are always enabled but may have style-based recommendations
        self.base_intensity_spin.setEnabled(True)
        self.use_specific_intensity_checkbox.setEnabled(True)

    def _reset_to_style_defaults(self) -> None:
        """Resetea todos los parámetros a los valores por defecto del estilo."""
        style = self.style_combo.currentText()
        self._on_style_changed(style)
        QMessageBox.information(self, "Reset Complete", f"All parameters have been reset to {style} style defaults.")

    def _on_parameter_changed(self) -> None:
        """Emite señal cuando algún parámetro cambia."""
        # Opcional: emitir configuración actualizada
        self.configChanged.emit(self.get_config())

    def get_config(self) -> Dict[str, Any]:
        """Genera la configuración completa del pipeline tab."""
        use_csv = self.use_csv_checkbox.isChecked()
        style = self.style_combo.currentText()
        
        config = {
            "input_path": self.input_line.text().strip(),
            "output_dir": self.output_line.text().strip(),
            "style": style,
            "use_csv": use_csv,
            "csv_path": self.csv_path_line.text().strip() if use_csv else None,
            "grouping_fields": self._grouping_fields,
            "cfg_overrides": {}
        }
        
        # Get current style defaults to compare
        from src.config.config_base import get_config as get_style_config
        try:
            default_config = get_style_config(style)
        except:
            default_config = {}
        
        # Always include overrides for independent configurations
        overrides = {}
        
        # Note: GridCode is now controlled exclusively from the GridCode Tab
        
        # Base intensity (only if not using CSV)
        if not use_csv:
            base_intensity = self.base_intensity_spin.value()
            if base_intensity != default_config.get('INTENSIDAD', 80):
                overrides["INTENSIDAD"] = base_intensity
        
        # Specific intensity configuration
        use_specific_intensity = self.use_specific_intensity_checkbox.isChecked()
        if use_specific_intensity != default_config.get('USE_INTENSIDAD_ESPECIFICA', False):
            overrides["USE_INTENSIDAD_ESPECIFICA"] = use_specific_intensity
        
        # Intensity by type (if specific intensity is enabled)
        if use_specific_intensity and self.intensity_spinboxes:
            intensity_by_type = {}
            for land_type, widget_info in self.intensity_spinboxes.items():
                intensity_by_type[land_type] = widget_info['spinbox'].value()
            
            # CRITICAL FIX: Always include both when intensity types are configured
            # This ensures that user-configured land use types are always applied
            overrides["USE_INTENSIDAD_ESPECIFICA"] = True
            overrides["INTENSIDAD_POR_CAMPO"] = {"tipouso": intensity_by_type}
        elif not use_specific_intensity and default_config.get('USE_INTENSIDAD_ESPECIFICA', False):
            # Clear intensity by type if disabling specific intensity
            overrides["USE_INTENSIDAD_ESPECIFICA"] = False
            overrides["INTENSIDAD_POR_CAMPO"] = {}
        
        # Parcel limits
        if self.min_parcels_enabled_checkbox.isChecked():
            min_parcels = self.min_parcels_value_spin.value()
            if min_parcels != default_config.get('MIN_PARCELAS'):
                overrides["MIN_PARCELAS"] = min_parcels
        else:
            if default_config.get('MIN_PARCELAS') is not None:
                overrides["MIN_PARCELAS"] = None
        
        if self.max_parcels_enabled_checkbox.isChecked():
            max_parcels = self.max_parcels_value_spin.value()
            if max_parcels != default_config.get('MAX_PARCELAS'):
                overrides["MAX_PARCELAS"] = max_parcels
        else:
            if default_config.get('MAX_PARCELAS') is not None:
                overrides["MAX_PARCELAS"] = None
        
        # Area and distance parameters (only if custom style or changed)
        projected_crs = self.projected_crs_spin.value()
        if projected_crs != default_config.get('PROJECTED_CRS', 32718):
            overrides["PROJECTED_CRS"] = projected_crs
        
        min_area = self.min_area_value_spin.value()
        if min_area != default_config.get('AREA_MINIMA_HA', 0.4):
            overrides["AREA_MINIMA_HA"] = min_area
        
        buffer_distance = self.buffer_value_spin.value()
        if buffer_distance != default_config.get('BUFFER_DISTANCE', -30):
            overrides["BUFFER_DISTANCE"] = buffer_distance
        
        min_distance = self.min_distance_value_spin.value()
        if min_distance != default_config.get('MIN_DISTANCE', 80.0):
            overrides["MIN_DISTANCE"] = min_distance
        
        # Parcel identification
        id_inicio = self.id_parcela_inicio_value_spin.value()
        if id_inicio != default_config.get('ID_PARCELA_INICIO', 0):
            overrides["ID_PARCELA_INICIO"] = id_inicio
        
        version = self.version_parcela_value_line.text().strip()
        if version != default_config.get('VERSION_PARCELA', ''):
            overrides["VERSION_PARCELA"] = version
        
        # Always include overrides (even if empty for clarity)
        config["cfg_overrides"] = overrides
        
        # CSV mapping avanzado
        if use_csv:
            config["count_column_csv"] = self.count_column_combo.currentText()
            config["field_mappings"] = self._get_field_mappings()
            
            # NUEVO: Configuración de gridcode del CSV
            gridcode_column = self.gridcode_column_combo.currentData()
            if gridcode_column:  # Si no es auto-detect
                config["gridcode_column_csv"] = gridcode_column
        
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración a los widgets del tab."""
        self.input_line.setText(config.get("input_path", ""))
        self.output_line.setText(config.get("output_dir", ""))
        
        use_csv = config.get("use_csv", False)
        self.use_csv_checkbox.setChecked(use_csv)
        self.csv_path_line.setText(config.get("csv_path", ""))
        
        # Restaurar los campos de agrupación
        self._grouping_fields = config.get("grouping_fields", [])
        if self._grouping_fields:
            self.group_fields_label.setText(", ".join(self._grouping_fields))
        else:
            self.group_fields_label.setText("Using default fields from style config.")
        
        # Configurar estilo
        style = config.get("style", "calibration")
        style_index = self.style_combo.findText(style, Qt.MatchFlag.MatchFixedString)
        if style_index >= 0:
            self.style_combo.setCurrentIndex(style_index)
        
        # Get style defaults first
        from src.config.config_base import get_config as get_style_config
        try:
            default_config = get_style_config(style)
        except:
            default_config = {}
        
        # Aplicar overrides si existen
        overrides = config.get("cfg_overrides", {})
        custom_params = config.get("custom_params", {})  # Para compatibilidad con formato anterior
        
        # Combinar ambos diccionarios, dando prioridad a cfg_overrides
        all_params = {**custom_params, **overrides}
        
        # Note: GridCode is now controlled exclusively from the GridCode Tab
        
        # Base intensity
        base_intensity = all_params.get("INTENSIDAD", default_config.get("INTENSIDAD", 80))
        self.base_intensity_spin.setValue(base_intensity)
        
        # Specific intensity configuration
        use_specific_intensity = all_params.get("USE_INTENSIDAD_ESPECIFICA", default_config.get("USE_INTENSIDAD_ESPECIFICA", False))
        self.use_specific_intensity_checkbox.setChecked(use_specific_intensity)
        
        # Clear existing land use types
        self._clear_all_land_use_types()
        
        # Load intensity by type if enabled
        if use_specific_intensity:
            intensity_by_type = all_params.get("INTENSIDAD_POR_CAMPO", default_config.get("INTENSIDAD_POR_CAMPO", {}))
            if isinstance(intensity_by_type, dict) and "tipouso" in intensity_by_type:
                tipo_intensities = intensity_by_type["tipouso"]
                for land_type, intensity_value in tipo_intensities.items():
                    self._add_land_use_type(land_type, intensity_value)
        
        # Parcel limits
        min_parcels = all_params.get("MIN_PARCELAS", default_config.get("MIN_PARCELAS"))
        self.min_parcels_enabled_checkbox.setChecked(min_parcels is not None)
        self.min_parcels_value_spin.setValue(min_parcels if min_parcels is not None else 1)
        
        max_parcels = all_params.get("MAX_PARCELAS", default_config.get("MAX_PARCELAS"))
        self.max_parcels_enabled_checkbox.setChecked(max_parcels is not None)
        self.max_parcels_value_spin.setValue(max_parcels if max_parcels is not None else 20)
        
        # Area and distance parameters
        self.projected_crs_spin.setValue(all_params.get("PROJECTED_CRS", default_config.get("PROJECTED_CRS", 32718)))
        self.min_area_value_spin.setValue(all_params.get("AREA_MINIMA_HA", default_config.get("AREA_MINIMA_HA", 0.4)))
        self.buffer_value_spin.setValue(all_params.get("BUFFER_DISTANCE", default_config.get("BUFFER_DISTANCE", -30)))
        self.min_distance_value_spin.setValue(all_params.get("MIN_DISTANCE", default_config.get("MIN_DISTANCE", 80.0)))
        
        # Parcel identification
        self.id_parcela_inicio_value_spin.setValue(all_params.get("ID_PARCELA_INICIO", default_config.get("ID_PARCELA_INICIO", 0)))
        self.version_parcela_value_line.setText(all_params.get("VERSION_PARCELA", default_config.get("VERSION_PARCELA", "")))
        
        # Update style information and controls (but don't override user settings)
        self._update_style_info(style, default_config)
        self._update_controls_visibility(style, default_config)
        
        # Update intensity config label
        if use_specific_intensity:
            if self.intensity_spinboxes:
                types_text = ", ".join([f"{k}:{v['spinbox'].value()}" for k, v in self.intensity_spinboxes.items()])
                intensity_text = f"✅ Specific by type: {types_text}"
            else:
                intensity_text = "✅ Enabled but no types defined"
        else:
            intensity_text = f"⚪ Uniform: {base_intensity} ha/parcel"
        self.intensity_config_label.setText(intensity_text)
        
        # Apply visibility
        self._toggle_generation_method()
        
        # CSV mapping avanzado
        if config.get("use_csv"):
            count_column = config.get("count_column_csv", "")
            if count_column:
                count_index = self.count_column_combo.findText(count_column)
                if count_index >= 0:
                    self.count_column_combo.setCurrentIndex(count_index)
            
            # NUEVO: Restaurar configuración de gridcode del CSV
            gridcode_column = config.get("gridcode_column_csv", "")
            if gridcode_column:
                gridcode_index = self.gridcode_column_combo.findData(gridcode_column)
                if gridcode_index >= 0:
                    self.gridcode_column_combo.setCurrentIndex(gridcode_index)
            
            # Restaurar mapeos de campos
            field_mappings = config.get("field_mappings", [])
            self.field_mapping_table.setRowCount(0)
            for gdf_field, csv_field in field_mappings:
                self._add_field_mapping()
                row = self.field_mapping_table.rowCount() - 1
                
                gdf_combo = self.field_mapping_table.cellWidget(row, 0)
                csv_combo = self.field_mapping_table.cellWidget(row, 1)
                
                if gdf_combo and csv_combo:
                    gdf_index = gdf_combo.findText(gdf_field)
                    csv_index = csv_combo.findText(csv_field)
                    if gdf_index >= 0:
                        gdf_combo.setCurrentIndex(gdf_index)
                    if csv_index >= 0:
                        csv_combo.setCurrentIndex(csv_index)

    def set_running_state(self, is_running: bool):
        """Controla el estado de los botones durante la ejecución."""
        self.run_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)
        
    def update_progress(self, value: int):
        """Actualiza la barra de progreso."""
        self.progress_bar.setValue(value)

    def _on_specific_intensity_toggled(self, enabled: bool) -> None:
        """Maneja la activación/desactivación de intensidad específica."""
        self.intensity_by_type_group.setVisible(enabled)
        self._on_parameter_changed()

    def _load_po_land_use_types(self) -> None:
        """Carga los tipos de uso de suelo desde el Plan Operativo configurado."""
        try:
            # Obtener configuración del PO desde el tab correspondiente
            from src.ui.app import ParcelGeneratorApp
            main_window = self.parent()
            while main_window and not isinstance(main_window, ParcelGeneratorApp):
                main_window = main_window.parent()
            
            if not main_window:
                QMessageBox.warning(self, "Error", "Could not access main application window.")
                return
                
            po_config = main_window.po_tab.get_config()
            
            if not po_config.get("ruta") or not po_config.get("capa"):
                QMessageBox.warning(self, "PO Configuration Missing", 
                                  "Please configure the Plan Operativo in the PO tab first.")
                return
            
            # Open the new land use selection dialog
            from src.ui.dialogs.po_landuse_dialog import POLandUseDialog
            
            dialog = POLandUseDialog(po_config, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_field, selected_types = dialog.get_selected_types()
                
                if not selected_types:
                    QMessageBox.information(self, "No Types Selected", 
                                          "No land use types were selected.")
                    return
                
                # Clear existing types and add the selected ones
                self._clear_all_land_use_types()
                
                # Add each selected type with base intensity as default
                base_intensity = self.base_intensity_spin.value()
                for land_type in selected_types:
                    self._add_land_use_type(land_type, base_intensity)
                
                # Show success message with summary
                type_summary = ", ".join(selected_types[:5])
                if len(selected_types) > 5:
                    type_summary += f" and {len(selected_types) - 5} more"
                
                QMessageBox.information(self, "Success", 
                                      f"Loaded {len(selected_types)} land use types from field '{selected_field}':\n\n{type_summary}\n\nYou can now adjust the intensity values for each type.\n\n🔄 IMPORTANT: The pipeline filters will automatically use these types instead of the default configuration values.")
                
        except ImportError as e:
            QMessageBox.critical(self, "Import Error", 
                               f"Failed to import required dialog:\n{str(e)}\n\nPlease ensure all dependencies are installed.")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading PO Types", 
                               f"Failed to load land use types from Plan Operativo:\n{str(e)}")

    def _add_land_use_type_manually(self) -> None:
        """Permite agregar manualmente un tipo de uso de suelo."""
        land_type, ok = QInputDialog.getText(self, "Add Land Use Type", 
                                           "Enter land use type name:")
        if ok and land_type.strip():
            land_type = land_type.strip().upper()
            if land_type not in self.intensity_spinboxes:
                self._add_land_use_type(land_type, self.base_intensity_spin.value())
            else:
                QMessageBox.information(self, "Type Already Exists", 
                                      f"Land use type '{land_type}' already exists.")

    def _add_land_use_type(self, land_type: str, intensity_value: int = 100) -> None:
        """Agrega un tipo de uso de suelo con su control de intensidad."""
        if land_type in self.intensity_spinboxes:
            return
        
        # Crear layout horizontal para el tipo
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label del tipo
        type_label = QLabel(f"{land_type}:")
        type_label.setMinimumWidth(100)
        
        # Spinbox para intensidad
        spinbox = self._create_spinbox(10, 1000, intensity_value)
        spinbox.valueChanged.connect(self._on_parameter_changed)
        
        # Botón para eliminar este tipo
        remove_btn = QPushButton("×")
        remove_btn.setMaximumWidth(30)
        remove_btn.setToolTip(f"Remove {land_type}")
        remove_btn.clicked.connect(lambda: self._remove_land_use_type(land_type))
        
        row_layout.addWidget(type_label)
        row_layout.addWidget(spinbox)
        row_layout.addWidget(remove_btn)
        
        # Agregar al layout
        self.land_use_layout.addRow(row_widget)
        
        # Almacenar referencia
        self.intensity_spinboxes[land_type] = {
            'spinbox': spinbox,
            'row_widget': row_widget,
            'remove_btn': remove_btn
        }

    def _remove_land_use_type(self, land_type: str) -> None:
        """Elimina un tipo de uso de suelo."""
        if land_type in self.intensity_spinboxes:
            # Eliminar widget del layout
            widget_info = self.intensity_spinboxes[land_type]
            widget_info['row_widget'].setParent(None)
            
            # Eliminar del diccionario
            del self.intensity_spinboxes[land_type]
            
            self._on_parameter_changed()

    def _clear_all_land_use_types(self) -> None:
        """Elimina todos los tipos de uso de suelo."""
        for land_type in list(self.intensity_spinboxes.keys()):
            self._remove_land_use_type(land_type)