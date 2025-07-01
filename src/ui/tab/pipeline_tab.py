# src/ui/tab/pipeline_tab_clean.py

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox, 
    QSpinBox, QDoubleSpinBox, QHBoxLayout, QProgressBar, QFileDialog, 
    QScrollArea, QLabel, QCheckBox, QFrame, QMessageBox, QDialog,
    QGroupBox, QTextEdit, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from typing import Dict, Any, List, Optional

# Reutilizaremos el diálogo de selección de campos del PO
from src.ui.dialogs.po_fields_dialog import POFieldsDialog
from src.ui.widgets_utils import create_spinbox, create_double_spinbox, create_style_combo
from src.utils.gpkg_helpers import list_layers, list_fields
from src.utils.dialog_utils import EnhancedFileDialog, create_geo_file_filter

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
        self.style_combo = create_style_combo()
        self.form_layout.addRow("Processing Style:", self.style_combo)
        
        # --- Configuration Summary ---
        self.config_summary_group = QGroupBox("Configuration Summary")
        config_summary_layout = QVBoxLayout(self.config_summary_group)
        
        # Botón para mostrar/ocultar resumen de configuración
        self.show_config_summary_btn = QPushButton("📋 Show Complete Configuration Summary")
        self.show_config_summary_btn.setCheckable(True)
        self.show_config_summary_btn.setToolTip("Click to show/hide a complete summary of all current configuration settings")
        self.show_config_summary_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:checked {
                background-color: #005a9e;
                border: 2px solid #007acc;
            }
        """)
        config_summary_layout.addWidget(self.show_config_summary_btn)
        
        # Área de texto para mostrar el resumen (inicialmente oculta)
        self.config_summary_text = QTextEdit()
        self.config_summary_text.setMaximumHeight(200)
        self.config_summary_text.setReadOnly(True)
        self.config_summary_text.setVisible(False)
        self.config_summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #007acc;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                font-weight: bold;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }
        """)
        config_summary_layout.addWidget(self.config_summary_text)
        

        
        # Parcel Limits Configuration
        self.parcel_limits_group = QGroupBox("Parcel Count Limits")
        parcel_limits_layout = QFormLayout(self.parcel_limits_group)
        
        self.min_parcels_enabled_checkbox = QCheckBox("Enable minimum parcels limit")
        self.min_parcels_value_spin = create_spinbox(1, 100, 1)
        min_parcels_layout = QHBoxLayout()
        min_parcels_layout.addWidget(self.min_parcels_enabled_checkbox)
        min_parcels_layout.addWidget(self.min_parcels_value_spin)
        parcel_limits_layout.addRow("Minimum parcels:", min_parcels_layout)
        
        self.max_parcels_enabled_checkbox = QCheckBox("Enable maximum parcels limit")
        self.max_parcels_value_spin = create_spinbox(1, 1000, 20)
        max_parcels_layout = QHBoxLayout()
        max_parcels_layout.addWidget(self.max_parcels_enabled_checkbox)
        max_parcels_layout.addWidget(self.max_parcels_value_spin)
        parcel_limits_layout.addRow("Maximum parcels:", max_parcels_layout)
        
        config_summary_layout.addWidget(self.parcel_limits_group)
        
        # Area and Distance Parameters
        self.area_distance_group = QGroupBox("Area and Distance Parameters")
        area_distance_layout = QFormLayout(self.area_distance_group)
        
        # EPSG/CRS Configuration
        self.projected_crs_spin = create_spinbox(1000, 99999, 31982)
        self.projected_crs_spin.setToolTip("EPSG code for the projected coordinate system (e.g., 31982 for SIRGAS 2000 UTM Zone 18S)")
        area_distance_layout.addRow("Projected CRS (EPSG):", self.projected_crs_spin)
        
        self.min_area_value_spin = create_double_spinbox(0.0, 1000.0, 0.3, 0.001)
        area_distance_layout.addRow("Min area (ha):", self.min_area_value_spin)
        
        self.buffer_value_spin = create_spinbox(-1000, 0, -20)
        area_distance_layout.addRow("Buffer distance (m):", self.buffer_value_spin)
        
        self.min_distance_value_spin = create_double_spinbox(0.0, 1000.0, 60.0, 0.1)
        area_distance_layout.addRow("Min distance between parcels (m):", self.min_distance_value_spin)
        
        # Quality Filters
        self.min_pixel_area_spin = create_spinbox(100, 1000, 399)
        self.min_pixel_area_spin.setToolTip("Minimum pixel area in m² to filter out noise pixels")
        area_distance_layout.addRow("Min pixel area (m²):", self.min_pixel_area_spin)
        
        self.min_p95_height_spin = create_double_spinbox(0.0, 10.0, 2.0, 0.1)
        self.min_p95_height_spin.setToolTip("Minimum p95 height to filter low vegetation pixels")
        area_distance_layout.addRow("Min p95 height:", self.min_p95_height_spin)
        
        self.parcel_area_spin = create_spinbox(100, 1000, 400)
        self.parcel_area_spin.setToolTip("Target area for each generated parcel in m²")
        area_distance_layout.addRow("Parcel area (m²):", self.parcel_area_spin)
        
        config_summary_layout.addWidget(self.area_distance_group)
        
        # Parcel Identification Parameters
        self.parcel_id_group = QGroupBox("Parcel Identification")
        parcel_id_layout = QFormLayout(self.parcel_id_group)
        
        self.id_parcela_inicio_value_spin = create_spinbox(0, 999999, 0)
        parcel_id_layout.addRow("Starting Parcel ID:", self.id_parcela_inicio_value_spin)
        
        self.version_parcela_value_line = QLineEdit()
        self.version_parcela_value_line.setPlaceholderText("e.g., A, B, v1")
        parcel_id_layout.addRow("Parcel Version:", self.version_parcela_value_line)
        
        config_summary_layout.addWidget(self.parcel_id_group)
        
        # Button to reset to default style values
        self.reset_style_btn = QPushButton("Reset to Style Defaults")
        self.reset_style_btn.setToolTip("Reset all parameters to the default values for the selected style")
        config_summary_layout.addWidget(self.reset_style_btn)
        main_vbox.addWidget(self.config_summary_group)
        
        # Nota informativa sobre controles de ejecución
        info_label = QLabel("ℹ️ Use the main Run Pipeline button at the top of the application to execute the pipeline.")
        info_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                border: 1px solid #2196f3;
                border-radius: 4px;
                padding: 8px;
                color: #1976d2;
                font-size: 12px;
            }
        """)
        info_label.setWordWrap(True)
        main_vbox.addWidget(info_label)
        
        # Progress Bar (mantener para compatibilidad)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_vbox.addWidget(self.progress_bar)
        
        main_layout.addWidget(scroll)
        
        # Initialize style defaults
        self._load_style_defaults()

    # Functions moved to src.ui.widgets_utils to avoid code duplication

    def _connect_signals(self) -> None:
        # File selection
        self.input_browse_btn.clicked.connect(self._browse_input_file)
        self.output_browse_btn.clicked.connect(self._browse_output_dir)
        self.select_group_fields_btn.clicked.connect(self._select_grouping_fields)
        
        # Style changes
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        self.reset_style_btn.clicked.connect(self._reset_to_style_defaults)
        
        # Configuration summary
        self.show_config_summary_btn.toggled.connect(self._toggle_config_summary)
        
        # Parameter changes
        self.input_line.textChanged.connect(self._on_parameter_changed)
        self.output_line.textChanged.connect(self._on_parameter_changed)
        self.projected_crs_spin.valueChanged.connect(self._on_parameter_changed)
        self.min_area_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.buffer_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.min_distance_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.id_parcela_inicio_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.version_parcela_value_line.textChanged.connect(self._on_parameter_changed)
        self.min_parcels_enabled_checkbox.toggled.connect(self._on_parameter_changed)
        self.min_parcels_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.max_parcels_enabled_checkbox.toggled.connect(self._on_parameter_changed)
        self.max_parcels_value_spin.valueChanged.connect(self._on_parameter_changed)
        self.min_pixel_area_spin.valueChanged.connect(self._on_parameter_changed)
        self.min_p95_height_spin.valueChanged.connect(self._on_parameter_changed)
        self.parcel_area_spin.valueChanged.connect(self._on_parameter_changed)

    def _select_grouping_fields(self):
        """Abre diálogo para seleccionar campos de agrupación."""
        input_path = self.input_line.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Warning", "Please select a valid input file first.")
            return

        try:
            # Obtener campos disponibles del archivo de entrada
            layers = list_layers(input_path)
            if not layers:
                QMessageBox.warning(self, "Warning", "No layers found in the input file.")
                return
            
            # Usar la primera capa por defecto
            layer_name = layers[0]
            available_fields = list_fields(input_path, layer_name)
            
            if not available_fields:
                QMessageBox.warning(self, "Warning", f"No fields found in layer '{layer_name}'.")
                return
            
            # Usar el diálogo de campos del PO
            dialog = POFieldsDialog(available_fields, self._grouping_fields, self)
            dialog.setWindowTitle("Select Grouping Fields")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._grouping_fields = dialog.get_selected_fields()
                self._update_grouping_fields_display()
                self._on_parameter_changed()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading input file:\n{e}")

    def _update_grouping_fields_display(self):
        """Actualiza la visualización de los campos de agrupación seleccionados."""
        if self._grouping_fields:
            fields_text = ", ".join(self._grouping_fields)
            self.group_fields_label.setText(fields_text)
        else:
            self.group_fields_label.setText("Using default fields from style config.")

    def _browse_input_file(self):
        """Opens a file dialog to select the input file."""
        file_path, _ = EnhancedFileDialog.get_open_file_name(
            self, "Select Input File", "", create_geo_file_filter()
        )
        if file_path:
            self.input_line.setText(file_path)

    def _browse_output_dir(self):
        """Opens a directory dialog to select the output directory."""
        dir_path = EnhancedFileDialog.get_existing_directory(self, "Select Output Directory")
        if dir_path:
            self.output_line.setText(dir_path)

    def _on_style_changed(self, style: str) -> None:
        """Maneja el cambio de estilo y carga la configuración por defecto."""
        self._load_style_defaults()
        self._on_parameter_changed()

    def _load_style_defaults(self) -> None:
        """Carga los valores por defecto del estilo seleccionado."""
        from src.config.config_base import get_config
        
        try:
            style = self.style_combo.currentText()
            config = get_config(style)
            self._load_style_configuration(config)
        except Exception as e:
            pass  # Error silenciado - no crítico, usa valores por defecto

    def _toggle_config_summary(self, checked: bool) -> None:
        """Muestra u oculta el resumen de configuración."""
        self.config_summary_text.setVisible(checked)
        if checked:
            self.show_config_summary_btn.setText("📋 Hide Configuration Summary")
            self._update_config_summary()
        else:
            self.show_config_summary_btn.setText("📋 Show Complete Configuration Summary")

    def _update_config_summary(self) -> None:
        """Actualiza el resumen completo de configuración."""
        try:
            # Obtener configuración actual
            config = self.get_config()
            cfg_overrides = config.get('cfg_overrides', {})
            
            # Construir resumen con HTML simplificado
            summary_html = """
            <div style="color: #00d4ff; font-size: 14px; font-weight: bold;">🔧 COMPLETE CONFIGURATION SUMMARY</div>
            <div style="color: #666666;">═══════════════════════════════════════════════════</div>
            <br>
            
            <div style="color: #ffb366; font-weight: bold;">📁 BASIC CONFIGURATION:</div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Input File: <span style="color: #90ee90; font-weight: bold;">{input_file}</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Output Directory: <span style="color: #90ee90; font-weight: bold;">{output_dir}</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Processing Style: <span style="color: #90ee90; font-weight: bold;">{style}</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Grouping Fields: <span style="color: #90ee90; font-weight: bold;">{grouping_fields}</span></div>
            <br>
            
            <div style="color: #ffb366; font-weight: bold;">📐 AREA & DISTANCE PARAMETERS:</div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• EPSG Code: <span style="color: #90ee90; font-weight: bold;">{epsg}</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Min Area: <span style="color: #90ee90; font-weight: bold;">{min_area} ha</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Buffer Distance: <span style="color: #90ee90; font-weight: bold;">{buffer} m</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Min Distance between parcels: <span style="color: #90ee90; font-weight: bold;">{min_distance} m</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Min pixel area: <span style="color: #90ee90; font-weight: bold;">{min_pixel_area} m²</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Min p95 height: <span style="color: #90ee90; font-weight: bold;">{min_p95_height}</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Parcel area: <span style="color: #90ee90; font-weight: bold;">{parcel_area} m²</span></div>
            <br>
            
            <div style="color: #ffb366; font-weight: bold;">📊 PARCEL COUNT LIMITS:</div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Minimum parcels: {min_parcels_status}</div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Maximum parcels: {max_parcels_status}</div>
            <br>
            
            <div style="color: #ffb366; font-weight: bold;">🏷️ PARCEL IDENTIFICATION:</div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Starting Parcel ID: <span style="color: #90ee90; font-weight: bold;">{start_id}</span></div>
            <div style="color: #ffffff;">&nbsp;&nbsp;• Parcel Version: <span style="color: #90ee90; font-weight: bold;">{version}</span></div>
            <br>
            
            <div style="color: #ffb366; font-weight: bold;">ℹ️ OTHER CONFIGURATIONS:</div>
            <div style="color: #87ceeb; font-style: italic;">&nbsp;&nbsp;• Sampling Method: See 'Sampling Method' tab</div>
            <div style="color: #87ceeb; font-style: italic;">&nbsp;&nbsp;• Plan Operativo: See 'Plan Operativo (PO)' tab</div>
            <div style="color: #87ceeb; font-style: italic;">&nbsp;&nbsp;• GridCode: See 'GridCode' tab</div>
            <div style="color: #87ceeb; font-style: italic;">&nbsp;&nbsp;• Exclusion Layers: See 'Exclusion Layers' tab</div>
            <div style="color: #87ceeb; font-style: italic;">&nbsp;&nbsp;• Delivery Settings: See 'Delivery' tab</div>
            <div style="color: #87ceeb; font-style: italic;">&nbsp;&nbsp;• Column Order: See 'Column Order' tab</div>
            """.format(
                input_file=os.path.basename(config.get('input_path', 'Not set')),
                output_dir=os.path.basename(config.get('output_dir', 'Not set')),
                style=config.get('style', 'Not set').upper(),
                grouping_fields=', '.join(config.get('grouping_fields', [])) if config.get('grouping_fields', []) else 'Using style defaults',
                epsg=cfg_overrides.get('PROJECTED_CRS', 'Not set'),
                min_area=cfg_overrides.get('AREA_MINIMA_HA', 'Not set'),
                buffer=cfg_overrides.get('BUFFER_DISTANCE', 'Not set'),
                min_distance=cfg_overrides.get('MIN_DISTANCE', 'Not set'),
                min_pixel_area=cfg_overrides.get('MIN_PIXEL_AREA_M2', 'Not set'),
                min_p95_height=cfg_overrides.get('MIN_P95_HEIGHT', 'Not set'),
                parcel_area=cfg_overrides.get('AREA_PARCELA', 'Not set'),
                min_parcels_status=f'<span class="enabled">{cfg_overrides.get("MIN_PARCELAS", "Not set")} (ENABLED)</span>' if cfg_overrides.get('MIN_PARCELAS_HABILITADO', False) else '<span class="disabled">DISABLED</span>',
                max_parcels_status=f'<span class="enabled">{cfg_overrides.get("MAX_PARCELAS", "Not set")} (ENABLED)</span>' if cfg_overrides.get('MAX_PARCELAS_HABILITADO', False) else '<span class="disabled">DISABLED</span>',
                start_id=cfg_overrides.get('ID_PARCELA_INICIO', 'Not set'),
                version=cfg_overrides.get('VERSION_PARCELA', '') if cfg_overrides.get('VERSION_PARCELA', '') else 'Not set'
            )
            
            # Establecer el HTML
            self.config_summary_text.setHtml(summary_html)
            
        except Exception as e:
            self.config_summary_text.setText(f"Error generating configuration summary: {e}")

    def _load_style_configuration(self, config: Dict[str, Any]) -> None:
        """Carga la configuración del estilo en los controles."""
        # Bloquear señales temporalmente
        self.projected_crs_spin.blockSignals(True)
        self.min_area_value_spin.blockSignals(True)
        self.buffer_value_spin.blockSignals(True)
        self.min_distance_value_spin.blockSignals(True)
        self.min_pixel_area_spin.blockSignals(True)
        self.min_p95_height_spin.blockSignals(True)
        self.parcel_area_spin.blockSignals(True)
        
        try:
            # Aplicar valores del estilo
            self.projected_crs_spin.setValue(config.get("PROJECTED_CRS", 31982))
            self.min_area_value_spin.setValue(config.get("AREA_MINIMA_HA", 0.3))
            self.buffer_value_spin.setValue(config.get("BUFFER_DISTANCE", -20))
            self.min_distance_value_spin.setValue(config.get("MIN_DISTANCE", 60.0))
            self.min_pixel_area_spin.setValue(config.get("MIN_PIXEL_AREA_M2", 399))
            self.min_p95_height_spin.setValue(config.get("MIN_P95_HEIGHT", 2.0))
            self.parcel_area_spin.setValue(config.get("AREA_PARCELA", 400))
            
            # Actualizar campos de agrupación si no hay selección manual
            if not self._grouping_fields:
                default_fields = config.get("FIELDS", [])
                if default_fields:
                    self._grouping_fields = default_fields
                    self._update_grouping_fields_display()
            
            # Configurar límites de parcelas basado en el estilo
            min_parcelas = config.get("MIN_PARCELAS")
            max_parcelas = config.get("MAX_PARCELAS")
            
            self.min_parcels_enabled_checkbox.setChecked(min_parcelas is not None)
            self.min_parcels_value_spin.setValue(min_parcelas if min_parcelas is not None else 1)
            
            self.max_parcels_enabled_checkbox.setChecked(max_parcelas is not None)
            self.max_parcels_value_spin.setValue(max_parcelas if max_parcelas is not None else 20)
        
        finally:
            # Restaurar señales
            self.projected_crs_spin.blockSignals(False)
            self.min_area_value_spin.blockSignals(False)
            self.buffer_value_spin.blockSignals(False)
            self.min_distance_value_spin.blockSignals(False)
            self.min_pixel_area_spin.blockSignals(False)
            self.min_p95_height_spin.blockSignals(False)
            self.parcel_area_spin.blockSignals(False)

    def _reset_to_style_defaults(self) -> None:
        """Resetea todos los parámetros a los valores por defecto del estilo."""
        current_style = self.style_combo.currentText()
        self._on_style_changed(current_style)

    def _on_parameter_changed(self) -> None:
        """Emite la señal cuando algún parámetro cambia."""
        config = self.get_config()
        self.configChanged.emit(config)
        
        # Actualizar resumen si está visible
        if self.config_summary_text.isVisible():
            self._update_config_summary()

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual del pipeline."""
        return {
            "input_path": self.input_line.text().strip(),
            "output_dir": self.output_line.text().strip(),
            "style": self.style_combo.currentText(),
            "grouping_fields": self._grouping_fields,
            "cfg_overrides": {
                "PROJECTED_CRS": self.projected_crs_spin.value(),
                "AREA_MINIMA_HA": self.min_area_value_spin.value(),
                "BUFFER_DISTANCE": self.buffer_value_spin.value(),
                "MIN_DISTANCE": self.min_distance_value_spin.value(),
                "MIN_PIXEL_AREA_M2": self.min_pixel_area_spin.value(),
                "MIN_P95_HEIGHT": self.min_p95_height_spin.value(),
                "AREA_PARCELA": self.parcel_area_spin.value(),
                "ID_PARCELA_INICIO": self.id_parcela_inicio_value_spin.value(),
                "VERSION_PARCELA": self.version_parcela_value_line.text().strip(),
                "MIN_PARCELAS_HABILITADO": self.min_parcels_enabled_checkbox.isChecked(),
                "MIN_PARCELAS": self.min_parcels_value_spin.value(),
                "MAX_PARCELAS_HABILITADO": self.max_parcels_enabled_checkbox.isChecked(),
                "MAX_PARCELAS": self.max_parcels_value_spin.value()
            }
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración al pipeline tab."""
        # Bloquear señales
        self.input_line.blockSignals(True)
        self.output_line.blockSignals(True)
        self.style_combo.blockSignals(True)
        
        try:
            # Configuración básica
            self.input_line.setText(config.get("input_path", ""))
            self.output_line.setText(config.get("output_dir", ""))
            
            style = config.get("style", "calibration")
            if style in ["calibration", "control", "custom"]:
                self.style_combo.setCurrentText(style)
            
            # Campos de agrupación
            self._grouping_fields = config.get("grouping_fields", [])
            self._update_grouping_fields_display()
            
            # Overrides de configuración
            cfg_overrides = config.get("cfg_overrides", {})
            if cfg_overrides:
                self.projected_crs_spin.setValue(cfg_overrides.get("PROJECTED_CRS", 31982))
                self.min_area_value_spin.setValue(cfg_overrides.get("AREA_MINIMA_HA", 0.3))
                self.buffer_value_spin.setValue(cfg_overrides.get("BUFFER_DISTANCE", -20))
                self.min_distance_value_spin.setValue(cfg_overrides.get("MIN_DISTANCE", 60.0))
                self.min_pixel_area_spin.setValue(cfg_overrides.get("MIN_PIXEL_AREA_M2", 399))
                self.min_p95_height_spin.setValue(cfg_overrides.get("MIN_P95_HEIGHT", 2.0))
                self.parcel_area_spin.setValue(cfg_overrides.get("AREA_PARCELA", 400))
                self.id_parcela_inicio_value_spin.setValue(cfg_overrides.get("ID_PARCELA_INICIO", 0))
                self.version_parcela_value_line.setText(cfg_overrides.get("VERSION_PARCELA", ""))
                self.min_parcels_enabled_checkbox.setChecked(cfg_overrides.get("MIN_PARCELAS_HABILITADO", False))
                min_parcelas = cfg_overrides.get("MIN_PARCELAS", 1)
                self.min_parcels_value_spin.setValue(min_parcelas if min_parcelas is not None else 1)
                self.max_parcels_enabled_checkbox.setChecked(cfg_overrides.get("MAX_PARCELAS_HABILITADO", False))
                max_parcelas = cfg_overrides.get("MAX_PARCELAS", 20)
                self.max_parcels_value_spin.setValue(max_parcelas if max_parcelas is not None else 20)
        
        finally:
            # Restaurar señales
            self.input_line.blockSignals(False)
            self.output_line.blockSignals(False)
            self.style_combo.blockSignals(False)
            
            # Solo cargar configuración del estilo si no hay cfg_overrides específicos
            # Esto evita sobrescribir valores guardados con defaults del estilo
            if not cfg_overrides:
                self._load_style_defaults()
            
            # Actualizar resumen si está visible
            if self.config_summary_text.isVisible():
                self._update_config_summary()

    def set_running_state(self, is_running: bool):
        """Actualiza el estado de la barra de progreso local."""
        self.progress_bar.setVisible(is_running)
        if not is_running:
            self.progress_bar.setValue(0)
        
    def update_progress(self, value: int):
        """Actualiza la barra de progreso."""
        self.progress_bar.setValue(value)