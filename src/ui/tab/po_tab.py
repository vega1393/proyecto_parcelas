from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QLabel

class POTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.po_path_line = QLineEdit()
        po_file_btn = QPushButton("Browse PO file...")
        po_file_layout = QHBoxLayout()
        po_file_layout.addWidget(self.po_path_line)
        po_file_layout.addWidget(po_file_btn)
        self.po_layer_combo = QComboBox()
        form_layout = QFormLayout()
        form_layout.addRow("PO file:", po_file_layout)
        form_layout.addRow("PO layer:", self.po_layer_combo)
        self.po_fields_btn = QPushButton("Select PO fields...")
        self.po_fields_label = QLabel("")
        po_fields_layout = QHBoxLayout()
        po_fields_layout.addWidget(self.po_fields_btn)
        po_fields_layout.addWidget(self.po_fields_label)
        form_layout.addRow("PO fields:", po_fields_layout)
        layout.addLayout(form_layout)
        self.setLayout(layout)

    def refresh_from_config(self, config: dict) -> None:
        """
        Actualiza los widgets del tab PO según la configuración recibida.
        """
        po_path = config.get("path", "")
        po_layer = config.get("layer", "")
        po_fields = config.get("fields", [])
        self.po_path_line.setText(po_path)
        self.po_fields_label.setText(", ".join(po_fields))
        # Intentar recargar capas si el archivo existe
        from src.utils.gpkg_helpers import list_layers
        import os
        self.po_layer_combo.clear()
        if po_path and os.path.exists(po_path):
            try:
                layers = list_layers(po_path)
                self.po_layer_combo.addItems(layers)
                idx = self.po_layer_combo.findText(po_layer)
                if idx >= 0:
                    self.po_layer_combo.setCurrentIndex(idx)
                else:
                    self.po_layer_combo.addItem(f"{po_layer} [NOT FOUND]")
                    self.po_layer_combo.setCurrentIndex(self.po_layer_combo.count()-1)
            except Exception:
                self.po_layer_combo.addItem("INVALID PATH")
        elif po_layer:
            self.po_layer_combo.addItem(f"{po_layer} [NOT FOUND]")
        else:
            self.po_layer_combo.addItem("") 