"""Structured JSON logging for RheaRouter"""

import logging
import sys
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context"""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure structured JSON logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("rhearouter")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplication
    logger.handlers.clear()

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "rhearouter") -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)
