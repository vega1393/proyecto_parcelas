# src/ui/tab/po_tab.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QLabel

class POTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.po_path_line = QLineEdit()
        self.po_path_line.setPlaceholderText("Path to the Plan Operative file (e.g., .gpkg, .shp)") # Placeholder
        self.po_file_btn = QPushButton("Browse PO file...")
        po_file_layout = QHBoxLayout()
        po_file_layout.addWidget(self.po_path_line)
        po_file_layout.addWidget(self.po_file_btn)

        self.po_layer_combo = QComboBox()

        form_layout = QFormLayout()
        form_layout.addRow("PO file:", po_file_layout)
        form_layout.addRow("PO layer:", self.po_layer_combo)

        self.po_fields_btn = QPushButton("Select PO fields...")
        self.po_fields_label = QLabel("") # This label will display selected fields
        self.po_fields_label.setWordWrap(True) # Allow text to wrap

        po_fields_layout = QHBoxLayout()
        po_fields_layout.addWidget(self.po_fields_btn)
        po_fields_layout.addWidget(self.po_fields_label, 1) # Give label more stretch factor

        form_layout.addRow("PO fields:", po_fields_layout)
        layout.addLayout(form_layout)
        layout.addStretch() # Pushes content to the top
        self.setLayout(layout)

    def refresh_from_config(self, config: dict) -> None:
        """
        Updates the PO tab widgets based on the provided configuration.
        """
        po_path = config.get("path", "")
        po_layer = config.get("layer", "")
        po_fields = config.get("fields", [])

        self.po_path_line.setText(po_path)
        self.po_fields_label.setText(", ".join(po_fields))

        # Import list_layers locally to avoid circular imports at module level if any
        from src.utils.gpkg_helpers import list_layers
        import os

        self.po_layer_combo.clear()
        if po_path and os.path.exists(po_path):
            try:
                layers = list_layers(po_path)
                self.po_layer_combo.addItems(layers)
                if layers and po_layer in layers:
                    self.po_layer_combo.setCurrentText(po_layer)
                elif po_layer: # Layer was specified but not found
                    self.po_layer_combo.addItem(f"{po_layer} [NOT FOUND]")
                    self.po_layer_combo.setCurrentText(f"{po_layer} [NOT FOUND]")
            except Exception: # Handle potential errors during list_layers
                self.po_layer_combo.addItem("[ERROR LISTING LAYERS]")
        elif po_layer: # Path is not set or invalid, but layer name was in config
             self.po_layer_combo.addItem(f"{po_layer} [FILE NOT FOUND/SET]")
             self.po_layer_combo.setCurrentText(f"{po_layer} [FILE NOT FOUND/SET]")
        # If no path, layer combo remains empty or with a placeholder if desired