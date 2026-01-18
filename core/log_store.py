# -*- coding: utf-8 -*-
"""
RenForge Log Store
Provides a thread-safe ring buffer for capturing recent log entries
for the Debug Bundle functionality.
"""

import threading
import logging
from typing import List, Optional

from renforge_logger import get_logger

logger = get_logger("core.log_store")

class LogRingBuffer:
    """
    Thread-safe ring buffer to store the last N log records.
    """
    
    def __init__(self, capacity: int = 200):
        self._capacity = capacity
        self._buffer: List[logging.LogRecord] = []
        self._lock = threading.RLock()
    
    def append(self, record: logging.LogRecord):
        """
        Add a log record to the buffer.
        If buffer is full, removes the oldest record.
        """
        with self._lock:
            # Enforce capacity
            if len(self._buffer) >= self._capacity:
                self._buffer.pop(0)  # Remove oldest
            
            self._buffer.append(record)
    
    def get_logs(self, limit: Optional[int] = None) -> List[str]:
        """
        Get formatted log lines from the buffer.
        
        Args:
            limit: Optional limit on number of lines to return (from end)
            
        Returns:
            List of formatted log strings
        """
        with self._lock:
            records = self._buffer
            if limit and limit < len(records):
                records = records[-limit:]
            
            # Simple formatting: timestamp | level | logger | message
            formatted_logs = []
            for record in records:
                try:
                    # Format timestamp
                    ct = record.created
                    # Convert to local time string if possible, or just use generic format
                    # Using a simplified format for debug bundle
                    import time
                    t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ct))
                    
                    line = f"{t_str} | {record.levelname:<8} | {record.name:<20} | {record.getMessage()}"
                    formatted_logs.append(line)
                except Exception:
                    # Fallback in case of formatting error
                    formatted_logs.append(f"Error formatting log record: {record}")
            
            return formatted_logs
    
    def clear(self):
        """Clear the buffer."""
        with self._lock:
            self._buffer.clear()

# Global instance
_instance = None
_instance_lock = threading.Lock()

def instance() -> LogRingBuffer:
    """Get the global LogRingBuffer instance."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = LogRingBuffer()
    return _instance
