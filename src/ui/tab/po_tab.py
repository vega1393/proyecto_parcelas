# src/ui/tab/po_tab.py

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox,
    QHBoxLayout, QLabel, QFileDialog, QMessageBox, QDialog, QScrollArea
)
from PyQt6.QtCore import pyqtSignal
from typing import Dict, List, Any

# Assuming these helpers exist and work as before
from src.utils.gpkg_helpers import list_layers, list_fields
from src.ui.dialogs.po_fields_dialog import POFieldsDialog

class POTab(QWidget):
    """
    Tab for Plan Operative (PO) settings. Encapsulates its own logic
    and emits a signal when its configuration changes.
    """
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._selected_fields: List[str] = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initializes the UI components of the tab."""
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QFormLayout(content_widget)

        # PO File Path
        self.po_path_line = QLineEdit()
        self.po_path_line.setPlaceholderText("Path to the Plan Operative file (e.g., .gpkg, .shp)")
        self.po_file_btn = QPushButton("Browse...")
        po_file_layout = QHBoxLayout()
        po_file_layout.addWidget(self.po_path_line)
        po_file_layout.addWidget(self.po_file_btn)
        form_layout.addRow("PO File:", po_file_layout)

        # PO Layer
        self.po_layer_combo = QComboBox()
        form_layout.addRow("PO Layer:", self.po_layer_combo)

        # PO Fields
        self.po_fields_btn = QPushButton("Select PO Fields...")
        self.po_fields_label = QLabel("No fields selected.")
        self.po_fields_label.setWordWrap(True)
        po_fields_layout = QHBoxLayout()
        po_fields_layout.addWidget(self.po_fields_btn)
        po_fields_layout.addWidget(self.po_fields_label, 1) # Stretch factor
        form_layout.addRow("PO Fields:", po_fields_layout)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        """Connects widget signals to internal slots."""
        self.po_file_btn.clicked.connect(self._select_po_file)
        self.po_path_line.textChanged.connect(self._on_path_changed)
        self.po_layer_combo.currentTextChanged.connect(self._on_layer_changed)
        self.po_fields_btn.clicked.connect(self._select_po_fields)

    def _select_po_file(self) -> None:
        """Opens a file dialog to select the PO file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PO File", "", "Geo Files (*.shp *.gpkg *.geojson *.gdb);;All Files (*)"
        )
        if file_path:
            self.po_path_line.setText(file_path)

    def _on_path_changed(self, path: str) -> None:
        """Handles changes to the PO file path, updating the layer combo."""
        self.po_layer_combo.clear()
        self._selected_fields = []
        self.po_fields_label.setText("No fields selected.")

        if path and os.path.exists(path):
            try:
                layers = list_layers(path)
                if layers:
                    self.po_layer_combo.addItems(layers)
                else:
                    self.po_layer_combo.addItem("[NO LAYERS FOUND]")
            except Exception as e:
                self.po_layer_combo.addItem("[ERROR LISTING LAYERS]")
                print(f"Error listing layers for {path}: {e}") # Log this properly
        else:
             self.po_layer_combo.addItem("[INVALID FILE PATH]")

        self.configChanged.emit(self.get_config())

    def _on_layer_changed(self) -> None:
        """Resets fields when layer changes and emits config update."""
        self._selected_fields = []
        self.po_fields_label.setText("No fields selected.")
        self.configChanged.emit(self.get_config())

    def _select_po_fields(self) -> None:
        """Opens a dialog to select fields from the current PO layer."""
        file_path = self.po_path_line.text()
        layer_name = self.po_layer_combo.currentText()

        if not (file_path and os.path.exists(file_path) and layer_name and not layer_name.startswith("[")):
            QMessageBox.warning(self, "PO Configuration Error", "Please select a valid PO file and layer first.")
            return

        try:
            available_fields = list_fields(file_path, layer_name)
            if not available_fields:
                QMessageBox.information(self, "No Fields", f"No attribute fields found in layer '{layer_name}'.")
                return

            dialog = POFieldsDialog(available_fields, self._selected_fields, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._selected_fields = dialog.get_selected_fields()
                self.po_fields_label.setText(", ".join(self._selected_fields) or "No fields selected.")
                self.configChanged.emit(self.get_config())

        except Exception as e:
            QMessageBox.critical(self, "Field Listing Error", f"Could not list fields for layer '{layer_name}':\n{e}")

    def get_config(self) -> Dict[str, Any]:
        """Returns the current PO configuration as a dictionary."""
        path = self.po_path_line.text()
        layer = self.po_layer_combo.currentText()
        
        # Only return a valid config if path and layer are usable
        if path and os.path.exists(path) and layer and not layer.startswith("["):
            return {
                "ruta": path,
                "capa": layer,
                "campos": self._selected_fields
            }
        return {} # Return empty dict if config is invalid

    def set_config(self, config: Dict[str, Any]) -> None:
        """Sets the tab's widgets based on a PO configuration dictionary."""
        path = config.get("ruta", "")
        layer = config.get("capa", "")
        fields = config.get("campos", [])

        # Temporarily disconnect signals to prevent them from firing during programmatic changes
        self.po_path_line.blockSignals(True)
        self.po_layer_combo.blockSignals(True)

        self.po_path_line.setText(path)
        
        # Manually trigger the path change logic to populate layers
        self._on_path_changed(path)

        # Now that layers are populated, try to set the correct one
        layer_index = self.po_layer_combo.findText(layer)
        if layer_index >= 0:
            self.po_layer_combo.setCurrentIndex(layer_index)

        self._selected_fields = fields
        self.po_fields_label.setText(", ".join(self._selected_fields) or "No fields selected.")

        # Reconnect signals
        self.po_path_line.blockSignals(False)
        self.po_layer_combo.blockSignals(False)