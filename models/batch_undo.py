# -*- coding: utf-8 -*-
"""
RenForge Batch Undo Manager

Provides snapshot capture and restore functionality for Undo Last Batch.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime

from renforge_logger import get_logger
logger = get_logger("models.batch_undo")


@dataclass
class RowState:
    """State of a single row before batch operation."""
    text: str
    marker: Optional[str] = None
    tooltip: Optional[str] = None


@dataclass
class UndoSnapshot:
    """Snapshot of affected rows before a batch operation."""
    file_path: str
    affected_rows: Dict[int, RowState] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    batch_type: str = "ai"  # "ai" or "google"
    
    def row_count(self) -> int:
        return len(self.affected_rows)


class BatchUndoManager:
    """
    Manages undo snapshots for batch operations.
    
    Stores one snapshot per file (stack depth = 1).
    When a new batch runs, it replaces the previous snapshot.
    """
    
    def __init__(self):
        # {file_path: UndoSnapshot}
        self._snapshots: Dict[str, UndoSnapshot] = {}
    
    def capture(self, file_path: str, row_indices: list, items: list, 
                batch_type: str = "ai") -> UndoSnapshot:
        """
        Capture undo snapshot before batch starts.
        
        Args:
            file_path: Path of the file being processed
            row_indices: List of row indices that will be affected
            items: List of ParsedItem objects (full file items)
            batch_type: "ai" or "google"
            
        Returns:
            The created UndoSnapshot
        """
        affected_rows = {}
        
        for idx in row_indices:
            if 0 <= idx < len(items):
                item = items[idx]
                affected_rows[idx] = RowState(
                    text=item.current_text or "",
                    marker=getattr(item, 'batch_marker', None),
                    tooltip=getattr(item, 'batch_tooltip', None)
                )
        
        snapshot = UndoSnapshot(
            file_path=file_path,
            affected_rows=affected_rows,
            batch_type=batch_type
        )
        
        # Replace previous snapshot (depth = 1)
        self._snapshots[file_path] = snapshot
        logger.debug(f"[BatchUndoManager] Captured snapshot for {file_path}: {len(affected_rows)} rows")
        
        return snapshot
    
    def has_undo(self, file_path: str) -> bool:
        """Check if undo is available for a file."""
        return file_path in self._snapshots
    
    def get_snapshot(self, file_path: str) -> Optional[UndoSnapshot]:
        """Get the undo snapshot for a file without removing it."""
        return self._snapshots.get(file_path)
    
    def restore(self, file_path: str, items: list) -> bool:
        """
        Restore items to their pre-batch state.
        
        Args:
            file_path: Path of the file
            items: List of ParsedItem objects to restore
            
        Returns:
            True if restore was successful, False if no snapshot exists
        """
        snapshot = self._snapshots.get(file_path)
        if not snapshot:
            logger.warning(f"[BatchUndoManager] No snapshot found for {file_path}")
            return False
        
        restored_count = 0
        for row_idx, row_state in snapshot.affected_rows.items():
            if 0 <= row_idx < len(items):
                item = items[row_idx]
                item.current_text = row_state.text
                item.batch_marker = row_state.marker
                item.batch_tooltip = row_state.tooltip
                # Mark as modified if text changed from initial
                item.is_modified_session = (item.current_text != item.initial_text)
                restored_count += 1
        
        logger.info(f"[BatchUndoManager] Restored {restored_count} rows for {file_path}")
        
        # Clear the snapshot after restore
        del self._snapshots[file_path]
        
        return True
    
    def clear(self, file_path: str = None):
        """
        Clear snapshots.
        
        Args:
            file_path: If provided, clear only that file. Otherwise clear all.
        """
        if file_path:
            self._snapshots.pop(file_path, None)
        else:
            self._snapshots.clear()


# Global instance
_undo_manager: Optional[BatchUndoManager] = None


def get_undo_manager() -> BatchUndoManager:
    """Get the singleton BatchUndoManager instance."""
    global _undo_manager
    if _undo_manager is None:
        _undo_manager = BatchUndoManager()
    return _undo_manager
