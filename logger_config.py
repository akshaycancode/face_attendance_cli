"""
logger_config.py
================
Sets up Python logging for the application.
- File handler  → logs/app.log  (DEBUG level, rotates implicitly by size)
- Console handler → stdout       (INFO level, clean for CLI users)
Auto-creates the logs directory if it doesn't exist.
"""

import os
import logging
from config import LOGS_DIR


def setup_logger(name: str = "attendance_system") -> logging.Logger:
    """
    Create and return a configured logger instance.

    Parameters
    ----------
    name : str
        Logger name (default "attendance_system").

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if called more than once
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # --- Ensure log directory exists ---
    os.makedirs(LOGS_DIR, exist_ok=True)

    # --- File handler (detailed) ---
    log_file = os.path.join(LOGS_DIR, "app.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # --- Console handler (clean) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Module-level convenience logger
logger = setup_logger()
