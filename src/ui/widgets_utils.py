"""
Shared utility functions for UI widgets to avoid code duplication.
"""

from typing import Any, Dict, List, Optional

from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QLineEdit


def create_spinbox(min_val: int, max_val: int, default: int) -> QSpinBox:
    """
    Creates a configured QSpinBox with given parameters.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        default: Default value
        
    Returns:
        Configured QSpinBox
    """
    spinbox = QSpinBox()
    spinbox.setRange(min_val, max_val)
    spinbox.setValue(default)
    return spinbox


def create_double_spinbox(min_val: float, max_val: float, default: float, step: float = 0.1) -> QDoubleSpinBox:
    """
    Creates a configured QDoubleSpinBox with given parameters.
    
    Args:
        min_val: Minimum value
        max_val: Maximum value
        default: Default value
        step: Step size for increment/decrement
        
    Returns:
        Configured QDoubleSpinBox
    """
    spinbox = QDoubleSpinBox()
    spinbox.setRange(min_val, max_val)
    spinbox.setSingleStep(step)
    spinbox.setValue(default)
    return spinbox


def create_style_combo() -> QComboBox:
    """
    Creates a combo box with standard processing styles.
    
    Returns:
        Configured QComboBox with processing styles
    """
    combo = QComboBox()
    combo.addItems(["calibration", "control", "custom"])
    return combo


def apply_widget_config(widget: Any, config: Dict[str, Any], key: str, default: Any = None) -> None:
    """
    Applies configuration value to a widget if the key exists.
    
    Args:
        widget: Widget to configure
        config: Configuration dictionary
        key: Configuration key
        default: Default value if key not found
    """
    if key not in config and default is None:
        return
        
    value = config.get(key, default)
    
    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        widget.setValue(value)
    elif isinstance(widget, QComboBox):
        if isinstance(value, str):
            index = widget.findText(value)
            if index >= 0:
                widget.setCurrentIndex(index)
    elif isinstance(widget, QCheckBox):
        widget.setChecked(bool(value))
    elif isinstance(widget, QLineEdit):
        widget.setText(str(value) if value is not None else "")


def get_widget_config(widget: Any) -> Any:
    """
    Gets the current value from a widget.
    
    Args:
        widget: Widget to get value from
        
    Returns:
        Current widget value
    """
    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        return widget.value()
    elif isinstance(widget, QComboBox):
        return widget.currentText()
    elif isinstance(widget, QCheckBox):
        return widget.isChecked()
    elif isinstance(widget, QLineEdit):
        text = widget.text().strip()
        return text if text else None
    
    return None


def block_widget_signals(widgets: List[Any], blocked: bool = True) -> None:
    """
    Blocks or unblocks signals for multiple widgets.
    
    Args:
        widgets: List of widgets to modify
        blocked: Whether to block (True) or unblock (False) signals
    """
    for widget in widgets:
        if widget is not None:
            widget.blockSignals(blocked)


def create_default_presets() -> Dict[str, Dict[str, Any]]:
    """
    Creates default preset configurations for different processing types.
    
    Returns:
        Dictionary with default presets
    """
    return {
        "calibration": {
            "base_intensity": 80,
            "use_specific_intensity": True,
            "min_area": 0.4,
            "buffer_distance": -30,
            "min_distance": 80.0,
            "use_gridcode": True
        },
        "control": {
            "base_intensity": 80,
            "use_specific_intensity": False,
            "min_area": 0.4,
            "buffer_distance": -30,
            "min_distance": 80.0,
            "use_gridcode": True,
            "min_parcels": 1,
            "max_parcels": 20
        },
        "custom": {
            "base_intensity": 50,
            "use_specific_intensity": True,
            "min_area": 0.3,
            "buffer_distance": -20,
            "min_distance": 60.0,
            "use_gridcode": False
        }
    } 