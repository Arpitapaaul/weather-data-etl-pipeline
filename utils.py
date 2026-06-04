"""
src/utils.py
------------
Shared utility functions used across the entire pipeline.

Contains:
    - get_logger()          : Returns a configured logger for any module
    - get_timestamp()       : Returns a clean timestamp string
    - save_json()           : Saves a Python dict as a JSON file
    - load_json()           : Loads a JSON file into a Python dict
    - timing_decorator()    : Decorator to measure function execution time

Senior Engineer Note:
    Centralising utilities avoids code duplication (DRY principle — Don't
    Repeat Yourself). Every module imports from here, so changing log format
    once here changes it everywhere.
"""

import json
import logging
import time
import functools
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Import project config — available because main.py runs from project root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a logger with both file and console handlers.

    Args:
        name: Usually __name__ from the calling module.

    Returns:
        Configured logging.Logger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("Pipeline started")
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.DEBUG))

    formatter = logging.Formatter(
        fmt=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT,
    )

    # ── File Handler: Rotating log file (max 5 MB, keeps 3 backups) ──
    file_handler = RotatingFileHandler(
        filename=config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # ── Console Handler: Shows INFO+ messages in terminal ──
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """
    Return the current datetime as a formatted string.

    Args:
        fmt: strftime format string. Default is suitable for filenames.

    Returns:
        Formatted timestamp string, e.g. "20240915_143022"
    """
    return datetime.now().strftime(fmt)


def save_json(data: dict | list, filepath: Path | str) -> None:
    """
    Save a Python object as a pretty-printed JSON file.

    Args:
        data:     Dictionary or list to serialise.
        filepath: Destination file path.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)


def load_json(filepath: Path | str) -> dict | list:
    """
    Load a JSON file and return the parsed Python object.

    Args:
        filepath: Path to the JSON file.

    Returns:
        Parsed Python dict or list.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def timing_decorator(func):
    """
    Decorator that logs how long a function takes to execute.

    Usage:
        @timing_decorator
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"[TIMER] {func.__name__} completed in {elapsed:.2f}s")
        return result
    return wrapper


def print_section(title: str, width: int = 60) -> None:
    """
    Print a visually clear section header in the terminal.

    Args:
        title: Section title to display.
        width: Total width of the separator line.
    """
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)
