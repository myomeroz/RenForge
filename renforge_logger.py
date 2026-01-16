# -*- coding: utf-8 -*-
"""
RenForge Merkezi Logging Modülü

Tüm uygulama için standart logging yapılandırması sağlar.
Log dosyaları ~/.renforge/logs/ dizininde saklanır.

FIX: Handlers are only configured on the root 'renforge' logger.
Child loggers propagate to root and do not add handlers themselves.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

# Log dizini
LOG_DIR = Path.home() / ".renforge" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log dosyası adı (tarih ile)
LOG_FILE = LOG_DIR / f"renforge_{datetime.now().strftime('%Y%m%d')}.log"

# Log formatı
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Flag to track if root logger is configured
_root_configured = False
_startup_buffer = []  # List to store startup LogRecords
MAX_STARTUP_BUFFER = 500  # Max records to keep


class StartupBufferHandler(logging.Handler):
    """
    Handler that buffers log records in memory until they can be 
    dumped to the Inspector UI.
    """
    def __init__(self):
        super().__init__()
        self.setLevel(logging.DEBUG)
    
    def emit(self, record):
        global _startup_buffer
        if len(_startup_buffer) >= MAX_STARTUP_BUFFER:
            return
        _startup_buffer.append(record)


def _configure_root_logger():
    """Configure the root 'renforge' logger with handlers (once only)."""
    global _root_configured
    if _root_configured:
        return
    
    root_logger = logging.getLogger("renforge")
    root_logger.setLevel(logging.DEBUG)
    
    # Prevent propagation to Python's root logger to avoid duplicates
    root_logger.propagate = False
    
    # Konsol handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Konsola sadece INFO ve üstü
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # Dosya handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Dosyaya tüm seviyeleri yaz
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # Startup Buffer Handler (YENİ)
    # Stores logs until Inspector is ready
    buffer_handler = StartupBufferHandler()
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(buffer_handler)
    
    _root_configured = True


def flush_startup_buffer(target_handler):
    """
    Flush buffered startup logs to the given target handler.
    Called when InspectorLogHandler is installed.
    """
    global _startup_buffer
    if not _startup_buffer:
        return
    
    # Emit all buffered records to the new handler
    for record in _startup_buffer:
        target_handler.emit(record)
    
    # Clear buffer to free memory (and stop buffering generally? 
    # Actually we might want to remove the handler, but keeping it simple for now)
    _startup_buffer.clear()
    
    # Remove the buffer handler from root logger if possible?
    # For now just clearing the list is enough.



def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Deprecated: Use get_logger() instead.
    This function is kept for backward compatibility.
    """
    return get_logger(name.replace("renforge.", ""))


# Ana uygulama logger'ı - configure root on module load
_configure_root_logger()
logger = logging.getLogger("renforge")


def get_logger(name: str) -> logging.Logger:
    """
    Modül için child logger döndürür.
    
    Child loggers do NOT add handlers - they propagate to the root 'renforge' logger.
    This prevents duplicate log lines.
    
    Args:
        name: Modül adı
    
    Returns:
        renforge.{name} formatında logger
    """
    # Ensure root is configured
    _configure_root_logger()
    
    # Return child logger - it inherits handlers from parent via propagation
    child_logger = logging.getLogger(f"renforge.{name}")
    # propagate=True is the default, child logs bubble up to root
    return child_logger
