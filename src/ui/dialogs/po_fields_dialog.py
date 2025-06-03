# src/ui/dialogs/po_fields_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QCheckBox, QPushButton, QDialogButtonBox, QLabel, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List

class POFieldsDialog(QDialog):
    """
    A custom dialog for selecting PO fields with checkboxes.
    """
    fieldsSelected = pyqtSignal(list)

    def __init__(self, available_fields: List[str], selected_fields: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select PO Fields")
        self.setMinimumWidth(400)
        self.available_fields = available_fields
        self.selected_fields_on_init = selected_fields

        layout = QVBoxLayout(self)

        # Description label
        description_label = QLabel(
            "Select the fields from the Plan Operative layer to be included:"
        )
        layout.addWidget(description_label)

        # Buttons for select/deselect all
        select_buttons_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        select_buttons_layout.addWidget(self.select_all_btn)
        select_buttons_layout.addWidget(self.deselect_all_btn)
        layout.addLayout(select_buttons_layout)

        # Scroll Area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(scroll_content_widget)
        self.checkbox_layout.setContentsMargins(5, 5, 5, 5) # Add some margin
        self.checkbox_layout.setSpacing(6) # Spacing between checkboxes

        self.checkboxes: List[QCheckBox] = []
        for field_name in self.available_fields:
            checkbox = QCheckBox(field_name)
            if field_name in self.selected_fields_on_init:
                checkbox.setChecked(True)
            self.checkboxes.append(checkbox)
            self.checkbox_layout.addWidget(checkbox)
        
        self.checkbox_layout.addStretch() # Pushes checkboxes to the top
        scroll_content_widget.setLayout(self.checkbox_layout)
        scroll_area.setWidget(scroll_content_widget)
        layout.addWidget(scroll_area)

        # Dialog buttons (OK, Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def _select_all(self):
        """Checks all checkboxes."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)

    def _deselect_all(self):
        """Unchecks all checkboxes."""
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def _on_accept(self):
        """Emits the selected fields and accepts the dialog."""
        selected = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        self.fieldsSelected.emit(selected)
        self.accept()

    def get_selected_fields(self) -> List[str]:
        """Returns the list of selected field names."""
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]