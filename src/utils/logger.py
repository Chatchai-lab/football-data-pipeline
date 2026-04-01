"""
Zentrales Logging-Modul für die Matchlytics-Pipeline.
Definiert einheitliche Log-Level und Formatierung für alle Module.

Verwendung:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Pipeline gestartet")
"""

import logging
import os
import sys


def get_logger(name: str = "matchlytics") -> logging.Logger:
    """Erstellt einen konfigurierten Logger.

    Log-Level wird über die Umgebungsvariable LOG_LEVEL gesteuert.
    Default: INFO (in Produktion), DEBUG zum Debuggen.

    Args:
        name: Logger-Name (üblicherweise __name__).

    Returns:
        Konfigurierter Logger.
    """
    logger = logging.getLogger(name)

    # Vermeidet doppelte Handler bei mehrfachem Aufruf
    if logger.handlers:
        return logger

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level, logging.INFO))

    # Console Handler mit einheitlichem Format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level, logging.INFO))
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
