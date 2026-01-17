# -*- coding: utf-8 -*-
"""
RenForge Inspector Log Handler

Thread-safe logging bridge that connects Python logging to Inspector Log tab.
Uses Qt signal/slot mechanism for safe cross-thread communication.
"""

import logging
import os
from collections import OrderedDict
from PySide6.QtCore import QObject, Signal


class LogEmitter(QObject):
    """
    Qt signal emitter for thread-safe log message delivery.
    
    This QObject lives on the main UI thread. Log messages from any thread
    are emitted as signals, which Qt automatically queues to the UI thread.
    """
    message = Signal(str)


class DeduplicationFilter(logging.Filter):
    """
    Filter that prevents duplicate log records from being emitted.
    
    Uses an LRU cache to track recently seen records.
    Duplicates are identified by (timestamp, name, level, message) tuple.
    """
    
    def __init__(self, max_cache_size: int = 100):
        super().__init__()
        self._seen = OrderedDict()
        self._max_size = max_cache_size
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False if this record was recently seen (duplicate)."""
        # Create a unique key for this record
        key = (
            round(record.created, 2),  # Round to 10ms to catch near-duplicates
            record.name,
            record.levelno,
            record.getMessage()
        )
        
        if key in self._seen:
            return False  # Duplicate, filter it out
        
        # Add to cache
        self._seen[key] = True
        
        # Trim cache if too large (LRU eviction)
        while len(self._seen) > self._max_size:
            self._seen.popitem(last=False)
        
        return True  # Not a duplicate


class InspectorLogHandler(logging.Handler):
    """
    Custom logging handler that emits log records to a Qt signal.
    
    Thread-safe: The signal emission uses Qt's queued connection mechanism,
    so log messages from worker threads are safely delivered to the UI thread.
    """
    
    def __init__(self, emitter: LogEmitter):
        """
        Initialize the handler with a LogEmitter.
        
        Args:
            emitter: LogEmitter instance whose signal will deliver messages
        """
        super().__init__()
        self.emitter = emitter
        self._in_emit = False  # Recursion guard
        
        # Add deduplication filter
        self.addFilter(DeduplicationFilter())
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record by sending it to the Qt signal.
        
        Args:
            record: The log record to emit
        """
        # Prevent infinite recursion (if logging happens inside this method)
        if self._in_emit:
            return
        
        try:
            self._in_emit = True
            msg = self.format(record)
            self.emitter.message.emit(msg)
        except Exception:
            # Never crash the application from a logging handler
            self.handleError(record)
        finally:
            self._in_emit = False


def install_inspector_log_handler(inspector_panel, base_logger_name: str = "renforge"):
    """
    Install the log handler bridge to an InspectorPanel.
    
    Attaches handler to BOTH the base logger AND the ROOT logger to catch all logs.
    Uses deduplication filter to prevent duplicate lines.
    
    Args:
        inspector_panel: InspectorPanel instance with append_log method
        base_logger_name: Base logger to attach handler to (default: "renforge")
        
    Returns:
        Tuple of (emitter, handler) for reference/cleanup, or (None, None) if failed
    """
    if not inspector_panel or not hasattr(inspector_panel, 'append_log'):
        print("[WARNING] inspector_panel missing or has no append_log method")
        return None, None
    
    try:
        # Determine log level from environment
        level_name = os.environ.get('RENFORGE_INSPECTOR_LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, level_name, logging.INFO)
        
        # Create emitter and handler
        emitter = LogEmitter()
        handler = InspectorLogHandler(emitter)
        handler.setLevel(level)
        
        # Set formatter with timestamp
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        # Connect signal to inspector (Qt handles thread safety via queued connection)
        emitter.message.connect(inspector_panel.append_log)
        
        # Check for existing InspectorLogHandler to avoid duplicates
        def has_inspector_handler(logger):
            for h in logger.handlers:
                if isinstance(h, InspectorLogHandler):
                    return True
            return False
        
        # Attach to base logger (renforge)
        base_logger = logging.getLogger(base_logger_name)
        if not has_inspector_handler(base_logger):
            base_logger.addHandler(handler)
        
        # ALSO attach to ROOT logger to catch ALL logs
        root_logger = logging.getLogger()
        if not has_inspector_handler(root_logger):
            root_logger.addHandler(handler)
        
        # Self-test: This log line MUST appear in Inspector Log tab
        logging.getLogger("renforge.inspector").info("[INSPECTOR] log hook active")
        
        # Flush startup buffer if available
        try:
            import renforge_logger
            if hasattr(renforge_logger, 'flush_startup_buffer'):
                renforge_logger.flush_startup_buffer(handler)
        except ImportError:
            pass
        except Exception as e:
            print(f"[WARNING] Failed to flush startup logs: {e}")
        
        return emitter, handler
        
    except Exception as e:
        # Never crash on logging setup failure
        print(f"[WARNING] Failed to install inspector log handler: {e}")
        import traceback
        traceback.print_exc()
        return None, None
