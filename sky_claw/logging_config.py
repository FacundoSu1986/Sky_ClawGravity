import logging
import logging.handlers
import sys
import os
from contextvars import ContextVar
from pythonjsonlogger import json

# Correlation ID for tracking requests across components
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

class CorrelationFilter(logging.Filter):
    """Filter that adds correlation_id from ContextVar to each record."""
    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True

def setup_logging(level: int = logging.INFO, log_file: str = "sky_claw.log"):
    """Set up structured logging with console and JSON file handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Common filter for correlation ID
    corr_filter = CorrelationFilter()

    # Console Handler (Human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(corr_filter)
    root_logger.addHandler(console_handler)

    # File Handler (Structured JSON)
    os.makedirs("logs", exist_ok=True)
    file_path = os.path.join("logs", log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        file_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )
    json_formatter = json.JsonFormatter(
        "%(asctime)s %(levelname)s %(correlation_id)s %(name)s %(message)s"
    )
    file_handler.setFormatter(json_formatter)
    file_handler.addFilter(corr_filter)
    root_logger.addHandler(file_handler)

    logging.info("Logging initialized - Console and JSON File (logs/%s)", log_file)
