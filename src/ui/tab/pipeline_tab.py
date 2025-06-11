# src/ui/tab/pipeline_tab.py

import os
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
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.form_layout.addRow(line)
        
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
        
        main_vbox.addWidget(csv_group)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        main_vbox.addWidget(line2)
        
        # Custom Parameters Section
        custom_label = QLabel("<b>Custom Parameters (only active when Style = 'custom'):</b>")
        main_vbox.addWidget(custom_label)
        
        # Intensity (for non-CSV mode)
        self.intensity_spin = self._create_spinbox(1, 1000, 80)
        self.intensity_label = QLabel("Intensity (ha per parcel):")
        self.form_layout.addRow(self.intensity_label, self.intensity_spin)
        
        # Min/Max Parcels
        self.min_parcels_spin = self._create_spinbox(0, 100, 1)
        self.form_layout.addRow("Min parcels per group:", self.min_parcels_spin)
        
        self.max_parcels_spin = self._create_spinbox(0, 1000, 20)
        self.form_layout.addRow("Max parcels per group:", self.max_parcels_spin)
        
        # Area and Distance Parameters
        self.min_area_spin = self._create_double_spinbox(0.01, 1000.0, 0.4, 0.01)
        self.form_layout.addRow("Min area (ha):", self.min_area_spin)
        
        self.buffer_spin = self._create_spinbox(-1000, 0, -30)
        self.form_layout.addRow("Buffer distance (m):", self.buffer_spin)
        
        self.min_distance_spin = self._create_double_spinbox(0.0, 1000.0, 80.0, 0.1)
        self.form_layout.addRow("Min distance between parcels (m):", self.min_distance_spin)
        
        # Additional Custom Parameters
        self.id_parcela_inicio_spin = self._create_spinbox(0, 999999, 0)
        self.form_layout.addRow("Starting Parcel ID:", self.id_parcela_inicio_spin)
        
        self.version_parcela_line = QLineEdit()
        self.version_parcela_line.setPlaceholderText("e.g., A, B, v1")
        self.form_layout.addRow("Parcel Version:", self.version_parcela_line)
        
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
        self.input_browse_btn.clicked.connect(self._select_input_file)
        self.select_group_fields_btn.clicked.connect(self._select_grouping_fields)
        self.output_browse_btn.clicked.connect(self._select_output_dir)
        self.csv_browse_btn.clicked.connect(self._select_csv_file)
        self.run_btn.clicked.connect(self.runRequested.emit)
        self.style_combo.currentTextChanged.connect(self._toggle_custom_params)
        self.use_csv_checkbox.stateChanged.connect(self._toggle_generation_method)
        self._toggle_custom_params(self.style_combo.currentText())
        self._toggle_generation_method()

        # CSV signals - NUEVOS
        self.csv_browse_btn.clicked.connect(self._select_csv_file)
        self.refresh_csv_fields_btn.clicked.connect(self._refresh_csv_fields)
        self.add_mapping_btn.clicked.connect(self._add_field_mapping)
        self.remove_mapping_btn.clicked.connect(self._remove_selected_mapping)
        self.auto_detect_mapping_btn.clicked.connect(self._auto_detect_field_mapping)
        self.csv_path_line.textChanged.connect(self._on_csv_path_changed)
        self.count_column_combo.currentTextChanged.connect(lambda: self.configChanged.emit(self.get_config()) if hasattr(self, 'configChanged') else None)

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
        else:
            self.count_column_combo.clear()
            self.csv_preview_text.clear()

    def _refresh_csv_fields(self):
        """Actualiza la lista de campos disponibles en el CSV."""
        csv_path = self.csv_path_line.text().strip()
        if not csv_path or not os.path.exists(csv_path):
            self.count_column_combo.clear()
            return
            
        try:
            import pandas as pd
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
                        
        except Exception as e:
            QMessageBox.warning(self, "CSV Error", f"Could not read CSV file:\n{e}")
            self.count_column_combo.clear()

    def _update_csv_preview(self):
        """Actualiza el preview del CSV."""
        csv_path = self.csv_path_line.text().strip()
        if not csv_path or not os.path.exists(csv_path):
            self.csv_preview_text.clear()
            return
            
        try:
            import pandas as pd
            df = pd.read_csv(csv_path, nrows=3)  # Solo 3 filas para preview
            df.columns = [str(col).lower() for col in df.columns]
            
            preview_text = f"CSV Preview ({len(df.columns)} columns, showing first 3 rows):\n\n"
            preview_text += df.to_string(index=False, max_cols=6)
            
            if len(df.columns) > 6:
                preview_text += f"\n... and {len(df.columns) - 6} more columns"
                
            self.csv_preview_text.setPlainText(preview_text)
            
        except Exception as e:
            self.csv_preview_text.setPlainText(f"Error reading CSV: {e}")

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
                from src.utils.gpkg_helpers import list_layers, list_fields
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
            from src.utils.gpkg_helpers import list_layers, list_fields
            import pandas as pd
            
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
        self.intensity_label.setVisible(not use_csv)
        self.intensity_spin.setVisible(not use_csv)

    def _toggle_custom_params(self, style: str):
        """Habilita/deshabilita los parámetros custom según el estilo seleccionado."""
        is_custom = (style == "custom")
        
        # Lista de todos los widgets de parámetros custom
        custom_widgets = [
            self.intensity_spin,
            self.min_parcels_spin,
            self.max_parcels_spin,
            self.min_area_spin,
            self.buffer_spin,
            self.min_distance_spin,
            self.id_parcela_inicio_spin,
            self.version_parcela_line
        ]
        
        # Habilitar/deshabilitar widgets
        for widget in custom_widgets:
            widget.setEnabled(is_custom)
            
        # Habilitar/deshabilitar labels asociados
        for i in range(self.form_layout.rowCount()):
            label = self.form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            field = self.form_layout.itemAt(i, QFormLayout.ItemRole.FieldRole)
            
            if label and field:
                label_widget = label.widget()
                field_widget = field.widget() if hasattr(field, 'widget') else field.layout()
                
                # Verificar si el field contiene alguno de nuestros custom widgets
                if field_widget and any(w == field_widget or (hasattr(field_widget, 'indexOf') and field_widget.indexOf(w) >= 0) for w in custom_widgets):
                    if label_widget and label_widget != self.intensity_label:  # La intensity_label se maneja separadamente
                        label_widget.setEnabled(is_custom)

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
        
        # Solo agregar overrides si es custom
        if style == "custom":
            overrides = {}
            
            # Parámetros de intensidad (solo si no usa CSV)
            if not use_csv:
                overrides["INTENSIDAD"] = self.intensity_spin.value()
            
            # Parámetros de límites de parcelas
            overrides["MIN_PARCELAS"] = self.min_parcels_spin.value() if self.min_parcels_spin.value() > 0 else None
            overrides["MAX_PARCELAS"] = self.max_parcels_spin.value() if self.max_parcels_spin.value() > 0 else None
            
            # Parámetros de área y distancia
            overrides["AREA_MINIMA_HA"] = self.min_area_spin.value()
            overrides["BUFFER_DISTANCE"] = self.buffer_spin.value()
            overrides["MIN_DISTANCE"] = self.min_distance_spin.value()
            
            # Parámetros de identificación
            overrides["ID_PARCELA_INICIO"] = self.id_parcela_inicio_spin.value()
            version_text = self.version_parcela_line.text().strip()
            if version_text:
                overrides["VERSION_PARCELA"] = version_text
            
            config["cfg_overrides"] = overrides
        
        # CSV mapping avanzado
        if use_csv:
            config["count_column_csv"] = self.count_column_combo.currentText()
            config["field_mappings"] = self._get_field_mappings()
        
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
        
        # Aplicar overrides si existen
        overrides = config.get("cfg_overrides", {})
        custom_params = config.get("custom_params", {})  # Para compatibilidad con formato anterior
        
        # Combinar ambos diccionarios, dando prioridad a cfg_overrides
        all_params = {**custom_params, **overrides}
        
        if all_params:
            self.intensity_spin.setValue(all_params.get("INTENSIDAD", all_params.get("intensity", 80)))
            self.min_parcels_spin.setValue(all_params.get("MIN_PARCELAS", 1))
            self.max_parcels_spin.setValue(all_params.get("MAX_PARCELAS", 20))
            self.min_area_spin.setValue(all_params.get("AREA_MINIMA_HA", 0.4))
            self.buffer_spin.setValue(all_params.get("BUFFER_DISTANCE", -30))
            self.min_distance_spin.setValue(all_params.get("MIN_DISTANCE", 80.0))
            self.id_parcela_inicio_spin.setValue(all_params.get("ID_PARCELA_INICIO", 0))
            self.version_parcela_line.setText(all_params.get("VERSION_PARCELA", ""))
        
        # Aplicar visibilidad según estilo
        self._toggle_custom_params(style)
        self._toggle_generation_method()
        
        # CSV mapping avanzado
        if config.get("use_csv"):
            count_column = config.get("count_column_csv", "")
            if count_column:
                count_index = self.count_column_combo.findText(count_column)
                if count_index >= 0:
                    self.count_column_combo.setCurrentIndex(count_index)
            
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