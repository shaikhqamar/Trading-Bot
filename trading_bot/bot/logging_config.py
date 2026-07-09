"""
Centralized logging configuration for the trading bot.

All API requests, responses, and errors are written to a rotating log file
(logs/trading_bot.log) as well as to the console (console gets INFO+ only,
the file gets DEBUG+ so it captures full request/response payloads).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_LOGGER_NAME = "trading_bot"
_configured = False


def get_logger() -> logging.Logger:
    """
    Return the shared trading_bot logger, configuring handlers on first call.
    Safe to call multiple times (idempotent).
    """
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)

    if _configured:
        return logger

    os.makedirs(LOG_DIR, exist_ok=True)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: keeps logs from growing unbounded (5MB x 3 backups)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    # Console handler: keep it clean, INFO and above only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    return logger
