"""
Dialog utilities for enhanced file dialogs with geodatabase support.
Provides specialized QFileDialog implementations that treat .gdb folders as selectable files.
"""

import os
from typing import Optional, Tuple
from PyQt6.QtWidgets import QFileDialog, QWidget


class EnhancedFileDialog:
    """
    Enhanced file dialog utilities with geodatabase support.
    Uses a simpler approach with post-processing to handle .gdb folders.
    """
    
    @staticmethod
    def get_open_file_name(
        parent: Optional[QWidget] = None,
        caption: str = "",
        directory: str = "",
        filter_string: str = "",
        initial_filter: str = ""
    ) -> Tuple[str, str]:
        """
        Enhanced version of QFileDialog.getOpenFileName with geodatabase support.
        
        This implementation uses a hybrid approach:
        1. First tries directory selection if user might want .gdb
        2. Falls back to file selection for other formats
        
        Args:
            parent: Parent widget
            caption: Dialog caption
            directory: Initial directory
            filter_string: File filter string
            initial_filter: Initially selected filter
            
        Returns:
            Tuple of (selected_file_path, selected_filter)
        """
        
        # Check if .gdb is in the filter string to decide approach
        supports_gdb = ".gdb" in filter_string.lower()
        
        if supports_gdb:
            # For GIS files that include .gdb, we need special handling
            return EnhancedFileDialog._get_geo_file_with_gdb_support(
                parent, caption, directory, filter_string, initial_filter
            )
        else:
            # Standard file dialog for non-GIS files
            return QFileDialog.getOpenFileName(
                parent, caption, directory, filter_string, initial_filter
            )
    
    @staticmethod
    def _get_geo_file_with_gdb_support(
        parent: Optional[QWidget] = None,
        caption: str = "",
        directory: str = "",
        filter_string: str = "",
        initial_filter: str = ""
    ) -> Tuple[str, str]:
        """
        Special handling for geospatial files including .gdb support.
        """
        from PyQt6.QtWidgets import QMessageBox, QInputDialog
        
        # First, try standard file dialog
        file_path, selected_filter = QFileDialog.getOpenFileName(
            parent, caption, directory, filter_string, initial_filter
        )
        
        # If user selected something, check if it's what they wanted
        if file_path:
            return file_path, selected_filter
        
        # If no file was selected, offer .gdb selection option
        if not file_path:
            # Ask user if they want to select a .gdb folder
            reply = QMessageBox.question(
                parent,
                "Select Geodatabase?",
                "No file was selected. Would you like to select a Geodatabase (.gdb) folder instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Use directory dialog for .gdb selection
                gdb_path = QFileDialog.getExistingDirectory(
                    parent,
                    "Select Geodatabase (.gdb folder)",
                    directory
                )
                
                if gdb_path and gdb_path.lower().endswith('.gdb'):
                    # Return the .gdb path with appropriate filter
                    gdb_filter = "Geodatabase (*.gdb)"
                    return gdb_path, gdb_filter
                elif gdb_path and not gdb_path.lower().endswith('.gdb'):
                    QMessageBox.warning(
                        parent,
                        "Invalid Selection",
                        "Selected folder is not a Geodatabase (.gdb). Please select a folder ending with .gdb"
                    )
        
        return "", ""
    
    @staticmethod
    def get_save_file_name(
        parent: Optional[QWidget] = None,
        caption: str = "",
        directory: str = "",
        filter_string: str = "",
        initial_filter: str = ""
    ) -> Tuple[str, str]:
        """
        Enhanced version of QFileDialog.getSaveFileName.
        Uses standard implementation since .gdb creation is uncommon in save dialogs.
        """
        return QFileDialog.getSaveFileName(
            parent, caption, directory, filter_string, initial_filter
        )
    
    @staticmethod
    def get_existing_directory(
        parent: Optional[QWidget] = None,
        caption: str = "",
        directory: str = ""
    ) -> str:
        """
        Standard directory selection dialog.
        """
        return QFileDialog.getExistingDirectory(parent, caption, directory)


def create_geo_file_filter() -> str:
    """
    Creates a comprehensive file filter string for geospatial files.
    Includes all common GIS formats with geodatabase support.
    
    Returns:
        Filter string suitable for QFileDialog
    """
    return (
        "All Geo Files (*.gpkg *.shp *.gdb *.geojson *.kml *.gml);;"
        "GeoPackage (*.gpkg);;"
        "Shapefile (*.shp);;"
        "Geodatabase (*.gdb);;"
        "GeoJSON (*.geojson);;"
        "KML (*.kml);;"
        "GML (*.gml);;"
        "All Files (*)"
    )


def create_vector_file_filter() -> str:
    """
    Creates a file filter string specifically for vector data files.
    
    Returns:
        Filter string for vector formats
    """
    return (
        "Vector Files (*.gpkg *.shp *.gdb *.geojson);;"
        "GeoPackage (*.gpkg);;"
        "Shapefile (*.shp);;"
        "Geodatabase (*.gdb);;"
        "GeoJSON (*.geojson);;"
        "All Files (*)"
    )


def create_csv_file_filter() -> str:
    """
    Creates a file filter string for CSV files.
    
    Returns:
        Filter string for CSV files
    """
    return "CSV Files (*.csv);;All Files (*)"


def get_initial_directory_from_path(path: str) -> str:
    """
    Determines the initial directory for a file dialog based on a given path.

    - If the path is a valid file or directory, its containing folder is returned.
    - Otherwise, the user's home directory is used as a default.
    """
    current_path = path.strip()
    if current_path and os.path.exists(current_path):
        if os.path.isdir(current_path):
            return current_path
        else:
            return os.path.dirname(current_path)
    return os.path.expanduser("~") 