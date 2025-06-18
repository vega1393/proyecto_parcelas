# src/ui/tab/po_tab.py

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox,
    QHBoxLayout, QLabel, QFileDialog, QMessageBox, QDialog, QScrollArea
)
from PyQt6.QtCore import pyqtSignal
from typing import Dict, List, Any

from src.utils.gpkg_helpers import list_layers, list_fields
from src.utils.dialog_utils import EnhancedFileDialog, create_geo_file_filter
from src.ui.dialogs.po_fields_dialog import POFieldsDialog

class POTab(QWidget):
    configChanged = pyqtSignal(dict)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._selected_fields: List[str] = []
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QFormLayout(content_widget)

        # PO File Path
        self.po_path_line = QLineEdit()
        self.po_path_line.setPlaceholderText("Path to the Plan Operative file (e.g., .gpkg, .shp)")
        self.po_file_btn = QPushButton("Browse...")
        po_file_layout = QHBoxLayout()
        po_file_layout.addWidget(self.po_path_line); po_file_layout.addWidget(self.po_file_btn)
        form_layout.addRow("PO File:", po_file_layout)

        # PO Layer
        self.po_layer_combo = QComboBox()
        form_layout.addRow("PO Layer:", self.po_layer_combo)

        # PO Fields to Join
        self.po_fields_btn = QPushButton("Select PO Fields...")
        self.po_fields_label = QLabel("No fields selected.")
        self.po_fields_label.setWordWrap(True)
        po_fields_layout = QHBoxLayout()
        po_fields_layout.addWidget(self.po_fields_btn); po_fields_layout.addWidget(self.po_fields_label, 1)
        form_layout.addRow("PO Fields to Join:", po_fields_layout)

        # [NUEVO] Campos para generar el ID de la parcela
        form_layout.addRow(QLabel("<b>Parcel ID Generation Fields:</b>"))
        self.id_predio_line = QLineEdit()
        self.id_predio_line.setPlaceholderText("e.g., idpredio, fazenda")
        form_layout.addRow("Property/Predio Field:", self.id_predio_line)
        
        self.id_tipo_uso_line = QLineEdit()
        self.id_tipo_uso_line.setPlaceholderText("e.g., tipo_uso, tipouso")
        form_layout.addRow("Use Type Field:", self.id_tipo_uso_line)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        self.po_file_btn.clicked.connect(self._select_po_file)
        self.po_path_line.textChanged.connect(self._on_path_changed)
        self.po_layer_combo.currentTextChanged.connect(self._on_layer_changed)
        self.po_fields_btn.clicked.connect(self._select_po_fields)
        # Conectar los nuevos campos para que emitan la señal de cambio
        self.id_predio_line.textChanged.connect(lambda: self.configChanged.emit(self.get_config()))
        self.id_tipo_uso_line.textChanged.connect(lambda: self.configChanged.emit(self.get_config()))

    def _select_po_file(self):
        path, _ = EnhancedFileDialog.get_open_file_name(
            self, "Select PO File", "", create_geo_file_filter()
        )
        if path:
            self.po_path_line.setText(path)
            self._on_path_changed(path)

    def _on_path_changed(self, path: str):
        self.po_layer_combo.clear(); self._selected_fields = []; self.po_fields_label.setText("No fields selected.")
        if path and os.path.exists(path):
            try:
                layers = list_layers(path)
                if layers: self.po_layer_combo.addItems(layers)
                else: self.po_layer_combo.addItem("[NO LAYERS FOUND]")
            except Exception: self.po_layer_combo.addItem("[ERROR LISTING LAYERS]")
        else: self.po_layer_combo.addItem("[INVALID FILE PATH]")
        self.configChanged.emit(self.get_config())

    def _on_layer_changed(self):
        self._selected_fields = []; self.po_fields_label.setText("No fields selected.")
        self.configChanged.emit(self.get_config())
    
    def _select_po_fields(self):
        file_path = self.po_path_line.text(); layer_name = self.po_layer_combo.currentText()
        if not (file_path and os.path.exists(file_path) and layer_name and not layer_name.startswith("[")):
            QMessageBox.warning(self, "PO Configuration Error", "Please select a valid PO file and layer first."); return
        try:
            available_fields = list_fields(file_path, layer_name)
            if not available_fields: QMessageBox.information(self, "No Fields", f"No attribute fields found in layer '{layer_name}'."); return
            dialog = POFieldsDialog(available_fields, self._selected_fields, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._selected_fields = dialog.get_selected_fields()
                self.po_fields_label.setText(", ".join(self._selected_fields) or "No fields selected.")
                self.configChanged.emit(self.get_config())
        except Exception as e:
            QMessageBox.critical(self, "Field Listing Error", f"Could not list fields for layer '{layer_name}':\n{e}")


    def get_config(self) -> Dict[str, Any]:
        """Returns the current PO configuration as a dictionary."""
        path = self.po_path_line.text(); layer = self.po_layer_combo.currentText()
        if path and os.path.exists(path) and layer and not layer.startswith("["):
            return {
                "ruta": path,
                "capa": layer,
                "campos": self._selected_fields,
                # [NUEVO] Añadir la configuración de los campos para el ID
                "campos_id_fasa": {
                    "predio": self.id_predio_line.text().strip(),
                    "tipo": self.id_tipo_uso_line.text().strip()
                }
            }
        return {}

    def set_config(self, config: Dict[str, Any]) -> None:
        """Sets the tab's widgets based on a PO configuration dictionary."""
        path = config.get("ruta", ""); layer = config.get("capa", ""); fields = config.get("campos", [])
        id_config = config.get("campos_id_fasa", {})
        predio_field = id_config.get("predio", "id_predio") # Default
        tipo_field = id_config.get("tipo", "tipouso") # Default

        self.po_path_line.blockSignals(True); self.po_layer_combo.blockSignals(True)
        self.id_predio_line.blockSignals(True); self.id_tipo_uso_line.blockSignals(True)

        self.po_path_line.setText(path)
        self._on_path_changed(path)
        layer_index = self.po_layer_combo.findText(layer)
        if layer_index >= 0: self.po_layer_combo.setCurrentIndex(layer_index)

        self._selected_fields = fields
        self.po_fields_label.setText(", ".join(self._selected_fields) or "No fields selected.")
        
        # [NUEVO] Restaurar los valores de los nuevos campos
        self.id_predio_line.setText(predio_field)
        self.id_tipo_uso_line.setText(tipo_field)

        self.po_path_line.blockSignals(False); self.po_layer_combo.blockSignals(False)
        self.id_predio_line.blockSignals(False); self.id_tipo_uso_line.blockSignals(False)