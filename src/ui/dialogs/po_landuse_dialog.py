"""
Dialog for selecting land use types from Plan Operativo data.
"""

import os
from typing import Dict, List, Tuple, Optional, Any
import geopandas as gpd
import pandas as pd

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QCheckBox, QScrollArea, QWidget,
    QGroupBox, QFormLayout, QMessageBox, QProgressBar, QFrame,
    QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


class PODataLoader(QThread):
    """Thread for loading Plan Operativo data without blocking UI."""
    
    dataLoaded = pyqtSignal(object, str)  # gdf, error_message
    progressUpdated = pyqtSignal(int, str)  # progress, status
    
    def __init__(self, po_path: str, po_layer: str):
        super().__init__()
        self.po_path = po_path
        self.po_layer = po_layer
    
    def run(self):
        try:
            self.progressUpdated.emit(10, "Reading Plan Operativo file...")
            
            # Read with pyogrio engine as requested
            if self.po_layer:
                gdf = gpd.read_file(self.po_path, layer=self.po_layer, engine='pyogrio')
            else:
                gdf = gpd.read_file(self.po_path, engine='pyogrio')
            
            self.progressUpdated.emit(50, "Processing data...")
            
            # Limit to first 1000 rows for performance
            if len(gdf) > 1000:
                gdf = gdf.head(1000)
            
            self.progressUpdated.emit(100, "Data loaded successfully")
            self.dataLoaded.emit(gdf, "")
            
        except Exception as e:
            self.dataLoaded.emit(None, str(e))


