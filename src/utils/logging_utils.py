"""
Logging utilities for the Parcel Generator project.

Utilidades para configurar el sistema de logging.
"""

import json
import logging
import os
import sys
from multiprocessing import Queue, current_process
from typing import Optional

# Elimina basicConfig y debug fuera de setup_logging
# Solo setup_logging debe configurar el logging
# Si quieres debug temprano, usa print (opcional)

class JsonStdoutHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = {
                "type": "log",
                "level": record.levelname.lower(),
                "message": self.format(record),
                "logger": record.name
            }
            print(json.dumps(log_entry), flush=True)
        except Exception:
            self.handleError(record)

_queue_listener = None
_queue = None

def setup_logging(log_file: str, level: int = logging.INFO, use_queue: bool = True) -> None:
    """
    Configures the logging system to write to a file, console, and JSON to stdout.
    If use_queue is True, sets up a QueueHandler/QueueListener for multiprocessing.
    Args:
        log_file: Path to the log file
        level: Logging level (default INFO)
        use_queue: Whether to use QueueHandler for multiprocessing
    """
    global _queue_listener, _queue
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    # Lee el nivel de log desde la variable de entorno LOG_LEVEL si está presente
    log_level_env = os.environ.get("LOG_LEVEL", None)
    if log_level_env:
        import logging
        level = getattr(logging, log_level_env.upper(), logging.INFO)
    # Remove all handlers first
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
        JsonStdoutHandler()
    ]
    if use_queue:
        from logging.handlers import QueueHandler, QueueListener
        if _queue is None:
            _queue = Queue(-1)
        queue_handler = QueueHandler(_queue)
        logging.root.addHandler(queue_handler)
        _queue_listener = QueueListener(_queue, *handlers, respect_handler_level=True)
        _queue_listener.start()
    else:
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
    logging.getLogger().setLevel(level)
    logging.info(f"Logging configured. Log file: {log_file}")

def setup_worker_logging(level: int = logging.INFO):
    """
    Configures logging in a multiprocessing worker to send logs to the main process via QueueHandler.
    """
    global _queue
    from logging.handlers import QueueHandler
    if _queue is not None:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        queue_handler = QueueHandler(_queue)
        logging.root.addHandler(queue_handler)
        logging.getLogger().setLevel(level)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Gets a logger with the specified name.
    
    Args:
        name: Logger name (optional)
        
    Returns:
        Configured logger object
    """
    return logging.getLogger(name) 