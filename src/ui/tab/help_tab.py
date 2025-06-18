# src/ui/tab/help_tab.py

import os
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QScrollArea, QLabel, QFrame,
    QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QIcon

class HelpTab(QWidget):
    """Tab que muestra la documentación de ayuda desde help.md"""
    
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.help_file_path = "help.md"
        self._init_ui()
        self._load_help_content()

    def _init_ui(self) -> None:
        """Inicializa la interfaz de usuario del tab de ayuda."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header con título y controles
        header_widget = self._create_header()
        main_layout.addWidget(header_widget)
        
        # Área principal de contenido
        content_widget = self._create_content_area()
        main_layout.addWidget(content_widget, 1)  # Se expande para llenar espacio
        
        # Footer con información adicional
        footer_widget = self._create_footer()
        main_layout.addWidget(footer_widget)

    def _create_header(self) -> QWidget:
        """Crea el header del tab de ayuda."""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título principal
        title_label = QLabel("[📚] Help & Documentation")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("""
            QLabel {
                color: #2196f3;
                padding: 8px;
                border-bottom: 2px solid #2196f3;
            }
        """)
        
        # Botones de control
        self.refresh_btn = QPushButton("[🔄] Refresh")
        self.refresh_btn.setToolTip("Reload help documentation from help.md")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        self.edit_help_btn = QPushButton("[✏] Edit Help")
        self.edit_help_btn.setToolTip("Open help.md file for editing")
        self.edit_help_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:pressed {
                background-color: #ef6c00;
            }
        """)
        
        # Layout del header
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.edit_help_btn)
        
        # Conectar señales
        self.refresh_btn.clicked.connect(self._load_help_content)
        self.edit_help_btn.clicked.connect(self._open_help_for_editing)
        
        return header_widget

    def _create_content_area(self) -> QWidget:
        """Crea el área principal de contenido."""
        # Crear splitter para dividir tabla de contenidos y contenido
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tabla de contenidos (lado izquierdo)
        toc_widget = self._create_table_of_contents()
        splitter.addWidget(toc_widget)
        
        # Área de contenido principal (lado derecho)
        content_widget = self._create_main_content()
        splitter.addWidget(content_widget)
        
        # Configurar proporciones (20% TOC, 80% contenido)
        splitter.setSizes([200, 800])
        
        return splitter

    def _create_table_of_contents(self) -> QWidget:
        """Crea la tabla de contenidos navegable."""
        toc_widget = QWidget()
        toc_layout = QVBoxLayout(toc_widget)
        toc_layout.setContentsMargins(5, 5, 5, 5)
        
        # Título de la tabla de contenidos
        toc_title = QLabel("[📑] Table of Contents")
        toc_title.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #00d4ff;
                background-color: #2b2b2b;
                padding: 8px;
                border-bottom: 2px solid #007acc;
                border-radius: 4px;
                margin-bottom: 10px;
            }
        """)
        toc_layout.addWidget(toc_title)
        
        # Lista de contenidos (será poblada dinámicamente)
        self.toc_text = QTextEdit()
        self.toc_text.setMaximumWidth(250)
        self.toc_text.setReadOnly(True)
        self.toc_text.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 2px solid #007acc;
                border-radius: 6px;
                padding: 12px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        toc_layout.addWidget(self.toc_text)
        
        return toc_widget

    def _create_main_content(self) -> QWidget:
        """Crea el área principal de contenido."""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 5, 10, 5)
        
        # Área de texto principal con scroll
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        
        # Estilo para el contenido de ayuda
        self.help_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #007acc;
                border-radius: 8px;
                padding: 20px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        
        # Configurar fuente para mejor legibilidad
        font = QFont()
        font.setFamily("Segoe UI, Arial, sans-serif")
        font.setPointSize(11)
        self.help_text.setFont(font)
        
        content_layout.addWidget(self.help_text)
        
        return content_widget

    def _create_footer(self) -> QWidget:
        """Crea el footer con información adicional."""
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        # Línea separadora
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #e0e0e0;")
        
        # Información del archivo
        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                font-style: italic;
                padding: 5px;
            }
        """)
        
        footer_layout.addWidget(self.file_info_label)
        footer_layout.addStretch()
        
        # Crear layout vertical para incluir línea y footer
        footer_container = QWidget()
        footer_container_layout = QVBoxLayout(footer_container)
        footer_container_layout.setContentsMargins(0, 0, 0, 0)
        footer_container_layout.addWidget(line)
        footer_container_layout.addWidget(footer_widget)
        
        return footer_container

    def _load_help_content(self) -> None:
        """Carga y muestra el contenido del archivo help.md."""
        try:
            # Verificar si el archivo existe
            if not os.path.exists(self.help_file_path):
                self._show_file_not_found()
                return
            
            # Leer el archivo markdown
            with open(self.help_file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Convertir markdown a HTML
            html_content = markdown.markdown(
                markdown_content, 
                extensions=['toc', 'tables', 'fenced_code', 'codehilite']
            )
            
            # Aplicar estilos CSS personalizados
            styled_html = self._apply_custom_styles(html_content)
            
            # Mostrar contenido
            self.help_text.setHtml(styled_html)
            
            # Generar tabla de contenidos
            self._generate_table_of_contents(markdown_content)
            
            # Actualizar información del archivo
            file_size = os.path.getsize(self.help_file_path)
            file_modified = os.path.getmtime(self.help_file_path)
            import datetime
            modified_date = datetime.datetime.fromtimestamp(file_modified).strftime("%Y-%m-%d %H:%M:%S")
            
            self.file_info_label.setText(
                f"[📄] {self.help_file_path} | Size: {file_size} bytes | Modified: {modified_date}"
            )
            
        except Exception as e:
            self._show_error(f"Error loading help file: {e}")

    def _apply_custom_styles(self, html_content: str) -> str:
        """Aplica estilos CSS personalizados al HTML."""
        css_styles = """
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.7;
                color: #ffffff;
                background-color: #1e1e1e;
                max-width: none;
                margin: 0;
                padding: 20px;
            }
            h1 {
                color: #00d4ff;
                border-bottom: 3px solid #00d4ff;
                padding-bottom: 10px;
                margin-top: 30px;
                text-shadow: 0 0 5px rgba(0, 212, 255, 0.3);
            }
            h2 {
                color: #66b3ff;
                border-bottom: 2px solid #007acc;
                padding-bottom: 8px;
                margin-top: 25px;
                text-shadow: 0 0 3px rgba(102, 179, 255, 0.3);
            }
            h3 {
                color: #99ccff;
                margin-top: 20px;
            }
            h4 {
                color: #b3d9ff;
                margin-top: 15px;
            }
            code {
                background-color: #333333;
                color: #ffeb3b;
                padding: 3px 8px;
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace;
                border: 1px solid #555555;
                font-weight: bold;
            }
            pre {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #007acc;
                border-radius: 8px;
                padding: 20px;
                overflow-x: auto;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            blockquote {
                border-left: 4px solid #00d4ff;
                background-color: #1a3a4a;
                color: #e0f7ff;
                margin: 15px 0;
                padding: 15px 25px;
                font-style: italic;
                border-radius: 4px;
            }
            ul, ol {
                padding-left: 25px;
                color: #e0e0e0;
            }
            li {
                margin-bottom: 8px;
                color: #e0e0e0;
            }
            strong {
                color: #ffeb3b;
                font-weight: bold;
            }
            em {
                color: #87ceeb;
                font-style: italic;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
                background-color: #2b2b2b;
            }
            th, td {
                border: 1px solid #555555;
                padding: 12px;
                text-align: left;
                color: #ffffff;
            }
            th {
                background-color: #007acc;
                font-weight: bold;
                color: #ffffff;
            }
            .emoji {
                font-size: 1.2em;
            }
            hr {
                border: none;
                height: 3px;
                background: linear-gradient(to right, #00d4ff, #007acc, transparent);
                margin: 30px 0;
                border-radius: 2px;
            }
        </style>
        """
        
        return css_styles + html_content

    def _generate_table_of_contents(self, markdown_content: str) -> None:
        """Genera la tabla de contenidos basada en los headers del markdown."""
        lines = markdown_content.split('\n')
        toc_items = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Contar el nivel del header
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                # Extraer el título (sin los #)
                title = line[level:].strip()
                if title:
                    indent = "  " * (level - 1)
                    toc_items.append(f"{indent}• {title}")
        
        if toc_items:
            toc_html = "<br>".join(toc_items)
            self.toc_text.setHtml(f"<div style='color: #ffffff; font-size: 12px; line-height: 1.6; font-weight: bold;'>{toc_html}</div>")
        else:
            self.toc_text.setHtml("<div style='color: #cccccc; font-style: italic;'>No table of contents available</div>")

    def _show_file_not_found(self) -> None:
        """Muestra mensaje cuando no se encuentra el archivo help.md."""
        not_found_html = """
        <div style="text-align: center; padding: 50px; color: #666;">
            <h2>[📄] Help File Not Found</h2>
            <p>The help documentation file <code>help.md</code> was not found in the project directory.</p>
            <p>Please ensure the file exists or click <strong>"Edit Help"</strong> to create it.</p>
            <hr>
            <p><em>Expected location: {}</em></p>
        </div>
        """.format(os.path.abspath(self.help_file_path))
        
        self.help_text.setHtml(not_found_html)
        self.toc_text.setText("No content available")
        self.file_info_label.setText(f"[❌] File not found: {self.help_file_path}")

    def _show_error(self, error_message: str) -> None:
        """Muestra mensaje de error."""
        error_html = f"""
        <div style="text-align: center; padding: 50px; color: #d32f2f;">
            <h2>[⚠] Error Loading Help</h2>
            <p>{error_message}</p>
            <p>Please check the file format and try refreshing.</p>
        </div>
        """
        
        self.help_text.setHtml(error_html)
        self.toc_text.setText("Error loading content")
        self.file_info_label.setText(f"[❌] Error: {error_message}")

    def _open_help_for_editing(self) -> None:
        """Abre el archivo help.md para edición."""
        try:
            import subprocess
            import platform
            
            # Crear el archivo si no existe
            if not os.path.exists(self.help_file_path):
                with open(self.help_file_path, 'w', encoding='utf-8') as f:
                    f.write("# Help Documentation\n\nAdd your help content here...\n")
            
            # Abrir con el editor por defecto según el sistema operativo
            if platform.system() == 'Windows':
                os.startfile(self.help_file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', self.help_file_path])
            else:  # Linux
                subprocess.run(['xdg-open', self.help_file_path])
                
        except Exception as e:
            QMessageBox.warning(
                self, 
                "Cannot Open File", 
                f"Could not open help.md for editing:\n{e}\n\nPlease open the file manually in your preferred text editor."
            )

    def refresh_content(self) -> None:
        """Método público para refrescar el contenido (útil para llamar desde fuera)."""
        self._load_help_content() 