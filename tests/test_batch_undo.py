# -*- coding: utf-8 -*-
"""
Unit tests for BatchUndoManager.
"""

import pytest
from dataclasses import dataclass
from typing import Optional


# Mock ParsedItem for testing
@dataclass
class MockParsedItem:
    current_text: str
    initial_text: str
    batch_marker: Optional[str] = None
    batch_tooltip: Optional[str] = None
    is_modified_session: bool = False


class TestBatchUndoManager:
    """Tests for BatchUndoManager functionality."""
    
    def test_capture_creates_snapshot(self):
        """Test that capture creates a valid snapshot."""
        from models.batch_undo import BatchUndoManager, RowState
        
        mgr = BatchUndoManager()
        items = [
            MockParsedItem(current_text="Text 1", initial_text="Original 1"),
            MockParsedItem(current_text="Text 2", initial_text="Original 2"),
            MockParsedItem(current_text="Text 3", initial_text="Original 3"),
        ]
        
        snapshot = mgr.capture("test.rpy", [0, 2], items, "ai")
        
        assert snapshot is not None
        assert snapshot.file_path == "test.rpy"
        assert snapshot.batch_type == "ai"
        assert snapshot.row_count() == 2
        assert 0 in snapshot.affected_rows
        assert 2 in snapshot.affected_rows
        assert 1 not in snapshot.affected_rows
    
    def test_has_undo_returns_correct_state(self):
        """Test has_undo returns True after capture, False after restore."""
        from models.batch_undo import BatchUndoManager
        
        mgr = BatchUndoManager()
        items = [MockParsedItem(current_text="Text", initial_text="Original")]
        
        assert mgr.has_undo("test.rpy") is False
        
        mgr.capture("test.rpy", [0], items, "ai")
        assert mgr.has_undo("test.rpy") is True
        
        mgr.restore("test.rpy", items)
        assert mgr.has_undo("test.rpy") is False
    
    def test_restore_reverts_text(self):
        """Test that restore correctly reverts text and markers."""
        from models.batch_undo import BatchUndoManager
        
        mgr = BatchUndoManager()
        items = [
            MockParsedItem(current_text="Before", initial_text="Initial"),
        ]
        
        # Capture before batch
        mgr.capture("test.rpy", [0], items, "ai")
        
        # Simulate batch changing the item
        items[0].current_text = "After batch"
        items[0].batch_marker = "OK"
        items[0].batch_tooltip = "Translated"
        
        # Restore
        result = mgr.restore("test.rpy", items)
        
        assert result is True
        assert items[0].current_text == "Before"
        assert items[0].batch_marker is None
        assert items[0].batch_tooltip is None
    
    def test_restore_returns_false_for_missing_snapshot(self):
        """Test restore returns False when no snapshot exists."""
        from models.batch_undo import BatchUndoManager
        
        mgr = BatchUndoManager()
        items = [MockParsedItem(current_text="Text", initial_text="Original")]
        
        result = mgr.restore("nonexistent.rpy", items)
        assert result is False
    
    def test_new_capture_replaces_old_snapshot(self):
        """Test that capturing again replaces the previous snapshot (depth=1)."""
        from models.batch_undo import BatchUndoManager
        
        mgr = BatchUndoManager()
        items = [
            MockParsedItem(current_text="First", initial_text="Initial"),
        ]
        
        mgr.capture("test.rpy", [0], items, "ai")
        
        # Change and capture again
        items[0].current_text = "Second"
        mgr.capture("test.rpy", [0], items, "ai")
        
        # After restore, should get "Second" not "First"
        items[0].current_text = "Third"
        mgr.restore("test.rpy", items)
        
        assert items[0].current_text == "Second"


class TestBatchSummaryFormat:
    """Tests for batch summary dict structure."""
    
    def test_summary_dict_required_keys(self):
        """Test that summary formatting handles all required keys."""
        from gui.views.batch_status_view import format_batch_summary, get_status_message
        
        # Minimal dict
        results = {
            "total": 100,
            "success": 95,
            "failed": 5,
            "canceled": False
        }
        
        summary = format_batch_summary(results)
        status = get_status_message(results)
        
        assert "100" in summary
        assert "95" in summary
        assert isinstance(status, str)
    
    def test_canceled_summary(self):
        """Test summary correctly shows CANCELED state."""
        from gui.views.batch_status_view import format_batch_summary, get_status_message
        
        results = {
            "total": 100,
            "success": 50,
            "canceled": True
        }
        
        summary = format_batch_summary(results)
        status = get_status_message(results)
        
        assert "CANCELED" in summary
        assert "canceled" in status.lower()
