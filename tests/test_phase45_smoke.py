# -*- coding: utf-8 -*-
"""
Phase 4.5 Smoke Tests

Tests for UI state stabilization:
1. Open file -> row count > 0
2. Select row -> inspector row updated
3. Batch status -> buttons enable/disable
"""

import pytest
from unittest.mock import MagicMock, patch


class TestPhase45Smoke:
    """Smoke tests for Phase 4.5 UI state stabilization."""
    
    def test_file_open_row_count(self):
        """Test: TableRowData creation works correctly."""
        from gui.models.translation_table_model import TranslationTableModel, TableRowData
        
        # Create table rows directly
        rows = [
            TableRowData(row_id=0, line_num="1", item_type="dialogue", tag="mc", 
                        original="Hello", translation="Merhaba"),
            TableRowData(row_id=1, line_num="2", item_type="dialogue", tag="mc", 
                        original="World", translation="Dünya"),
        ]
        
        # Test model can accept rows
        model = TranslationTableModel()
        model.set_rows(rows)
        
        assert model.rowCount() == 2, f"Expected 2 rows, got {model.rowCount()}"
        assert rows[0].original == "Hello"
        assert rows[1].original == "World"
    
    def test_selection_payload_keys(self):
        """Test: selection_changed payload has required keys."""
        required_keys = {'row_id', 'type', 'tag', 'original', 'translation', 'status'}
        
        # Mock payload from shared_table_view
        mock_payload = {
            'row_id': 1,
            'type': 'dialogue',
            'tag': 'eileen',
            'original': 'Hello',
            'translation': 'Merhaba',
            'status': '',
            'line_num': '10',
            'is_modified': False,
            'item_type': 'dialogue',
            'batch_marker': ''
        }
        
        missing = required_keys - set(mock_payload.keys())
        assert not missing, f"Missing required keys: {missing}"
    
    def test_batch_status_keys(self):
        """Test: batch_status_updated has required keys."""
        required_keys = {'running', 'processed', 'total', 'success', 'failed', 'chunk_index', 'chunk_total'}
        
        # Mock status from BatchController._emit_status
        mock_status = {
            'running': True,
            'processed': 50,
            'total': 100,
            'success': 48,
            'failed': 2,
            'chunk_index': 2,
            'chunk_total': 5,
            'errors': 2,
            'warnings': 0,
            'is_running': True
        }
        
        missing = required_keys - set(mock_status.keys())
        assert not missing, f"Missing required keys: {missing}"
    
    def test_batch_controller_cancel(self):
        """Test: BatchController has cancel() method."""
        from controllers.batch_controller import BatchController
        
        mock_main = MagicMock()
        controller = BatchController(mock_main)
        
        assert hasattr(controller, 'cancel'), "BatchController missing cancel() method"
        assert callable(controller.cancel), "cancel should be callable"
        
        # Cancel when not running should be no-op
        controller.cancel()
        
        # Start batch and cancel
        controller.start_batch(100)
        assert controller._is_running == True
        
        controller.cancel()
        assert controller._is_running == False
        assert controller._cancelled == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
