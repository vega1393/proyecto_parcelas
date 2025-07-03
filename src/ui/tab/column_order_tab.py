#!/usr/bin/env python3
"""
Tab for reordering columns in output files.
"""

import os
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QLabel, QScrollArea, QGroupBox,
    QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
    QTextEdit, QComboBox, QCheckBox, QSplitter, QSizePolicy,
    QSpinBox, QDoubleSpinBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from src.utils.dialog_utils import EnhancedFileDialog, get_initial_directory_from_path

try:
    import geopandas as gpd
    import pyogrio
    from osgeo import ogr, gdal
    GEOPANDAS_AVAILABLE = True
    GDAL_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    GDAL_AVAILABLE = False


class DraggableListWidget(QListWidget):
    """Lista con funcionalidad de drag and drop para reordenar elementos."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Configurar scroll nativo del QListWidget
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        
        # Política de tamaño para permitir scroll
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def dropEvent(self, event: QDropEvent) -> None:
        """Override para emitir señal cuando se complete el drop."""
        super().dropEvent(event)
        # Emitir señal personalizada para actualizar preview
        if hasattr(self.parent(), '_update_preview'):
            self.parent()._update_preview()


class ColumnOrderTab(QWidget):
    """
    Tab para reordenar columnas en archivos de salida.
    """
    configChanged = pyqtSignal(dict)
    request_pipeline_output = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._current_file_path = None
        self._current_layer = None  # Para manejar capas de GPKG
        self._original_columns = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Inicializa la interfaz de usuario del tab de ordenamiento de columnas."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # Verificar disponibilidad de GeoPandas
        if not GEOPANDAS_AVAILABLE:
            warning_layout = QVBoxLayout()
            warning_label = QLabel("⚠️ GeoPandas/PyOGRIO not available")
            warning_label.setStyleSheet("color: red; font-weight: bold; padding: 10px; background-color: #ffe6e6; border: 1px solid red;")
            warning_layout.addWidget(warning_label)
            
            info_text = QTextEdit()
            info_text.setMaximumHeight(100)
            info_text.setReadOnly(True)
            info_text.setPlainText(
                "Column reordering functionality requires GeoPandas and PyOGRIO.\n"
                "Install with: pip install geopandas pyogrio\n"
                "This tab will have limited functionality without these dependencies."
            )
            warning_layout.addWidget(info_text)
            main_layout.addLayout(warning_layout)
        
        # --- Selección de archivo ---
        file_group = QGroupBox("File Selection")
        file_group.setMaximumHeight(120)  # Limitar altura del grupo
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(8, 8, 8, 8)  # Márgenes más pequeños
        file_layout.setSpacing(4)  # Espaciado reducido
        
        # Ruta del archivo
        path_layout = QHBoxLayout()
        path_layout.setSpacing(4)
        
        self.file_path_line = QLineEdit()
        self.file_path_line.setPlaceholderText("Select a GPKG/SHP file to reorder columns...")
        self.file_path_line.setReadOnly(True)
        path_layout.addWidget(QLabel("File:"))
        path_layout.addWidget(self.file_path_line)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.clicked.connect(self._browse_file)
        path_layout.addWidget(self.browse_btn)
        
        self.use_output_btn = QPushButton("Use Final Output")
        self.use_output_btn.setMaximumWidth(120)
        self.use_output_btn.setToolTip("Use the final parcels output file from pipeline configuration")
        self.use_output_btn.clicked.connect(self._use_pipeline_output)
        path_layout.addWidget(self.use_output_btn)
        
        file_layout.addLayout(path_layout)
        
        # Información del archivo (más compacta)
        self.file_info_text = QTextEdit()
        self.file_info_text.setMaximumHeight(45)  # Aún más pequeña
        self.file_info_text.setMinimumHeight(35)
        self.file_info_text.setReadOnly(True)
        self.file_info_text.setPlaceholderText("File information will appear here...")
        self.file_info_text.setStyleSheet("QTextEdit { font-size: 9pt; }")
        file_layout.addWidget(self.file_info_text)
        
        main_layout.addWidget(file_group)
        
        # --- Reordenamiento de columnas ---
        columns_group = QGroupBox("Column Reordering")
        columns_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )  # Permitir que crezca
        columns_layout = QVBoxLayout(columns_group)
        columns_layout.setContentsMargins(8, 8, 8, 8)
        columns_layout.setSpacing(6)
        
        # Splitter para dividir la vista
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Lista de columnas disponibles (lado izquierdo)
        left_widget = QWidget()
        left_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Título y botones de control
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Available Columns (drag to reorder, uncheck to exclude):"))
        title_layout.addStretch()
        
        # Botones de esquemas de columnas
        self.save_schema_btn = QPushButton("💾 Save Schema")
        self.save_schema_btn.setMaximumWidth(100)
        self.save_schema_btn.setToolTip("Save current column order as a reusable schema")
        self.save_schema_btn.clicked.connect(self._save_column_schema)
        title_layout.addWidget(self.save_schema_btn)
        
        self.load_schema_btn = QPushButton("📂 Load Schema")
        self.load_schema_btn.setMaximumWidth(100)
        self.load_schema_btn.setToolTip("Load a previously saved column order schema")
        self.load_schema_btn.clicked.connect(self._load_column_schema)
        title_layout.addWidget(self.load_schema_btn)
        
        self.load_columns_btn = QPushButton("Load Columns")
        self.load_columns_btn.setMaximumWidth(100)
        self.load_columns_btn.clicked.connect(self._load_columns)
        title_layout.addWidget(self.load_columns_btn)
        
        self.reset_btn = QPushButton("Reset Order")
        self.reset_btn.setMaximumWidth(100)
        self.reset_btn.clicked.connect(self._reset_order)
        title_layout.addWidget(self.reset_btn)
        
        left_layout.addLayout(title_layout)
        
        # Botones de selección masiva
        selection_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setMaximumWidth(80)
        self.select_all_btn.clicked.connect(self._select_all_columns)
        selection_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = QPushButton("Select None")
        self.select_none_btn.setMaximumWidth(80)
        self.select_none_btn.clicked.connect(self._select_none_columns)
        selection_layout.addWidget(self.select_none_btn)
        
        self.invert_selection_btn = QPushButton("Invert")
        self.invert_selection_btn.setMaximumWidth(60)
        self.invert_selection_btn.clicked.connect(self._invert_selection)
        selection_layout.addWidget(self.invert_selection_btn)
        
        selection_layout.addStretch()
        
        # Contador de columnas seleccionadas
        self.selected_count_label = QLabel("Selected: 0 / 0")
        self.selected_count_label.setStyleSheet("color: #666; font-size: 10pt;")
        selection_layout.addWidget(self.selected_count_label)
        
        left_layout.addLayout(selection_layout)
        
        # Lista de columnas con scroll nativo del QListWidget
        self.columns_list = DraggableListWidget(self)
        self.columns_list.setToolTip("Drag and drop to reorder columns\nCheck/uncheck to include/exclude columns")
        self.columns_list.setMinimumHeight(200)
        self.columns_list.setMaximumHeight(250)  # Establecer altura máxima para forzar scroll
        self.columns_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.columns_list)
        
        splitter.addWidget(left_widget)
        
        # Panel de configuraciones (lado derecho)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Configuraciones de salida
        config_group = QGroupBox("Output Configuration")
        config_layout = QVBoxLayout(config_group)
        
        config_form = QFormLayout()
        
        # Archivo de salida
        output_layout = QHBoxLayout()
        self.output_path_line = QLineEdit()
        self.output_path_line.setPlaceholderText("Output file path (optional - will use input if empty)")
        output_layout.addWidget(self.output_path_line)
        
        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.setMaximumWidth(80)
        self.browse_output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.browse_output_btn)
        
        config_form.addRow("Output File:", output_layout)
        
        # Opciones
        self.backup_checkbox = QCheckBox("Create backup of original file")
        self.backup_checkbox.setChecked(True)
        config_form.addRow("Backup:", self.backup_checkbox)
        
        self.geometry_first_checkbox = QCheckBox("Keep geometry column first")
        self.geometry_first_checkbox.setChecked(False)
        self.geometry_first_checkbox.setToolTip("Keep geometry column at the beginning (recommended for some GIS software)")
        config_form.addRow("Geometry:", self.geometry_first_checkbox)
        
        config_layout.addLayout(config_form)
        right_layout.addWidget(config_group)
        
        # Preview del orden
        preview_group = QGroupBox("Column Order Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_text = QTextEdit()
        self.preview_text.setMinimumHeight(180)
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Column order preview will appear here...")
        self.preview_text.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Monaco', monospace; font-size: 9pt; }")
        self.preview_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        preview_layout.addWidget(self.preview_text)
        
        right_layout.addWidget(preview_group)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)  # Lista de columnas más ancha
        splitter.setStretchFactor(1, 2)  # Panel de configuración más pequeño
        
        columns_layout.addWidget(splitter)
        main_layout.addWidget(columns_group, 1)  # Stretch factor 1 para que crezca
        
        # --- Botones de acción ---
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Update Preview")
        self.preview_btn.clicked.connect(self._update_preview)
        action_layout.addWidget(self.preview_btn)
        
        action_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply Column Order")
        self.apply_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.apply_btn.clicked.connect(self._apply_column_order)
        action_layout.addWidget(self.apply_btn)
        
        main_layout.addLayout(action_layout)
        
        # Estado inicial
        self._update_ui_state()

    def _connect_signals(self) -> None:
        """Conecta las señales de los widgets."""
        self.file_path_line.textChanged.connect(self._update_ui_state)
        self.columns_list.itemChanged.connect(self._update_preview)
        self.geometry_first_checkbox.toggled.connect(self._update_preview)
        
        # Conectar señales para actualizar preview automáticamente
        self.columns_list.model().rowsMoved.connect(self._update_preview)
        
        # Conectar señal para actualizar cuando cambie el estado de los checkboxes
        self.columns_list.itemChanged.connect(self._update_selected_count)

    def _get_gpkg_info_with_gdal(self, file_path: str) -> Dict[str, Any]:
        """Obtiene información del GPKG usando GDAL directamente."""
        if not GDAL_AVAILABLE:
            return None
            
        try:
            # Abrir el dataset con GDAL
            dataset = gdal.OpenEx(file_path, gdal.OF_VECTOR)
            if not dataset:
                return None
            
            info = {
                'layers': [],
                'driver': dataset.GetDriver().GetDescription()
            }
            
            # Obtener información de cada capa
            for i in range(dataset.GetLayerCount()):
                layer = dataset.GetLayerByIndex(i)
                layer_info = {
                    'name': layer.GetName(),
                    'feature_count': layer.GetFeatureCount(),
                    'geometry_type': ogr.GeometryTypeToName(layer.GetGeomType()),
                    'fields': []
                }
                
                # Obtener información de los campos
                layer_def = layer.GetLayerDefn()
                for j in range(layer_def.GetFieldCount()):
                    field_def = layer_def.GetFieldDefn(j)
                    layer_info['fields'].append({
                        'name': field_def.GetName(),
                        'type': field_def.GetTypeName()
                    })
                
                # Agregar campo de geometría si existe
                geom_field_def = layer_def.GetGeomFieldDefn(0)
                if geom_field_def:
                    geometry_column = geom_field_def.GetName() or 'geom'
                    layer_info['geometry_column'] = geometry_column
                    # Insertar al inicio de la lista de campos
                    layer_info['fields'].insert(0, {
                        'name': geometry_column,
                        'type': 'Geometry'
                    })
                
                info['layers'].append(layer_info)
            
            dataset = None  # Cerrar dataset
            return info
            
        except Exception as e:
            pass  # Error silenciado - se usa fallback
            return None

    def _get_columns_with_gdal(self, file_path: str, layer_name: str = None) -> List[str]:
        """Obtiene las columnas usando GDAL directamente."""
        if not GDAL_AVAILABLE:
            return []
            
        try:
            dataset = gdal.OpenEx(file_path, gdal.OF_VECTOR)
            if not dataset:
                return []
            
            # Seleccionar la capa
            if layer_name:
                layer = dataset.GetLayerByName(layer_name)
            else:
                layer = dataset.GetLayerByIndex(0)
            
            if not layer:
                return []
            
            columns = []
            layer_def = layer.GetLayerDefn()
            
            # Agregar campo de geometría si existe
            geom_field_def = layer_def.GetGeomFieldDefn(0)
            if geom_field_def:
                geometry_column = geom_field_def.GetName() or 'geom'
                columns.append(geometry_column)
            
            # Agregar campos de atributos
            for i in range(layer_def.GetFieldCount()):
                field_def = layer_def.GetFieldDefn(i)
                columns.append(field_def.GetName())
            
            dataset = None  # Cerrar dataset
            return columns
            
        except Exception as e:
            pass  # Error silenciado - se usa fallback
            return []

    def _update_ui_state(self) -> None:
        """Actualiza el estado de la interfaz según el archivo seleccionado."""
        has_file = bool(self.file_path_line.text().strip())
        has_columns = self.columns_list.count() > 0
        
        self.load_columns_btn.setEnabled(has_file)
        self.reset_btn.setEnabled(has_columns)
        self.apply_btn.setEnabled(has_file and has_columns)
        self.preview_btn.setEnabled(has_columns)
        
        # Control de botones de esquemas
        self.save_schema_btn.setEnabled(has_columns)
        self.load_schema_btn.setEnabled(has_file)  # Necesita archivo para validar compatibilidad

    def _browse_file(self) -> None:
        initial_dir = get_initial_directory_from_path(self.file_path_line.text())
        file_path, _ = EnhancedFileDialog.get_open_file_name(
            self, "Select GPKG/SHP File", initial_dir, "GeoPackage (*.gpkg);;Shapefile (*.shp)"
        )
        if file_path:
            self._load_file_info(file_path)

    def _browse_output(self) -> None:
        """Abre un diálogo para seleccionar el archivo de salida, usando la ruta de entrada como base."""
        if not self._current_file_path:
            QMessageBox.warning(self, "Input File Required", "Please load an input file first.")
            return

        initial_dir = os.path.dirname(self._current_file_path)
        default_name = os.path.basename(self._current_file_path).replace(".gpkg", "_reordered.gpkg")
        
        output_path, _ = EnhancedFileDialog.get_save_file_name(
            self, "Select Output File", os.path.join(initial_dir, default_name), "GeoPackage (*.gpkg)"
        )
        if output_path:
            self.output_path_line.setText(output_path)

    def _use_pipeline_output(self) -> None:
        """Emite una señal para solicitar la ruta de salida del pipeline principal."""
        self.request_pipeline_output.emit()

    def _load_file_info(self, file_path: str) -> None:
        """Carga información del archivo seleccionado."""
        if not GEOPANDAS_AVAILABLE and not GDAL_AVAILABLE:
            self.file_info_text.setPlainText("Error: Neither GeoPandas nor GDAL available. Cannot load file information.")
            return
            
        try:
            if not os.path.exists(file_path):
                self.file_info_text.setPlainText("Error: File does not exist.")
                return
                
            # Cargar información básica
            if file_path.lower().endswith('.gpkg'):
                # Método 1: Intentar con GDAL (más robusto para GPKG)
                if GDAL_AVAILABLE:
                    gdal_info = self._get_gpkg_info_with_gdal(file_path)
                    if gdal_info and gdal_info['layers']:
                        layer_info = f"GPKG with {len(gdal_info['layers'])} layer(s) (using GDAL):\n"
                        for i, layer in enumerate(gdal_info['layers']):
                            layer_info += f"  {i+1}. {layer['name']} ({layer['geometry_type']}, {layer['feature_count']} features)\n"
                        
                        self.file_info_text.setPlainText(layer_info)
                        
                        # Usar la primera capa
                        self._current_file_path = file_path
                        self._current_layer = gdal_info['layers'][0]['name']
                        
                        # Cargar columnas usando el método estándar para mantener consistencia
                        self._load_columns()
                        
                        if len(gdal_info['layers']) > 1:
                            layer_info += f"\nUsing layer '{gdal_info['layers'][0]['name']}' by default."
                            self.file_info_text.setPlainText(layer_info)
                        
                        return
                
                # Método 2: Fallback con pyogrio si GDAL falla
                if GEOPANDAS_AVAILABLE:
                    try:
                        layers = pyogrio.list_layers(file_path)
                        if layers:
                            layer_info = f"GPKG with {len(layers)} layer(s) (using pyogrio):\n"
                            for i, (layer_name, layer_type, feature_count) in enumerate(layers):
                                layer_info += f"  {i+1}. {layer_name} ({layer_type}, {feature_count} features)\n"
                            self.file_info_text.setPlainText(layer_info)
                            
                            self._current_file_path = file_path
                            self._current_layer = layers[0][0]  # Nombre de la primera capa
                            self._load_columns()
                            
                            if len(layers) > 1:
                                layer_info += f"\nUsing layer '{layers[0][0]}' by default."
                                self.file_info_text.setPlainText(layer_info)
                        else:
                            self.file_info_text.setPlainText("GPKG file with no layers found.")
                    except Exception as e:
                        self.file_info_text.setPlainText(f"Error reading GPKG with pyogrio: {e}")
                else:
                    self.file_info_text.setPlainText("Error: No suitable library available to read GPKG files.")
            else:
                # Para otros formatos, usar GeoPandas si está disponible
                if GEOPANDAS_AVAILABLE:
                    try:
                        # Leer solo una muestra pequeña para obtener información básica
                        gdf = gpd.read_file(file_path, rows=5, engine='pyogrio')
                        info = f"File: {os.path.basename(file_path)}\n"
                        info += f"Sample features: {len(gdf)}\n"
                        info += f"Columns: {len(gdf.columns)}\n"
                        info += f"CRS: {gdf.crs if gdf.crs else 'Not defined'}"
                        self.file_info_text.setPlainText(info)
                        
                        self._current_file_path = file_path
                        self._current_layer = None  # No layer for non-GPKG files
                        self._load_columns()
                    except Exception as e:
                        self.file_info_text.setPlainText(f"Error reading file: {e}")
                else:
                    self.file_info_text.setPlainText("Error: GeoPandas not available for reading non-GPKG files.")
                    
        except Exception as e:
            self.file_info_text.setPlainText(f"Error loading file information: {e}")

    def _load_columns_from_list(self, columns: List[str]) -> None:
        """Carga las columnas desde una lista predefinida."""
        if not columns:
            return
            
        self._original_columns = columns.copy()
        
        # Limpiar lista actual
        self.columns_list.clear()
        
        # Agregar columnas a la lista con checkboxes
        for col in columns:
            item = QListWidgetItem(col)
            item.setToolTip(f"Column: {col}\nCheck to include in output, uncheck to exclude")
            
            # Hacer el item checkeable
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)  # Por defecto todas seleccionadas
            
            # Marcar geometría con color diferente
            if col.lower() in ['geometry', 'geom', 'shape']:
                item.setBackground(Qt.GlobalColor.lightGray)
                item.setToolTip(f"Geometry Column: {col}\nRecommended to keep this column")
            
            self.columns_list.addItem(item)
        
        self._update_selected_count()
        self._update_preview()
        self._update_ui_state()

    def _select_all_columns(self) -> None:
        """Selecciona todas las columnas."""
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        self._update_selected_count()
        self._update_preview()

    def _select_none_columns(self) -> None:
        """Deselecciona todas las columnas."""
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self._update_selected_count()
        self._update_preview()

    def _invert_selection(self) -> None:
        """Invierte la selección de columnas."""
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
        self._update_selected_count()
        self._update_preview()

    def _update_selected_count(self) -> None:
        """Actualiza el contador de columnas seleccionadas."""
        total = self.columns_list.count()
        selected = 0
        for i in range(total):
            item = self.columns_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected += 1
        
        self.selected_count_label.setText(f"Selected: {selected} / {total}")
        
        # Cambiar color según selección
        if selected == 0:
            self.selected_count_label.setStyleSheet("color: #d32f2f; font-size: 10pt; font-weight: bold;")
        elif selected == total:
            self.selected_count_label.setStyleSheet("color: #388e3c; font-size: 10pt;")
        else:
            self.selected_count_label.setStyleSheet("color: #f57c00; font-size: 10pt;")

    def _load_columns(self) -> None:
        """Carga las columnas del archivo seleccionado."""
        if not self._current_file_path:
            return
            
        try:
            # Método 1: Usar GDAL si está disponible (más robusto)
            if GDAL_AVAILABLE and self._current_file_path.lower().endswith('.gpkg'):
                columns = self._get_columns_with_gdal(self._current_file_path, self._current_layer)
                if columns:
                    self._load_columns_from_list(columns)
                    return
            
            # Método 2: Fallback con GeoPandas/pyogrio
            if not GEOPANDAS_AVAILABLE:
                QMessageBox.warning(self, "Warning", "Neither GDAL nor GeoPandas available to load columns.")
                return
                
            # Usar pyogrio directamente para evitar problemas de ambigüedad
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Leer solo las primeras filas para obtener las columnas usando pyogrio
                if self._current_file_path.lower().endswith('.gpkg') and hasattr(self, '_current_layer'):
                    # Para GPKG con capa específica
                    try:
                        # Método 1: Usar pyogrio directamente
                        df = pyogrio.read_dataframe(
                            self._current_file_path, 
                            layer=self._current_layer,
                            max_features=1
                        )
                        columns = list(df.columns)
                    except Exception:
                        # Fallback: usar geopandas con configuración específica
                        gdf = gpd.read_file(
                            self._current_file_path, 
                            layer=self._current_layer,
                            rows=1, 
                            engine='pyogrio'
                        )
                        columns = list(gdf.columns)
                else:
                    # Para otros formatos
                    try:
                        # Método 1: Usar pyogrio directamente
                        df = pyogrio.read_dataframe(
                            self._current_file_path, 
                            max_features=1
                        )
                        columns = list(df.columns)
                    except Exception:
                        # Fallback: usar geopandas
                        gdf = gpd.read_file(
                            self._current_file_path, 
                            rows=1, 
                            engine='pyogrio'
                        )
                        columns = list(gdf.columns)
            
            self._load_columns_from_list(columns)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load columns: {e}\n\nTry using a different file or check the file format.")

    def _reset_order(self) -> None:
        """Restaura el orden original de las columnas."""
        if not self._original_columns:
            return
            
        # Guardar estado de selección actual
        current_selection = {}
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            current_selection[item.text()] = item.checkState()
            
        self.columns_list.clear()
        for col in self._original_columns:
            item = QListWidgetItem(col)
            item.setToolTip(f"Column: {col}\nCheck to include in output, uncheck to exclude")
            
            # Hacer el item checkeable
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # Restaurar estado de selección si existía, sino marcar como seleccionado
            if col in current_selection:
                item.setCheckState(current_selection[col])
            else:
                item.setCheckState(Qt.CheckState.Checked)
            
            # Marcar geometría con color diferente
            if col.lower() in ['geometry', 'geom', 'shape']:
                item.setBackground(Qt.GlobalColor.lightGray)
                item.setToolTip(f"Geometry Column: {col}\nRecommended to keep this column")
                
            self.columns_list.addItem(item)
        
        self._update_selected_count()
        self._update_preview()

    def _get_current_column_order(self) -> List[str]:
        """Obtiene el orden actual de las columnas seleccionadas."""
        columns = []
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            # Solo incluir columnas que están marcadas (checked)
            if item.checkState() == Qt.CheckState.Checked:
                columns.append(item.text())
        return columns

    def _update_preview(self) -> None:
        """Actualiza el preview del orden de columnas."""
        selected_columns = self._get_current_column_order()
        
        # Obtener columnas excluidas
        excluded_columns = []
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            if item.checkState() == Qt.CheckState.Unchecked:
                excluded_columns.append(item.text())
        
        if not selected_columns and not excluded_columns:
            self.preview_text.setPlainText("No columns loaded.")
            return
        
        # Aplicar configuración de geometría
        columns = selected_columns.copy()
        if self.geometry_first_checkbox.isChecked() and columns:
            geometry_cols = [col for col in columns if col.lower() in ['geometry', 'geom', 'shape']]
            other_cols = [col for col in columns if col.lower() not in ['geometry', 'geom', 'shape']]
            columns = geometry_cols + other_cols
        
        # Construir preview
        preview_text = ""
        
        if columns:
            preview_text += f"✅ SELECTED COLUMNS ({len(columns)}):\n\n"
            for i, col in enumerate(columns, 1):
                marker = "📐" if col.lower() in ['geometry', 'geom', 'shape'] else "📊"
                preview_text += f"{i:2d}. {marker} {col}\n"
        else:
            preview_text += "⚠️  NO COLUMNS SELECTED\n\n"
        
        if excluded_columns:
            preview_text += f"\n❌ EXCLUDED COLUMNS ({len(excluded_columns)}):\n\n"
            for i, col in enumerate(excluded_columns, 1):
                marker = "📐" if col.lower() in ['geometry', 'geom', 'shape'] else "📊"
                preview_text += f"   {marker} {col}\n"
        
        if columns:
            preview_text += f"\n📋 FINAL OUTPUT: {len(columns)} columns will be saved"
        else:
            preview_text += f"\n⚠️  WARNING: No columns selected - output file will be empty!"
        
        self.preview_text.setPlainText(preview_text)
        
        # Actualizar contador
        self._update_selected_count()

    def _apply_column_order(self) -> None:
        """Aplica el nuevo orden de columnas al archivo."""
        if not self._current_file_path:
            QMessageBox.warning(self, "Warning", "No file selected.")
            return
            
        if not GEOPANDAS_AVAILABLE and not GDAL_AVAILABLE:
            QMessageBox.warning(self, "Warning", "Neither GeoPandas nor GDAL available.")
            return
        
        try:
            # Obtener orden de columnas
            columns = self._get_current_column_order()
            
            if not columns:
                QMessageBox.warning(self, "Warning", "No columns to reorder.")
                return
            
            if self.geometry_first_checkbox.isChecked():
                geometry_cols = [col for col in columns if col.lower() in ['geometry', 'geom', 'shape']]
                other_cols = [col for col in columns if col.lower() not in ['geometry', 'geom', 'shape']]
                columns = geometry_cols + other_cols
            
            # Cargar archivo completo usando método robusto
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                # Método 1: Usar GDAL + GeoPandas si está disponible
                if GDAL_AVAILABLE and self._current_file_path.lower().endswith('.gpkg'):
                    try:
                        # Leer con GDAL para obtener información confiable
                        dataset = gdal.OpenEx(self._current_file_path, gdal.OF_VECTOR)
                        if dataset and self._current_layer:
                            layer = dataset.GetLayerByName(self._current_layer)
                            if layer:
                                # Obtener nombres reales de columnas del archivo
                                layer_def = layer.GetLayerDefn()
                                real_columns = []
                                
                                # Agregar geometría
                                geom_field_def = layer_def.GetGeomFieldDefn(0)
                                if geom_field_def:
                                    geometry_column = geom_field_def.GetName() or 'geom'
                                    real_columns.append(geometry_column)
                                
                                # Agregar atributos
                                for i in range(layer_def.GetFieldCount()):
                                    field_def = layer_def.GetFieldDefn(i)
                                    real_columns.append(field_def.GetName())
                                
                                dataset = None  # Cerrar
                                
                                # Verificar que las columnas solicitadas existen
                                missing_columns = [col for col in columns if col not in real_columns]
                                if missing_columns:
                                    QMessageBox.warning(
                                        self, "Warning", 
                                        f"The following columns are not in the file:\n{', '.join(missing_columns)}\n\n"
                                        f"Available columns: {', '.join(real_columns)}"
                                    )
                                    return
                                
                                # Filtrar solo columnas que existen
                                columns = [col for col in columns if col in real_columns]
                    except Exception as e:
                        pass  # Error silenciado - se usa fallback
                
                # Cargar archivo con GeoPandas
                if self._current_file_path.lower().endswith('.gpkg') and hasattr(self, '_current_layer'):
                    # Para GPKG con capa específica
                    try:
                        gdf = gpd.read_file(
                            self._current_file_path, 
                            layer=self._current_layer,
                            engine='pyogrio'
                        )
                    except Exception:
                        # Fallback sin especificar engine
                        gdf = gpd.read_file(
                            self._current_file_path, 
                            layer=self._current_layer
                        )
                else:
                    # Para otros formatos
                    try:
                        gdf = gpd.read_file(self._current_file_path, engine='pyogrio')
                    except Exception:
                        gdf = gpd.read_file(self._current_file_path)
            
            # Verificar que todas las columnas existen en el GeoDataFrame
            available_columns = list(gdf.columns)
            missing_columns = [col for col in columns if col not in available_columns]
            
            # Mapear nombres comunes de geometría
            geometry_mappings = {
                'geom': 'geometry',
                'geometry': 'geom',
                'shape': 'geometry',
                'the_geom': 'geometry'
            }
            
            # Intentar mapear columnas faltantes
            if missing_columns:
                mapped_columns = []
                still_missing = []
                
                for col in columns:
                    if col in available_columns:
                        mapped_columns.append(col)
                    elif col in geometry_mappings and geometry_mappings[col] in available_columns:
                        # Mapear nombre de geometría
                        mapped_columns.append(geometry_mappings[col])
                    else:
                        still_missing.append(col)
                
                if still_missing:
                    QMessageBox.warning(
                        self, "Warning", 
                        f"The following columns are not available in the loaded data:\n{', '.join(still_missing)}\n\n"
                        f"Available columns: {', '.join(available_columns)}\n\n"
                        f"Please reload the file to refresh column information."
                    )
                    return
                
                # Usar columnas mapeadas
                columns = mapped_columns
            
            # Reordenar columnas
            gdf_reordered = gdf[columns]
            
            # Determinar archivo de salida
            output_path = self.output_path_line.text().strip()
            if not output_path:
                output_path = self._current_file_path
            
            # Crear backup si está habilitado
            if self.backup_checkbox.isChecked() and output_path == self._current_file_path:
                backup_path = f"{self._current_file_path}.backup"
                import shutil
                shutil.copy2(self._current_file_path, backup_path)
            
            # Guardar archivo reordenado
            try:
                if output_path.lower().endswith('.gpkg'):
                    # Para GPKG, usar layer name si existe
                    layer_name = os.path.splitext(os.path.basename(output_path))[0]
                    gdf_reordered.to_file(output_path, driver='GPKG', layer=layer_name, engine='pyogrio')
                else:
                    gdf_reordered.to_file(output_path, engine='pyogrio')
            except Exception:
                # Fallback sin engine específico
                if output_path.lower().endswith('.gpkg'):
                    layer_name = os.path.splitext(os.path.basename(output_path))[0]
                    gdf_reordered.to_file(output_path, driver='GPKG', layer=layer_name)
                else:
                    gdf_reordered.to_file(output_path)
            
            QMessageBox.information(
                self, "Success", 
                f"Column order applied successfully!\n\n"
                f"Output: {output_path}\n"
                f"Columns reordered: {len(columns)}\n"
                f"Final order: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply column order: {e}\n\nTry reloading the file or check the file format.")

    def set_pipeline_output_path(self, file_path: str) -> None:
        """Establece la ruta del archivo de salida del pipeline."""
        if file_path and os.path.exists(file_path):
            self.file_path_line.setText(file_path)
            self._load_file_info(file_path)
        else:
            QMessageBox.warning(self, "Warning", f"Pipeline output file not found: {file_path}")

    def get_config(self) -> Dict[str, Any]:
        """Retorna la configuración actual del tab."""
        return {
            "file_path": self.file_path_line.text(),
            "output_path": self.output_path_line.text(),
            "create_backup": self.backup_checkbox.isChecked(),
            "geometry_first": self.geometry_first_checkbox.isChecked(),
            "column_order": self._get_current_column_order()
        }

    def set_config(self, config: Dict[str, Any]) -> None:
        """Aplica una configuración al tab."""
        self.file_path_line.setText(config.get("file_path", ""))
        self.output_path_line.setText(config.get("output_path", ""))
        self.backup_checkbox.setChecked(config.get("create_backup", True))
        self.geometry_first_checkbox.setChecked(config.get("geometry_first", False))
        
        # Si hay un archivo, cargar información
        if config.get("file_path"):
            self._load_file_info(config["file_path"])

    def _save_column_schema(self) -> None:
        """Guarda el esquema actual de orden de columnas."""
        if not self._original_columns:
            QMessageBox.warning(self, "Warning", "No columns loaded to save as schema.")
            return
            
        # Obtener el orden actual y estado de selección
        schema_data = {
            "schema_version": "1.0",
            "created_date": datetime.now().isoformat(),
            "source_file": os.path.basename(self._current_file_path) if self._current_file_path else "unknown",
            "total_columns": len(self._original_columns),
            "column_order": [],
            "excluded_columns": [],
            "settings": {
                "geometry_first": self.geometry_first_checkbox.isChecked()
            }
        }
        
        # Recopilar información de todas las columnas
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            column_name = item.text()
            is_selected = item.checkState() == Qt.CheckState.Checked
            is_geometry = column_name.lower() in ['geometry', 'geom', 'shape']
            
            column_info = {
                "name": column_name,
                "position": i,
                "is_geometry": is_geometry
            }
            
            if is_selected:
                schema_data["column_order"].append(column_info)
            else:
                schema_data["excluded_columns"].append(column_info)
        
        # Diálogo para guardar archivo
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Column Schema",
            f"column_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schema_data, f, indent=2, ensure_ascii=False)
                
            QMessageBox.information(
                self, "Success", 
                f"Column schema saved successfully!\n\n"
                f"File: {os.path.basename(file_path)}\n"
                f"Columns: {len(schema_data['column_order'])} selected, {len(schema_data['excluded_columns'])} excluded"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save schema:\n{e}")

    def _load_column_schema(self) -> None:
        """Carga un esquema de orden de columnas previamente guardado."""
        if not self._original_columns:
            QMessageBox.warning(self, "Warning", "Please load a file first before applying a column schema.")
            return
            
        # Diálogo para abrir archivo
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Column Schema",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
                
            # Validar estructura del esquema
            if not isinstance(schema_data, dict) or "column_order" not in schema_data:
                QMessageBox.warning(self, "Warning", "Invalid schema file format.")
                return
                
            # Obtener columnas actuales del archivo
            current_columns = set(self._original_columns)
            
            # Extraer nombres de columnas del esquema
            schema_selected = [col["name"] if isinstance(col, dict) else col for col in schema_data.get("column_order", [])]
            schema_excluded = [col["name"] if isinstance(col, dict) else col for col in schema_data.get("excluded_columns", [])]
            schema_all_columns = set(schema_selected + schema_excluded)
            
            # Validar compatibilidad
            matching_columns = current_columns.intersection(schema_all_columns)
            missing_in_file = schema_all_columns - current_columns
            new_in_file = current_columns - schema_all_columns
            
            # Mostrar información de compatibilidad
            compatibility_info = []
            compatibility_info.append(f"Schema file: {os.path.basename(file_path)}")
            compatibility_info.append(f"Schema source: {schema_data.get('source_file', 'unknown')}")
            compatibility_info.append(f"Created: {schema_data.get('created_date', 'unknown')}")
            compatibility_info.append("")
            compatibility_info.append(f"✅ Matching columns: {len(matching_columns)}")
            compatibility_info.append(f"❌ Columns in schema but not in file: {len(missing_in_file)}")
            compatibility_info.append(f"🆕 New columns in file: {len(new_in_file)}")
            
            if missing_in_file:
                compatibility_info.append(f"\nMissing: {', '.join(sorted(missing_in_file))}")
            if new_in_file:
                compatibility_info.append(f"\nNew: {', '.join(sorted(new_in_file))}")
                
            # Preguntar al usuario si quiere continuar
            reply = QMessageBox.question(
                self, "Load Column Schema",
                "\n".join(compatibility_info) + "\n\nDo you want to apply this schema?\n\n"
                "Note: Only matching columns will be applied. New columns will be added at the end.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
                
            # Aplicar el esquema
            self._apply_column_schema(schema_data, current_columns)
            
            # Aplicar configuraciones
            settings = schema_data.get("settings", {})
            if "geometry_first" in settings:
                self.geometry_first_checkbox.setChecked(settings["geometry_first"])
                
            self._update_preview()
            
            QMessageBox.information(
                self, "Success",
                f"Column schema applied successfully!\n\n"
                f"Applied: {len(matching_columns)} matching columns\n"
                f"New columns added at end: {len(new_in_file)}"
            )
            
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Invalid JSON file format.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load schema:\n{e}")

    def _apply_column_schema(self, schema_data: Dict[str, Any], current_columns: set) -> None:
        """Aplica un esquema de columnas al orden actual."""
        # Extraer información del esquema
        schema_selected = []
        schema_excluded = []
        
        for col in schema_data.get("column_order", []):
            if isinstance(col, dict):
                schema_selected.append(col["name"])
            else:
                schema_selected.append(col)
                
        for col in schema_data.get("excluded_columns", []):
            if isinstance(col, dict):
                schema_excluded.append(col["name"])
            else:
                schema_excluded.append(col)
        
        # Crear nuevo orden basado en el esquema
        new_order = []
        used_columns = set()
        
        # 1. Agregar columnas del esquema en el orden especificado (solo las que existen)
        for col_name in schema_selected:
            if col_name in current_columns:
                new_order.append((col_name, True))  # (nombre, seleccionado)
                used_columns.add(col_name)
                
        # 2. Agregar columnas excluidas del esquema (solo las que existen)
        for col_name in schema_excluded:
            if col_name in current_columns:
                new_order.append((col_name, False))  # (nombre, no seleccionado)
                used_columns.add(col_name)
        
        # 3. Agregar columnas nuevas que no estaban en el esquema (al final, seleccionadas)
        remaining_columns = current_columns - used_columns
        for col_name in sorted(remaining_columns):  # Ordenadas alfabéticamente
            new_order.append((col_name, True))
        
        # Actualizar la lista de columnas
        self.columns_list.clear()
        for col_name, is_selected in new_order:
            item = QListWidgetItem(col_name)
            item.setToolTip(f"Column: {col_name}\nCheck to include in output, uncheck to exclude")
            
            # Hacer el item checkeable
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # Establecer estado de selección
            item.setCheckState(Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked)
            
            # Marcar geometría con color diferente
            if col_name.lower() in ['geometry', 'geom', 'shape']:
                item.setBackground(Qt.GlobalColor.lightGray)
                item.setToolTip(f"Geometry Column: {col_name}\nRecommended to keep this column")
                
            self.columns_list.addItem(item)
        
        self._update_selected_count() 