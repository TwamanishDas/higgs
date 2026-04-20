import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "companion.log")

log: logging.Logger = logging.getLogger("companion")


def setup(level: str = "INFO"):
    os.makedirs(_LOG_DIR, exist_ok=True)

    log.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter(
        fmt="%(asctime)s  [%(levelname)-8s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file: max 2 MB, keep 3 backups
    fh = RotatingFileHandler(_LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(fh)

    # Also print to console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    log.addHandler(ch)

    log.info("=" * 60)
    log.info("Desktop Companion starting up")
    log.info(f"Log file: {_LOG_FILE}")
