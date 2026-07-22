"""
Structured (JSON) logging setup.

Plain print()/text logs are fine on a laptop; they fall apart the moment
you ship to something like Datadog/Splunk/ELK, which want one JSON object
per line so they can index fields (path, status, duration_ms, etc.)
without regex-parsing free text.
"""
import logging
import json
import sys
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Anything passed via logger.info(msg, extra={...}) gets merged in.
        for key, value in record.__dict__.items():
            if key in ("args", "msg", "levelname", "levelno", "name", "pathname",
                        "filename", "module", "exc_info", "exc_text", "stack_info",
                        "lineno", "funcName", "created", "msecs", "relativeCreated",
                        "thread", "threadName", "processName", "process"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("cst")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logging()
