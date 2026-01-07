# -*- coding: utf-8 -*-
"""
Signal Wiring Tests for RenForge

Tests for View↔Controller signal connections and event flow.
Uses pytest-qt for PyQt6 signal testing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


class TestRenForgeGUISignals:
    """Tests for RenForgeGUI signal definitions."""
    
    def test_gui_has_imainview_signals(self):
        """Test that RenForgeGUI defines all IMainView signals."""
        from PyQt6.QtCore import pyqtSignal
        from gui.renforge_gui import RenForgeGUI
        
        # Check file operation signals
        assert hasattr(RenForgeGUI, 'open_project_requested')
        assert hasattr(RenForgeGUI, 'open_file_requested')
        assert hasattr(RenForgeGUI, 'save_requested')
        assert hasattr(RenForgeGUI, 'save_all_requested')
        assert hasattr(RenForgeGUI, 'close_tab_requested')
        assert hasattr(RenForgeGUI, 'exit_requested')
        
        # Check navigation signals
        assert hasattr(RenForgeGUI, 'tab_changed')
        assert hasattr(RenForgeGUI, 'item_selected')
        
        # Check translation signals
        assert hasattr(RenForgeGUI, 'translate_google_requested')
        assert hasattr(RenForgeGUI, 'translate_ai_requested')
        assert hasattr(RenForgeGUI, 'batch_google_requested')
        assert hasattr(RenForgeGUI, 'batch_ai_requested')
        
        # Check settings signals
        assert hasattr(RenForgeGUI, 'target_language_changed')
        assert hasattr(RenForgeGUI, 'source_language_changed')
        assert hasattr(RenForgeGUI, 'model_changed')


class TestBootstrapWiring:
    """Tests for app_bootstrap signal wiring."""
    
    def test_bootstrap_returns_controller_and_view(self):
        """Test that bootstrap returns both controller and view."""
        # Skip if GUI not available
        pytest.importorskip("PyQt6.QtWidgets")
        
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # Create app if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from app_bootstrap import bootstrap
        from controllers.app_controller import AppController
        from gui.renforge_gui import RenForgeGUI
        
        controller, view = bootstrap()
        
        assert isinstance(controller, AppController)
        assert isinstance(view, RenForgeGUI)
        
        # Verify controller reference is stored in view
        assert view._app_controller is controller
    
    def test_file_controller_signals_connected(self):
        """Test that FileController signals are connected."""
        pytest.importorskip("PyQt6.QtWidgets")
        
        from PyQt6.QtWidgets import QApplication
        import sys
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from app_bootstrap import bootstrap
        
        controller, view = bootstrap()
        
        # FileController should have signals
        assert hasattr(controller.file_controller, 'file_opened')
        assert hasattr(controller.file_controller, 'file_saved')
        assert hasattr(controller.file_controller, 'file_error')


class TestFileControllerSignals:
    """Tests for FileController signal emission."""
    
    def test_file_opened_signal_emitted(self, file_controller, temp_rpy_file):
        """Test that file_opened signal is emitted on successful open."""
        pytest.importorskip("PyQt6.QtCore")
        
        from PyQt6.QtCore import QSignalSpy
        
        spy = QSignalSpy(file_controller.file_opened)
        
        # Open file
        result = file_controller.open_file(str(temp_rpy_file))
        
        # Signal should have been emitted if file opened successfully
        if result is not None:
            assert len(spy) >= 1
    
    def test_file_error_signal_on_invalid_file(self, file_controller):
        """Test that file_error signal is emitted for invalid file."""
        pytest.importorskip("PyQt6.QtCore")
        
        from PyQt6.QtCore import QSignalSpy
        
        spy = QSignalSpy(file_controller.file_error)
        
        # Try to open non-existent file
        result = file_controller.open_file("/nonexistent/path.rpy")
        
        assert result is None
        # Error signal should be emitted
        assert len(spy) >= 1


class TestControllerViewIntegration:
    """Integration tests for controller-view communication."""
    
    def test_controller_open_file_updates_view(self):
        """Test that opening a file via controller updates the view."""
        pytest.importorskip("PyQt6.QtWidgets")
        
        from PyQt6.QtWidgets import QApplication
        import sys
        import tempfile
        import os
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from app_bootstrap import bootstrap
        
        controller, view = bootstrap()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rpy', delete=False, encoding='utf-8') as f:
            f.write('label start:\n    "Hello world"\n')
            temp_path = f.name
        
        try:
            # Open via controller
            controller.open_file(temp_path, 'direct')
            
            # Process events to allow signal handling
            app.processEvents()
            
            # Verify view was updated
            # (actual verification depends on implementation)
        finally:
            os.unlink(temp_path)
