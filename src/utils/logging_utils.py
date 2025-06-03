"""
Logging utilities for the Parcel Generator project.

Utilidades para configurar el sistema de logging.
"""

import logging
import os
from typing import Optional


def setup_logging(log_file: str, level: int = logging.INFO) -> None:
    """
    Configures the logging system to write to a file and console.
    
    Args:
        log_file: Path to the log file
        level: Logging level (default INFO)
    """
    # Create directory for the log file if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure the logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info(f"Logging configured. Log file: {log_file}")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Gets a logger with the specified name.
    
    Args:
        name: Logger name (optional)
        
    Returns:
        Configured logger object
    """
    return logging.getLogger(name) 