class POLandUseDialog(QDialog):
    """Dialog for selecting land use field and types from Plan Operativo."""
    
    def __init__(self, po_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.po_config = po_config
        self.gdf = None
        self.selected_field = None
        self.selected_types = []
        
        self.setWindowTitle("Select Land Use Types from Plan Operativo")
        self.setModal(True)
        self.resize(800, 600)
        
        self._init_ui()
        self._load_po_data()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header info
        header_label = QLabel("Inspect Plan Operativo data and select land use field and types")
        header_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(header_label)
        
        # PO file info
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        info_layout = QFormLayout(info_frame)
        
        po_path = self.po_config.get("ruta", "Not configured")
        po_layer = self.po_config.get("capa", "Not specified")
        
        info_layout.addRow("PO File:", QLabel(os.path.basename(po_path) if po_path else "Not configured"))
        info_layout.addRow("Layer:", QLabel(po_layer if po_layer else "Default"))
        layout.addWidget(info_frame)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # Main content (splitter)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Column inspection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        columns_label = QLabel("Available Columns:")
        columns_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        left_layout.addWidget(columns_label)
        
        # Columns table
        self.columns_table = QTableWidget()
        self.columns_table.setColumnCount(3)
        self.columns_table.setHorizontalHeaderLabels(["Column Name", "Data Type", "Sample Value"])
        self.columns_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.columns_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.columns_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        left_layout.addWidget(self.columns_table)
        
        # Field selection
        field_group = QGroupBox("Select Land Use Field")
        field_layout = QFormLayout(field_group)
        
        self.field_combo = QComboBox()
        self.field_combo.currentTextChanged.connect(self._on_field_selected)
        field_layout.addRow("Land Use Field:", self.field_combo)
        
        left_layout.addWidget(field_group)
        
        splitter.addWidget(left_widget)
        
        # Right side: Land use types selection
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        types_label = QLabel("Available Land Use Types:")
        types_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        right_layout.addWidget(types_label)
        
        # Land use types scroll area
        self.types_scroll = QScrollArea()
        self.types_widget = QWidget()
        self.types_layout = QVBoxLayout(self.types_widget)
        self.types_scroll.setWidget(self.types_widget)
        self.types_scroll.setWidgetResizable(True)
        right_layout.addWidget(self.types_scroll)
        
        # Selection controls
        selection_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_none_btn = QPushButton("Select None")
        self.select_common_btn = QPushButton("Select Common Types")
        
        self.select_all_btn.clicked.connect(self._select_all_types)
        self.select_none_btn.clicked.connect(self._select_no_types)
        self.select_common_btn.clicked.connect(self._select_common_types)
        
        selection_layout.addWidget(self.select_all_btn)
        selection_layout.addWidget(self.select_none_btn)
        selection_layout.addWidget(self.select_common_btn)
        selection_layout.addStretch()
        right_layout.addLayout(selection_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Accept")
        self.cancel_button = QPushButton("Cancel")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.setEnabled(False)  # Disabled until data loads
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # Storage for checkboxes
        self.type_checkboxes = {}
    
    def _load_po_data(self):
        """Load Plan Operativo data in background thread."""
        po_path = self.po_config.get("ruta")
        po_layer = self.po_config.get("capa")
        
        if not po_path:
            QMessageBox.warning(self, "Missing Configuration", 
                              "Plan Operativo path is not configured.")
            self.reject()
            return
        
        if not os.path.exists(po_path):
            QMessageBox.warning(self, "File Not Found", 
                              f"Plan Operativo file not found:\n{po_path}")
            self.reject()
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Loading data...")
        
        # Start background loading
        self.loader_thread = PODataLoader(po_path, po_layer)
        self.loader_thread.dataLoaded.connect(self._on_data_loaded)
        self.loader_thread.progressUpdated.connect(self._on_progress_updated)
        self.loader_thread.start()
    
    def _on_progress_updated(self, progress: int, status: str):
        """Update progress bar and status."""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(status)
    
    def _on_data_loaded(self, gdf, error_message: str):
        """Handle loaded Plan Operativo data."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        # Clean up thread
        self._cleanup_thread()
        
        if error_message:
            QMessageBox.critical(self, "Error Loading Data", 
                               f"Failed to load Plan Operativo data:\n{error_message}")
            self.reject()
            return
        
        if gdf is None or gdf.empty:
            QMessageBox.warning(self, "No Data", 
                              "Plan Operativo file contains no data.")
            self.reject()
            return
        
        self.gdf = gdf
        self._populate_columns_table()
        self._populate_field_combo()
        self.ok_button.setEnabled(True)
    
    def _populate_columns_table(self):
        """Populate the columns inspection table."""
        if self.gdf is None:
            return
        
        # Exclude geometry column
        columns = [col for col in self.gdf.columns if col != 'geometry']
        
        self.columns_table.setRowCount(len(columns))
        
        for i, col in enumerate(columns):
            # Column name
            name_item = QTableWidgetItem(col)
            self.columns_table.setItem(i, 0, name_item)
            
            # Data type
            dtype = str(self.gdf[col].dtype)
            type_item = QTableWidgetItem(dtype)
            self.columns_table.setItem(i, 1, type_item)
            
            # Sample value (first non-null value)
            sample_value = "N/A"
            non_null_values = self.gdf[col].dropna()
            if not non_null_values.empty:
                sample_value = str(non_null_values.iloc[0])
                # Truncate if too long
                if len(sample_value) > 30:
                    sample_value = sample_value[:27] + "..."
            
            sample_item = QTableWidgetItem(sample_value)
            self.columns_table.setItem(i, 2, sample_item)
    
    def _populate_field_combo(self):
        """Populate field selection combo with likely land use fields."""
        if self.gdf is None:
            return
        
        # Get text/object columns (likely candidates for land use)
        text_columns = []
        for col in self.gdf.columns:
            if col != 'geometry' and self.gdf[col].dtype == 'object':
                text_columns.append(col)
        
        # Sort by likelihood (common land use field names first)
        priority_fields = ["tipouso", "tipo_uso", "uso", "landuse", "land_use", "class", "tipo"]
        
        sorted_columns = []
        for priority in priority_fields:
            for col in text_columns:
                if priority.lower() in col.lower() and col not in sorted_columns:
                    sorted_columns.append(col)
        
        # Add remaining text columns
        for col in text_columns:
            if col not in sorted_columns:
                sorted_columns.append(col)
        
        self.field_combo.addItems(sorted_columns)
        
        # Auto-select the most likely field
        if sorted_columns:
            self._on_field_selected(sorted_columns[0])
    
    def _on_field_selected(self, field_name: str):
        """Handle land use field selection."""
        if not field_name or self.gdf is None:
            return
        
        self.selected_field = field_name
        
        # Get unique values for this field
        unique_values = self.gdf[field_name].dropna().unique()
        unique_values = sorted([str(v) for v in unique_values if str(v) and str(v) != 'nan'])
        
        # Clear existing checkboxes
        for checkbox in self.type_checkboxes.values():
            checkbox.setParent(None)
        self.type_checkboxes.clear()
        
        # Create checkboxes for each unique value
        for value in unique_values:
            checkbox = QCheckBox(f"{value} ({sum(self.gdf[field_name] == value)} records)")
            self.type_checkboxes[value] = checkbox
            self.types_layout.addWidget(checkbox)
        
        # Add stretch to bottom
        self.types_layout.addStretch()
    
    def _select_all_types(self):
        """Select all land use types."""
        for checkbox in self.type_checkboxes.values():
            checkbox.setChecked(True)
    
    def _select_no_types(self):
        """Deselect all land use types."""
        for checkbox in self.type_checkboxes.values():
            checkbox.setChecked(False)
    
    def _select_common_types(self):
        """Select commonly used land use types."""
        common_patterns = ["pira", "euni", "eugl", "ehng", "egrn", "pino", "eucal", "forest"]
        
        for land_type, checkbox in self.type_checkboxes.items():
            is_common = any(pattern.lower() in land_type.lower() for pattern in common_patterns)
            checkbox.setChecked(is_common)
    
    def get_selected_types(self) -> Tuple[str, List[str]]:
        """Get the selected field and land use types."""
        selected_types = []
        for land_type, checkbox in self.type_checkboxes.items():
            if checkbox.isChecked():
                selected_types.append(land_type)
        
        return self.selected_field, selected_types
    
    def accept(self):
        """Accept dialog and validate selection."""
        if not self.selected_field:
            QMessageBox.warning(self, "No Field Selected", 
                              "Please select a land use field.")
            return
        
        # Get selected types
        field, types = self.get_selected_types()
        
        if not types:
            reply = QMessageBox.question(self, "No Types Selected", 
                                       "No land use types are selected. Continue anyway?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.selected_field = field
        self.selected_types = types
        
        super().accept()
    
    def _cleanup_thread(self):
        """Clean up the background loading thread."""
        if hasattr(self, 'loader_thread') and self.loader_thread is not None:
            if self.loader_thread.isRunning():
                self.loader_thread.quit()
                self.loader_thread.wait(1000)  # Wait up to 1 second
            self.loader_thread = None
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        self._cleanup_thread()
        super().closeEvent(event)
    
    def reject(self):
        """Handle dialog rejection."""
        self._cleanup_thread()
        super().reject() 