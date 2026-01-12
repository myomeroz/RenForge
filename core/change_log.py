
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from renforge_logger import get_logger

logger = get_logger("core.change_log")

class ChangeSource(Enum):
    MANUAL = "manual"
    BATCH = "batch"
    SEARCH_REPLACE = "search_replace"
    QA_FIX = "qa_fix"
    OTHER = "other"

@dataclass
class ChangeRecord:
    timestamp: float
    file_path: str
    item_index: int     # Stable data index
    display_row: int    # 1-based, snapshot at time of change
    before_text: str
    after_text: str
    source: ChangeSource
    batch_id: Optional[str] = None
    
    @property
    def diff_summary(self) -> str:
        # Simple summary for debug/logs
        return f"Row {self.display_row}: '{self.before_text[:20]}...' -> '{self.after_text[:20]}...'"

class ChangeLog:
    """
    Manages a history of changes for the current session/project.
    Designed to be a Singleton or attached to AppController.
    """
    def __init__(self):
        self._records: List[ChangeRecord] = []
        self._listeners = []
        
    def add_record(self, record: ChangeRecord):
        self._records.append(record)
        self._notify_listeners()
        
    def get_records(self, file_path: Optional[str] = None, 
                    source: Optional[ChangeSource] = None, 
                    batch_id: Optional[str] = None) -> List[ChangeRecord]:
        
        filtered = self._records
        if file_path:
            filtered = [r for r in filtered if r.file_path == file_path]
        if source:
            filtered = [r for r in filtered if r.source == source]
        if batch_id:
            filtered = [r for r in filtered if r.batch_id == batch_id]
            
        return filtered
        
    def clear(self):
        self._records.clear()
        self._notify_listeners()

    def remove_record(self, record: ChangeRecord):
        if record in self._records:
            self._records.remove(record)
            self._notify_listeners()

    def add_listener(self, callback):
        self._listeners.append(callback)
        
    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)
            
    def _notify_listeners(self):
        for cb in self._listeners:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in ChangeLog listener: {e}")

# Global instance for now (or managed by Controller)
_instance = None

def get_change_log() -> ChangeLog:
    global _instance
    if _instance is None:
        _instance = ChangeLog()
    return _instance
