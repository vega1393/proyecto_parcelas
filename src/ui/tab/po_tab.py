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