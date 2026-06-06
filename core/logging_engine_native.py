#!/usr/bin/env python3
"""
Structured Logging Engine for MAGNATRIX-OS
Log levels, rotation, JSON structured logs, correlation IDs.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class StructuredLogFormatter(logging.Formatter):
    """JSON structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'source': f"{record.filename}:{record.lineno}",
            'function': record.funcName,
        }

        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
        if hasattr(record, 'extra'):
            log_entry['extra'] = record.extra
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class LogEngine:
    """Structured logging engine with rotation and correlation IDs."""

    LEVELS = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'CRITICAL': 50}

    def __init__(self, name: str = 'magnatrix', log_dir: str = './logs') -> None:
        self._name = name
        self._log_dir = log_dir
        self._correlation_id = threading.local()
        self._handlers: List[logging.Handler] = []

        os.makedirs(log_dir, exist_ok=True)

        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers = []

        console = logging.StreamHandler()
        console.setFormatter(StructuredLogFormatter())
        self._logger.addHandler(console)
        self._handlers.append(console)

        log_file = os.path.join(log_dir, f'{name}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredLogFormatter())
        self._logger.addHandler(file_handler)
        self._handlers.append(file_handler)

    def set_correlation_id(self, cid: str) -> None:
        self._correlation_id.value = cid

    def _log(self, level: str, message: str, extra: Optional[Dict] = None) -> None:
        cid = getattr(self._correlation_id, 'value', None)
        extra_dict = {'correlation_id': cid or 'none'}
        if extra:
            extra_dict['extra'] = extra

        self._logger.log(self.LEVELS[level], message, extra=extra_dict)

    def debug(self, message: str, extra: Optional[Dict] = None) -> None:
        self._log('DEBUG', message, extra)

    def info(self, message: str, extra: Optional[Dict] = None) -> None:
        self._log('INFO', message, extra)

    def warning(self, message: str, extra: Optional[Dict] = None) -> None:
        self._log('WARNING', message, extra)

    def error(self, message: str, extra: Optional[Dict] = None, exc_info: bool = False) -> None:
        self._log('ERROR', message, extra)

    def critical(self, message: str, extra: Optional[Dict] = None) -> None:
        self._log('CRITICAL', message, extra)

    def rotate(self, max_size_mb: int = 10, max_files: int = 5) -> None:
        log_file = os.path.join(self._log_dir, f'{self._name}.log')
        if os.path.exists(log_file):
            size_mb = os.path.getsize(log_file) / (1024 * 1024)
            if size_mb >= max_size_mb:
                for i in range(max_files - 1, 0, -1):
                    old = f'{log_file}.{i}'
                    new = f'{log_file}.{i + 1}'
                    if os.path.exists(old):
                        os.rename(old, new)
                os.rename(log_file, f'{log_file}.1')
                for h in self._handlers:
                    if isinstance(h, logging.FileHandler):
                        h.close()
                        self._logger.removeHandler(h)
                new_handler = logging.FileHandler(log_file)
                new_handler.setFormatter(StructuredLogFormatter())
                self._logger.addHandler(new_handler)
                self._handlers.append(new_handler)


def _demo() -> None:
    print("=== Structured Logging Engine Demo ===\n")
    log = LogEngine('magnatrix_test', '/tmp/magnatrix_logs')
    log.set_correlation_id('req-12345')
    log.info('System started', {'version': '1.0', 'node': 'alpha'})
    log.debug('Loading config', {'path': '/etc/magnatrix.json'})
    log.warning('High memory usage', {'usage': '85%'})
    log.error('Database connection failed', {'host': 'localhost', 'retry': 3})
    print("\nCheck /tmp/magnatrix_logs/magnatrix_test.log for JSON output")
    print("=== Logging Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()
