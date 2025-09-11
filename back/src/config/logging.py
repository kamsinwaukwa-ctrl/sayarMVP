"""
Logging configuration for Sayar WhatsApp Commerce Platform
Structured JSON logging with correlation IDs and request context
"""

import logging
import os
import json
import queue
from typing import Dict, Any
from logging.handlers import QueueHandler, QueueListener


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        payload = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }
        
        # Merge extra fields from the log record
        for k, v in getattr(record, "__dict__", {}).items():
            if k in payload or k.startswith("_") or k in (
                "args", "msg", "exc_info", "exc_text", "stack_info", 
                "created", "filename", "funcName", "levelno", "lineno",
                "module", "msecs", "name", "pathname", "process", 
                "processName", "relativeCreated", "thread", "threadName"
            ):
                continue
            payload[k] = v
            
        # Add exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
            
        return json.dumps(payload, ensure_ascii=False, default=str)


def build_logger(name: str = "sayar") -> logging.Logger:
    """
    Build configured logger with JSON formatting and queue handling
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    log = logging.getLogger(name)
    
    # Avoid reconfiguring already configured loggers
    if getattr(log, "_configured", False):
        return log

    # Get configuration from environment
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("LOG_FORMAT", "json")
    
    log.setLevel(level)

    # Set up queue-based logging to avoid blocking requests
    log_queue = queue.Queue(-1)
    queue_handler = QueueHandler(log_queue)
    log.addHandler(queue_handler)

    # Set up stream handler with formatter
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    
    if fmt == "json":
        stream_handler.setFormatter(JsonFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    # Start queue listener
    listener = QueueListener(log_queue, stream_handler, respect_handler_level=True)
    listener.daemon = True
    listener.start()

    # Mark logger as configured
    log._configured = True
    return log


# Global logger instance
logger = build_logger("sayar")