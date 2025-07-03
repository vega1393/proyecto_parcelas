# src/ui/tab/exclusion_tab.py

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QHBoxLayout, QFileDialog, QMessageBox, QInputDialog, QScrollArea
)
from PyQt6.QtCore import pyqtSignal
from typing import List, Dict, Any, Optional

# Se asume que este helper existe y funciona
from src.utils.gpkg_helpers import list_layers
from src.utils.dialog_utils import EnhancedFileDialog, create_geo_file_filter

class ExclusionTab(QWidget):
    """
    Tab for managing exclusion layers. Encapsulates its own logic
    and emits a signal when the exclusion list changes.
    """
    configChanged = pyqtSignal(list)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._exclusion_list: List[Dict[str, Any]] = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initializes the UI components of the tab."""
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        layout.addWidget(QLabel("Exclusion Layers:"))
        self.excl_list_widget = QListWidget()
        layout.addWidget(self.excl_list_widget)

        self.add_btn = QPushButton("Add Exclusion...")
        self.remove_btn = QPushButton("Remove Selected")
        btns_layout = QHBoxLayout()
        btns_layout.addWidget(self.add_btn)
        btns_layout.addWidget(self.remove_btn)
        layout.addLayout(btns_layout)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        """Connects widget signals to internal slots."""
        self.add_btn.clicked.connect(self._add_exclusion)
        self.remove_btn.clicked.connect(self._remove_exclusion)

    def _add_exclusion(self) -> None:
        """Guides the user through adding a new exclusion layer."""
        initial_dir = os.path.expanduser("~") 
        if self._exclusion_list:
            last_item_path = self._exclusion_list[-1].get("path")
            if last_item_path and os.path.exists(last_item_path):
                initial_dir = os.path.dirname(last_item_path)

        file_path, _ = EnhancedFileDialog.get_open_file_name(
            self, "Select Exclusion File", initial_dir, create_geo_file_filter()
        )
        if not file_path:
            return

        layer: Optional[str] = None
        if file_path.lower().endswith((".gpkg", ".gdb")):
            try:
                layers = list_layers(file_path)
                if not layers:
                    QMessageBox.warning(self, "No Layers Found", f"No layers could be found in {file_path}.")
                    return
                if len(layers) == 1:
                    layer = layers[0]
                else:
                    layer, ok = QInputDialog.getItem(self, "Select Layer", "Available layers:", layers, 0, False)
                    if not ok:
                        return
            except Exception as e:
                QMessageBox.critical(self, "Layer Listing Error", f"Could not list layers: {e}")
                return

        desc, ok = QInputDialog.getText(self, "Exclusion Description", "Enter a description:", text=os.path.basename(file_path))
        if not ok or not desc:
            return

        # The internal format always uses 'path', 'layer', 'description'
        exclusion_item = {"path": file_path, "layer": layer, "description": desc}
        self._exclusion_list.append(exclusion_item)
        self._update_list_widget()
        self.configChanged.emit(self.get_config())

    def _remove_exclusion(self) -> None:
        """Removes the currently selected exclusion layer from the list."""
        selected_row = self.excl_list_widget.currentRow()
        if selected_row >= 0:
            reply = QMessageBox.question(
                self, "Confirm Removal", "Are you sure you want to remove the selected exclusion layer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._exclusion_list.pop(selected_row)
                self._update_list_widget()
                self.configChanged.emit(self.get_config())

    def _update_list_widget(self) -> None:
        """Refreshes the QListWidget from the internal _exclusion_list safely."""
        self.excl_list_widget.clear()
        for item in self._exclusion_list:
            file_path = item.get("path")
            
            # Use description if available, otherwise fallback safely to filename
            # <--- CAMBIO CLAVE PARA CORREGIR EL ERROR
            if item.get("description"):
                text = item["description"]
            elif file_path:
                text = os.path.basename(file_path)
            else:
                text = "Invalid Item"

            if item.get("layer"):
                text += f" ({item['layer']})"
            
            list_item = QListWidgetItem(text)
            list_item.setToolTip(file_path or "No path specified")
            self.excl_list_widget.addItem(list_item)

    def get_config(self) -> List[Dict[str, Any]]:
        """Returns the current list of exclusion layers in pipeline format."""
        pipeline_format_list = []
        for item in self._exclusion_list:
            # Convert internal format to pipeline format ('ruta', 'capa', 'descripcion')
            pipeline_format_list.append({
                "ruta": item.get("path"),
                "capa": item.get("layer"),
                "descripcion": item.get("description")
            })
        return pipeline_format_list

    def set_config(self, config: List[Dict[str, Any]]) -> None:
        """Sets the exclusion list from a configuration list, handling old and new formats."""
        self._exclusion_list = []
        if not config: # Handle empty or None config
            self._update_list_widget()
            return
            
        for item in config:
            # <--- CAMBIO CLAVE PARA COMPATIBILIDAD
            # Be robust: check for pipeline key ('ruta') and old settings key ('path')
            file_path = item.get("ruta") or item.get("path")
            layer = item.get("capa") or item.get("layer")
            description = item.get("descripcion") or item.get("description")
            
            # The internal format is always 'path', 'layer', 'description'
            self._exclusion_list.append({
                "path": file_path,
                "layer": layer,
                "description": description
            })
        self._update_list_widget()