from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal

class ConfigTab(QWidget):
    configChanged = pyqtSignal(dict)  # Señal custom para notificar cambios de configuración

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        export_btn = QPushButton("Export Config")
        export_btn.setObjectName("export_config_btn")
        import_btn = QPushButton("Import Config")
        import_btn.setObjectName("import_config_btn")
        config_buttons_layout = QHBoxLayout()
        config_buttons_layout.addWidget(export_btn)
        config_buttons_layout.addWidget(import_btn)
        layout.addLayout(config_buttons_layout)
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("save_settings_btn")
        load_btn = QPushButton("Load Settings")
        load_btn.setObjectName("load_settings_btn")
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(save_btn)
        settings_layout.addWidget(load_btn)
        layout.addLayout(settings_layout)
        log_level_label = QLabel("Log Level:")
        log_level_combo = QComboBox()
        log_level_combo.setObjectName("log_level_combo")
        log_level_combo.addItems(["INFO", "DEBUG"])
        log_level_combo.setCurrentText("INFO")
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(log_level_label)
        log_level_layout.addWidget(log_level_combo)
        layout.addLayout(log_level_layout)
        self.setLayout(layout) 