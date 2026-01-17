# -*- coding: utf-8 -*-
"""
Smoke Tests for RenForge Fluent UI

Verifies that the new Fluent UI components initialize correctly.
"""

import pytest


class TestFluentUIImports:
    """Test that all Fluent UI components can be imported."""
    
    def test_main_fluent_window_import(self):
        """Test MainFluentWindow can be imported."""
        from gui.windows.main_fluent_window import MainFluentWindow
        assert MainFluentWindow is not None
    
    def test_inspector_panel_import(self):
        """Test InspectorPanel can be imported."""
        from gui.panels.inspector_panel import InspectorPanel
        assert InspectorPanel is not None
    
    def test_translation_table_widget_import(self):
        """Test TranslationTableWidget can be imported."""
        from gui.widgets.shared_table_view import TranslationTableWidget
        assert TranslationTableWidget is not None
    
    def test_all_pages_import(self):
        """Test all pages can be imported."""
        from gui.pages import (
            FilesPage, TranslatePage, ReviewPage,
            TMPage, GlossaryPage, PackagingPage, SettingsPage
        )
        assert FilesPage is not None
        assert TranslatePage is not None
        assert ReviewPage is not None
        assert TMPage is not None
        assert GlossaryPage is not None
        assert PackagingPage is not None
        assert SettingsPage is not None


class TestFluentUIInstantiation:
    """Test that Fluent UI components can be instantiated."""
    
    def test_inspector_panel_creation(self, qtbot):
        """Test InspectorPanel can be created."""
        from gui.panels.inspector_panel import InspectorPanel
        
        panel = InspectorPanel()
        qtbot.addWidget(panel)
        
        assert panel is not None
        assert hasattr(panel, 'show_row')
        assert hasattr(panel, 'show_batch_status')
        assert hasattr(panel, 'append_log')
    
    def test_inspector_panel_api(self, qtbot):
        """Test InspectorPanel API methods work."""
        from gui.panels.inspector_panel import InspectorPanel
        
        panel = InspectorPanel()
        qtbot.addWidget(panel)
        
        # Test show_row
        panel.show_row({
            'row_id': 1,
            'line_num': '10',
            'item_type': 'dialogue',
            'tag': 'mc',
            'original': 'Hello World',
            'translation': 'Merhaba Dünya',
            'is_modified': True,
            'batch_marker': ''
        })
        assert panel.row_number_label.text() == "Satır: 10"
        
        # Test show_batch_status
        panel.show_batch_status({
            'processed': 5,
            'total': 10,
            'success': 4,
            'errors': 1,
            'warnings': 0,
            'is_running': True
        })
        assert panel.progress_label.text() == "5 / 10"
        
        # Test append_log
        panel.append_log("Test log message")
        assert "Test log message" in panel.log_text.toPlainText()
    
    def test_main_fluent_window_creation(self, qtbot):
        """Test MainFluentWindow can be created with all pages."""
        from gui.windows.main_fluent_window import MainFluentWindow
        
        window = MainFluentWindow()
        qtbot.addWidget(window)
        
        # Verify window created
        assert window is not None
        assert window.windowTitle() == "RenForge"
        
        # Verify pages exist
        assert hasattr(window, 'files_page')
        assert hasattr(window, 'translate_page')
        assert hasattr(window, 'review_page')
        assert hasattr(window, 'settings_page')
        
        # Verify inspector exists
        assert hasattr(window, 'inspector')
        
        # Verify compatibility attributes
        assert hasattr(window, 'file_data')
        assert hasattr(window, 'tab_data')
        assert hasattr(window, 'open_file_requested')
        
        window.close()


class TestFluentUITheme:
    """Test theme switching functionality."""
    
    def test_theme_toggle(self, qtbot):
        """Test theme can be toggled."""
        from gui.windows.main_fluent_window import MainFluentWindow
        from qfluentwidgets import isDarkTheme
        
        window = MainFluentWindow()
        qtbot.addWidget(window)
        
        # Initial state
        initial_dark = isDarkTheme()
        
        # Toggle
        window.toggle_theme()
        assert isDarkTheme() != initial_dark
        
        # Toggle back
        window.toggle_theme()
        assert isDarkTheme() == initial_dark
        
        window.close()
