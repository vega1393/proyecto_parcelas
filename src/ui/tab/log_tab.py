from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit

class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Log and messages will appear here...")
        layout.addWidget(self.log_text)
        self.setLayout(layout) 