"""
Main window for the Parcel Generator application using PyQt6.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QTextEdit, QMessageBox,
    QListWidget, QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt, QProcess
from src.utils.settings import load_gui_settings, save_gui_settings
from src.utils.gpkg_helpers import list_layers, list_fields
from src.core.pipeline import ejecutar_proceso
import os
import json
import tempfile

class ParcelGeneratorApp(QMainWindow):
    """
    Main application window for the Parcel Generator.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Parcel Generator")
        self.setMinimumSize(900, 650)
        self.settings = load_gui_settings()
        self.po_layer = None
        self.po_fields = []
        self.exclusion_list = self.settings.get("exclusion_list", [])
        self.process = None
        self._init_ui()
        self._restore_gui_settings()

    def _init_ui(self) -> None:
        """
        Initializes the main UI layout.
        """
        central_widget = QWidget()
        main_layout = QVBoxLayout()

        # Form for input parameters
        form_layout = QFormLayout()

        # Input file
        self.input_line = QLineEdit()
        input_btn = QPushButton("Browse...")
        input_btn.clicked.connect(self._select_input_file)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(input_btn)
        form_layout.addRow("Input file:", input_layout)

        # Output directory
        self.output_line = QLineEdit()
        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(self._select_output_dir)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_btn)
        form_layout.addRow("Output directory:", output_layout)

        # Processing style
        self.style_combo = QComboBox()
        self.style_combo.addItems(["calibration", "control", "custom"])
        self.style_combo.currentTextChanged.connect(self._on_style_changed)
        form_layout.addRow("Processing style:", self.style_combo)

        # Advanced parameters (only for 'custom')
        self.intensity_spin = QSpinBox()
        self.intensity_spin.setRange(1, 1000)
        self.intensity_spin.setValue(50)
        form_layout.addRow("Intensity (ha per parcel):", self.intensity_spin)

        self.min_parcels_spin = QSpinBox()
        self.min_parcels_spin.setRange(1, 100)
        self.min_parcels_spin.setValue(1)
        form_layout.addRow("Min parcels per group:", self.min_parcels_spin)

        self.max_parcels_spin = QSpinBox()
        self.max_parcels_spin.setRange(1, 100)
        self.max_parcels_spin.setValue(10)
        form_layout.addRow("Max parcels per group:", self.max_parcels_spin)

        self.min_area_spin = QDoubleSpinBox()
        self.min_area_spin.setRange(0.01, 100.0)
        self.min_area_spin.setSingleStep(0.01)
        self.min_area_spin.setValue(0.3)
        form_layout.addRow("Min area (ha):", self.min_area_spin)

        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(-1000, 1000)
        self.buffer_spin.setValue(-20)
        form_layout.addRow("Buffer distance (m):", self.buffer_spin)

        self.min_distance_spin = QDoubleSpinBox()
        self.min_distance_spin.setRange(0.0, 1000.0)
        self.min_distance_spin.setSingleStep(0.1)
        self.min_distance_spin.setValue(60.0)
        form_layout.addRow("Min distance between parcels (m):", self.min_distance_spin)

        # Hide advanced params by default
        self._set_advanced_params_visible(False)

        main_layout.addLayout(form_layout)

        # --- Plan Operative (PO) Section ---
        po_layout = QFormLayout()
        po_label = QLabel("Plan Operative (PO):")
        po_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(po_label)

        # PO file and layer
        self.po_path_line = QLineEdit()
        po_file_btn = QPushButton("Browse PO file...")
        po_file_btn.clicked.connect(self._select_po_file)
        po_file_layout = QHBoxLayout()
        po_file_layout.addWidget(self.po_path_line)
        po_file_layout.addWidget(po_file_btn)
        po_layout.addRow("PO file:", po_file_layout)

        self.po_layer_combo = QComboBox()
        po_layout.addRow("PO layer:", self.po_layer_combo)
        self.po_layer_combo.currentTextChanged.connect(self._on_po_layer_changed)

        # PO fields
        self.po_fields_btn = QPushButton("Select PO fields...")
        self.po_fields_btn.clicked.connect(self._select_po_fields)
        self.po_fields_label = QLabel("")
        po_fields_layout = QHBoxLayout()
        po_fields_layout.addWidget(self.po_fields_btn)
        po_fields_layout.addWidget(self.po_fields_label)
        po_layout.addRow("PO fields:", po_fields_layout)

        main_layout.addLayout(po_layout)

        # --- Exclusion Layers Section ---
        excl_label = QLabel("Exclusion Layers:")
        excl_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(excl_label)

        excl_layout = QHBoxLayout()
        self.excl_list_widget = QListWidget()
        excl_layout.addWidget(self.excl_list_widget)
        excl_btns_layout = QVBoxLayout()
        excl_add_btn = QPushButton("Add exclusion...")
        excl_add_btn.clicked.connect(self._add_exclusion)
        excl_remove_btn = QPushButton("Remove selected")
        excl_remove_btn.clicked.connect(self._remove_exclusion)
        excl_btns_layout.addWidget(excl_add_btn)
        excl_btns_layout.addWidget(excl_remove_btn)
        excl_btns_layout.addStretch()
        excl_layout.addLayout(excl_btns_layout)
        main_layout.addLayout(excl_layout)
        self._update_exclusion_list()

        # Save/Load settings buttons
        settings_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_gui_settings)
        load_btn = QPushButton("Load Settings")
        load_btn.clicked.connect(self._restore_gui_settings)
        settings_layout.addWidget(save_btn)
        settings_layout.addWidget(load_btn)
        main_layout.addLayout(settings_layout)

        # Run button
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._on_run_clicked)
        main_layout.addWidget(self.run_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Log/messages area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Log and messages will appear here...")
        main_layout.addWidget(self.log_text)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    # --- PO and Exclusion logic ---
    def _select_po_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PO file", "", "Geo Files (*.shp *.gpkg *.geojson *.gdb);;All Files (*)")
        if file_path:
            self.po_path_line.setText(file_path)
            layers = list_layers(file_path)
            self.po_layer_combo.clear()
            self.po_layer_combo.addItems(layers)
            if layers:
                self.po_layer_combo.setCurrentIndex(0)
            self.po_fields = []
            self.po_fields_label.setText("")

    def _on_po_layer_changed(self, layer: str) -> None:
        self.po_layer = layer
        self.po_fields = []
        self.po_fields_label.setText("")

    def _select_po_fields(self) -> None:
        file_path = self.po_path_line.text()
        layer = self.po_layer_combo.currentText()
        if not file_path or not layer:
            QMessageBox.warning(self, "PO selection", "Please select a PO file and layer first.")
            return
        fields = list_fields(file_path, layer)
        if not fields:
            QMessageBox.warning(self, "PO selection", "No fields found in the selected layer.")
            return
        selected, ok = QInputDialog.getItem(self, "Select PO fields", "Fields (comma separated):", [", ".join(fields)], 0, True)
        if ok and selected:
            self.po_fields = [f.strip() for f in selected.split(",") if f.strip()]
            self.po_fields_label.setText(", ".join(self.po_fields))

    def _add_exclusion(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select exclusion file", "", "Geo Files (*.shp *.gpkg *.geojson *.gdb);;All Files (*)")
        if not file_path:
            return
        layer = None
        if file_path.lower().endswith((".gpkg", ".gdb")):
            layers = list_layers(file_path)
            if not layers:
                QMessageBox.warning(self, "No layers found", f"No layers found in {file_path}")
                return
            if len(layers) == 1:
                layer = layers[0]
            else:
                layer, ok = self._select_layer_dialog(layers)
                if not ok:
                    return
        desc, ok = QInputDialog.getText(self, "Exclusion description", "Description:", text=os.path.basename(file_path))
        if not ok:
            return
        exclusion = {"path": file_path, "layer": layer, "description": desc}
        self.exclusion_list.append(exclusion)
        self._update_exclusion_list()

    def _remove_exclusion(self) -> None:
        selected = self.excl_list_widget.currentRow()
        if selected >= 0:
            self.exclusion_list.pop(selected)
            self._update_exclusion_list()

    def _update_exclusion_list(self) -> None:
        self.excl_list_widget.clear()
        for excl in self.exclusion_list:
            text = excl.get("description", os.path.basename(excl.get("path", "Unknown")))
            if excl.get("layer"):
                text += f" ({excl['layer']})"
            self.excl_list_widget.addItem(QListWidgetItem(text))

    # --- Existing logic ---
    def _select_input_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select input file", "", "Geo Files (*.shp *.gpkg *.geojson);;All Files (*)")
        if file_path:
            self.input_line.setText(file_path)
            if file_path.lower().endswith(('.gpkg', '.gdb')):
                layers = list_layers(file_path)
                if not layers:
                    QMessageBox.warning(self, "No layers found", f"No layers found in {file_path}")
                    return
                if len(layers) == 1:
                    self.log_text.append(f"[INFO] Only one layer found: {layers[0]}")
                else:
                    layer, ok = self._select_layer_dialog(layers)
                    if ok:
                        self.log_text.append(f"[INFO] Selected layer: {layer}")
                    else:
                        self.input_line.clear()
                        return

    def _select_layer_dialog(self, layers):
        layer, ok = QInputDialog.getItem(self, "Select Layer", "Available layers:", layers, 0, False)
        return layer, ok

    def _select_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select output directory", "")
        if dir_path:
            self.output_line.setText(dir_path)

    def _on_style_changed(self, style: str) -> None:
        self._set_advanced_params_visible(style == "custom")

    def _set_advanced_params_visible(self, visible: bool) -> None:
        self.intensity_spin.setVisible(visible)
        self.min_parcels_spin.setVisible(visible)
        self.max_parcels_spin.setVisible(visible)
        self.min_area_spin.setVisible(visible)
        self.buffer_spin.setVisible(visible)
        self.min_distance_spin.setVisible(visible)

    def _on_run_clicked(self) -> None:
        # Validate inputs
        input_path = self.input_line.text().strip()
        output_dir = self.output_line.text().strip()
        style = self.style_combo.currentText()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Input required", "Please select a valid input file.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Output required", "Please select an output directory.")
            return
        # Prepare cfg_overrides
        cfg_overrides = {}
        if style == "custom":
            cfg_overrides = {
                "INTENSITY": self.intensity_spin.value(),
                "MIN_PARCELS": self.min_parcels_spin.value(),
                "MAX_PARCELS": self.max_parcels_spin.value(),
                "MIN_AREA": self.min_area_spin.value(),
                "BUFFER_DISTANCE": self.buffer_spin.value(),
                "MIN_DISTANCE": self.min_distance_spin.value()
            }
        # PO config
        po_config = {
            "ruta": self.po_path_line.text(),
            "capa": self.po_layer_combo.currentText(),
            "campos": self.po_fields
        } if self.po_path_line.text() and self.po_layer_combo.currentText() else None
        if po_config:
            cfg_overrides["PO_CONFIG"] = po_config
        # Exclusions
        if self.exclusion_list:
            cfg_overrides["CAPAS_EXCLUSION"] = self.exclusion_list
        # Prepare params
        params = {
            "input_path": input_path,
            "output_dir": output_dir,
            "entrega": None,  # Could be added as a field if needed
            "style": style,
            "cfg_overrides": cfg_overrides
        }
        # Crear carpeta json_config si no existe
        json_config_dir = os.path.join(os.path.dirname(__file__), "..", "json_config")
        os.makedirs(json_config_dir, exist_ok=True)
        # Escribir params en un archivo JSON temporal dentro de json_config
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json", dir=json_config_dir) as tmp:
            json.dump(params, tmp)
            tmp_path = tmp.name
        # Start QProcess
        self.progress_bar.setValue(0)
        self.log_text.append("[INFO] Starting processing (QProcess)...")
        self.run_btn.setEnabled(False)
        self.process = QProcess(self)
        self.process.setProgram("python")
        self.process.setArguments([os.path.join(os.path.dirname(__file__), "..", "run_pipeline.py"), tmp_path])
        self.process.readyReadStandardOutput.connect(self._on_process_stdout)
        self.process.readyReadStandardError.connect(self._on_process_stderr)
        self.process.finished.connect(self._on_process_finished)
        self.process.start()

    def _on_process_stdout(self):
        while self.process.canReadLine():
            line = self.process.readLine().data().decode().strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get("type") == "progress":
                    self.progress_bar.setValue(msg.get("value", 0))
                    self.log_text.append(f"[PROGRESS] {msg.get('value', 0)}% - {msg.get('status', '')}")
                elif msg.get("type") == "success":
                    self.progress_bar.setValue(100)
                    self.log_text.append("[SUCCESS] Processing completed successfully.")
                    QMessageBox.information(self, "Process completed", "Parcel generation completed successfully.")
                    self.run_btn.setEnabled(True)
                elif msg.get("type") == "error":
                    self.log_text.append(f"[ERROR] {msg.get('message', '')}")
                    QMessageBox.critical(self, "Error", f"An error occurred during processing:\n{msg.get('message', '')}")
                    self.run_btn.setEnabled(True)
            except Exception:
                self.log_text.append(f"[STDOUT] {line}")

    def _on_process_stderr(self):
        while self.process.canReadLine():
            line = self.process.readLine().data().decode().strip()
            self.log_text.append(f"[STDERR] {line}")

    def _on_process_finished(self):
        self.run_btn.setEnabled(True)
        self.process = None

    def _save_gui_settings(self) -> None:
        settings = {
            "input_path": self.input_line.text(),
            "output_dir": self.output_line.text(),
            "style": self.style_combo.currentText(),
            "custom_params": {
                "intensity": self.intensity_spin.value(),
                "min_parcels": self.min_parcels_spin.value(),
                "max_parcels": self.max_parcels_spin.value(),
                "min_area": self.min_area_spin.value(),
                "buffer_distance": self.buffer_spin.value(),
                "min_distance": self.min_distance_spin.value()
            },
            "po_config": {
                "path": self.po_path_line.text(),
                "layer": self.po_layer_combo.currentText(),
                "fields": self.po_fields
            },
            "exclusion_list": self.exclusion_list,
            "intensity_by_field": self.settings.get("intensity_by_field", {})
        }
        save_gui_settings(settings)
        self.log_text.append("[INFO] Settings saved.")

    def _restore_gui_settings(self) -> None:
        settings = load_gui_settings()
        self.input_line.setText(settings.get("input_path", ""))
        self.output_line.setText(settings.get("output_dir", ""))
        style = settings.get("style", "calibration")
        idx = self.style_combo.findText(style)
        if idx >= 0:
            self.style_combo.setCurrentIndex(idx)
        params = settings.get("custom_params", {})
        self.intensity_spin.setValue(params.get("intensity", 50))
        self.min_parcels_spin.setValue(params.get("min_parcels", 1))
        self.max_parcels_spin.setValue(params.get("max_parcels", 10))
        self.min_area_spin.setValue(params.get("min_area", 0.3))
        self.buffer_spin.setValue(params.get("buffer_distance", -20))
        self.min_distance_spin.setValue(params.get("min_distance", 60.0))
        # Restore PO
        po_conf = settings.get("po_config", {})
        self.po_path_line.setText(po_conf.get("path", ""))
        layers = list_layers(po_conf.get("path", "")) if po_conf.get("path") else []
        self.po_layer_combo.clear()
        self.po_layer_combo.addItems(layers)
        if po_conf.get("layer") and po_conf.get("layer") in layers:
            self.po_layer_combo.setCurrentText(po_conf.get("layer"))
        self.po_fields = po_conf.get("fields", [])
        self.po_fields_label.setText(", ".join(self.po_fields))
        # Restore exclusions
        self.exclusion_list = settings.get("exclusion_list", [])
        self._update_exclusion_list()
        self.settings = settings
        self.log_text.append("[INFO] Settings loaded.") 