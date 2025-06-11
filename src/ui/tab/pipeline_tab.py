# src/ui/tab/pipeline_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QHBoxLayout, QProgressBar,
    QFileDialog, QScrollArea, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import Dict, Any

class PipelineTab(QWidget):
    """
    Tab for core pipeline settings and execution control.
    Manages its own state and emits signals for external actions.
    """
    runRequested = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initializes the UI components of the tab."""
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        main_vbox = QVBoxLayout(content_widget)

        # Store a direct reference to the form layout
        self.form_layout = QFormLayout()
        main_vbox.addLayout(self.form_layout)

        # --- Input / Output ---
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Path to the input geographic file (e.g., .gpkg, .shp)")
        self.input_browse_btn = QPushButton("Browse...")
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(self.input_browse_btn)

        self.output_line = QLineEdit()
        self.output_line.setPlaceholderText("Path to the output directory")
        self.output_browse_btn = QPushButton("Browse...")
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(self.output_browse_btn)

        self.form_layout.addRow("Input File:", input_layout)
        self.form_layout.addRow("Output Directory:", output_layout)

        # --- Processing Style ---
        self.style_combo = QComboBox()
        self.style_combo.addItems(["calibration", "control", "custom"])
        self.form_layout.addRow("Processing Style:", self.style_combo)

        # --- Custom Parameters ---
        self.intensity_spin = self._create_spinbox(1, 1000, 80)
        self.min_parcels_spin = self._create_spinbox(0, 100, 1)
        self.max_parcels_spin = self._create_spinbox(0, 1000, 20)
        self.min_area_spin = self._create_double_spinbox(0.01, 1000.0, 0.4, 0.01)
        self.buffer_spin = self._create_spinbox(-1000, 0, -30)
        self.min_distance_spin = self._create_double_spinbox(0.0, 1000.0, 80.0, 0.1)

        self.form_layout.addRow("Intensity (ha per parcel):", self.intensity_spin)
        self.form_layout.addRow("Min parcels per group:", self.min_parcels_spin)
        self.form_layout.addRow("Max parcels per group:", self.max_parcels_spin)
        self.form_layout.addRow("Min area (ha):", self.min_area_spin)
        self.form_layout.addRow("Buffer distance (m):", self.buffer_spin)
        self.form_layout.addRow("Min distance between parcels (m):", self.min_distance_spin)

        # --- Execution Control ---
        self.run_btn = QPushButton("Run Pipeline")
        self.stop_btn = QPushButton("Stop Process")
        self.stop_btn.setEnabled(False)
        run_stop_layout = QHBoxLayout()
        run_stop_layout.addWidget(self.run_btn)
        run_stop_layout.addWidget(self.stop_btn)
        main_vbox.addLayout(run_stop_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_vbox.addWidget(self.progress_bar)
        
        main_vbox.addStretch() # Añade un espacio flexible al final

        main_layout.addWidget(scroll)

    def _create_spinbox(self, min_val: int, max_val: int, default: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        return spin

    def _create_double_spinbox(self, min_val: float, max_val: float, default: float, step: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(step)
        return spin

    def _connect_signals(self) -> None:
        """Connects widget signals to internal slots."""
        self.input_browse_btn.clicked.connect(self._select_input_file)
        self.output_browse_btn.clicked.connect(self._select_output_dir)
        self.run_btn.clicked.connect(self.runRequested.emit)
        self.style_combo.currentTextChanged.connect(self._toggle_custom_params)
        self._toggle_custom_params(self.style_combo.currentText())

    def _select_input_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "", "Geo Files (*.shp *.gpkg *.geojson);;All Files (*)"
        )
        if file_path:
            self.input_line.setText(file_path)

    def _select_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", "")
        if dir_path:
            self.output_line.setText(dir_path)

    def _toggle_custom_params(self, style: str) -> None:
        """Enables or disables custom parameter widgets based on the selected style."""
        is_custom = (style == "custom")
        widgets = [
            self.intensity_spin, self.min_parcels_spin, self.max_parcels_spin,
            self.min_area_spin, self.buffer_spin, self.min_distance_spin
        ]
        for widget in widgets:
            widget.setEnabled(is_custom)
            label = self.form_layout.labelForField(widget)
            if label:
                label.setEnabled(is_custom)

    def get_config(self) -> Dict[str, Any]:
        """Returns the current configuration of the tab as a dictionary."""
        config = {
            "input_path": self.input_line.text().strip(),
            "output_dir": self.output_line.text().strip(),
            "style": self.style_combo.currentText(),
            "cfg_overrides": {}
        }
        if config["style"] == "custom":
            config["cfg_overrides"] = {
                "INTENSIDAD": self.intensity_spin.value(),
                "MIN_PARCELAS": self.min_parcels_spin.value(),
                "MAX_PARCELAS": self.max_parcels_spin.value(),
                "AREA_MINIMA_HA": self.min_area_spin.value(),
                "BUFFER_DISTANCE": self.buffer_spin.value(),
                "MIN_DISTANCE": self.min_distance_spin.value()
            }
        return config

    def set_config(self, config: Dict[str, Any]) -> None:
        """Sets the tab's widgets based on a configuration dictionary."""
        self.input_line.setText(config.get("input_path", ""))
        self.output_line.setText(config.get("output_dir", ""))

        style = config.get("style", "calibration")
        style_index = self.style_combo.findText(style, Qt.MatchFlag.MatchFixedString)
        if style_index >= 0:
            self.style_combo.setCurrentIndex(style_index)
        
        self._toggle_custom_params(style)

        custom_params = config.get("custom_params", {})
        self.intensity_spin.setValue(custom_params.get("intensity", 80))
        self.min_parcels_spin.setValue(custom_params.get("min_parcels", 1))
        self.max_parcels_spin.setValue(custom_params.get("max_parcels", 20))
        self.min_area_spin.setValue(custom_params.get("min_area", 0.4))
        self.buffer_spin.setValue(custom_params.get("buffer_distance", -30))
        self.min_distance_spin.setValue(custom_params.get("min_distance", 80.0))

    def set_running_state(self, is_running: bool) -> None:
        """Enables/disables buttons based on pipeline running state."""
        self.run_btn.setEnabled(not is_running)
        self.stop_btn.setEnabled(is_running)

    def update_progress(self, value: int) -> None:
        """Updates the progress bar value."""
        self.progress_bar.setValue(value)