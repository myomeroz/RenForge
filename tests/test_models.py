# -*- coding: utf-8 -*-
"""
Unit Tests for RenForge Models

Tests for ParsedFile, ProjectModel, and SettingsModel.
"""

import pytest
from pathlib import Path


class TestParsedItem:
    """Tests for ParsedItem dataclass."""
    
    def test_get_text(self, parsed_file):
        """Test getting current text."""
        item = parsed_file.get_item(0)
        assert item.get_text() == "Merhaba, dünya!"
    
    def test_set_text_marks_modified(self, parsed_file):
        """Test that setting text marks item as modified."""
        item = parsed_file.get_item(1)
        assert not item.is_modified_session
        
        item.set_text("Nasılsın?")
        
        assert item.is_modified_session
        assert item.current_text == "Nasılsın?"
    
    def test_reset_to_initial(self, parsed_file):
        """Test resetting to initial text."""
        item = parsed_file.get_item(1)
        item.set_text("Modified text")
        
        item.reset_to_initial()
        
        assert item.current_text == item.initial_text
        assert not item.is_modified_session


class TestParsedFile:
    """Tests for ParsedFile model."""
    
    def test_file_properties(self, parsed_file):
        """Test basic file properties."""
        assert parsed_file.filename == "sample.rpy"
        assert parsed_file.item_count == 2
    
    def test_get_item(self, parsed_file):
        """Test getting items by index."""
        item = parsed_file.get_item(0)
        assert item is not None
        assert item.original_text == "Hello, world!"
        
        # Out of bounds
        assert parsed_file.get_item(99) is None
    
    def test_update_item_text(self, parsed_file):
        """Test updating item text."""
        result = parsed_file.update_item_text(0, "New translation")
        
        assert result is True
        assert parsed_file.get_item(0).current_text == "New translation"
        assert parsed_file.is_modified
    
    def test_get_modified_items(self, parsed_file):
        """Test getting modified item indices."""
        # Initially no modifications
        assert parsed_file.get_modified_items() == []
        
        # Modify an item
        parsed_file.update_item_text(0, "Changed")
        
        modified = parsed_file.get_modified_items()
        assert 0 in modified
    
    def test_revert_item(self, parsed_file):
        """Test reverting a single item."""
        parsed_file.update_item_text(0, "Changed")
        
        parsed_file.revert_item(0)
        
        item = parsed_file.get_item(0)
        assert item.current_text == item.initial_text
    
    def test_revert_all(self, parsed_file):
        """Test reverting all items."""
        parsed_file.update_item_text(0, "Changed 1")
        parsed_file.update_item_text(1, "Changed 2")
        
        count = parsed_file.revert_all()
        
        assert count == 2
        assert not parsed_file.is_modified
    
    def test_breakpoint_toggle(self, parsed_file):
        """Test toggling breakpoints."""
        assert 5 not in parsed_file.breakpoints
        
        added = parsed_file.toggle_breakpoint(5)
        assert added is True
        assert 5 in parsed_file.breakpoints
        
        removed = parsed_file.toggle_breakpoint(5)
        assert removed is False
        assert 5 not in parsed_file.breakpoints
    
    def test_observer_pattern(self, parsed_file):
        """Test observer notifications."""
        notifications = []
        
        def on_modified(value):
            notifications.append(('modified', value))
        
        parsed_file.subscribe('modified', on_modified)
        parsed_file.is_modified = True
        
        assert ('modified', True) in notifications


class TestProjectModel:
    """Tests for ProjectModel."""
    
    def test_initial_state(self, project_model):
        """Test initial project state."""
        assert not project_model.is_open
        assert project_model.open_file_count == 0
    
    def test_open_project(self, project_model, temp_project_dir):
        """Test opening a project."""
        result = project_model.open_project(str(temp_project_dir))
        
        assert result is True
        assert project_model.is_open
        assert project_model.project_name == "test_project"
    
    def test_add_file(self, project_model, parsed_file):
        """Test adding a file to project."""
        result = project_model.add_file(parsed_file)
        
        assert result is True
        assert project_model.open_file_count == 1
        assert project_model.is_file_open(parsed_file.file_path)
    
    def test_set_active_file(self, project_model, parsed_file):
        """Test setting active file."""
        project_model.add_file(parsed_file)
        
        result = project_model.set_active_file(parsed_file.file_path)
        
        assert result is True
        assert project_model.active_file == parsed_file


class TestSettingsModel:
    """Tests for SettingsModel."""
    
    def test_singleton(self, settings_model):
        """Test singleton pattern."""
        from models.settings_model import SettingsModel
        
        another = SettingsModel.instance()
        assert another is settings_model
    
    def test_default_values(self, settings_model):
        """Test default setting values."""
        assert settings_model.ui_language in ["tr", "en"]
        assert settings_model.default_target_language is not None
    
    def test_set_and_get(self, settings_model):
        """Test setting and getting values."""
        settings_model.default_target_language = "de"
        
        assert settings_model.default_target_language == "de"
    
    def test_observer_pattern(self, settings_model):
        """Test settings change notifications."""
        changes = []
        
        def on_change(value):
            changes.append(value)
        
        settings_model.subscribe(settings_model.KEY_UI_LANGUAGE, on_change)
        settings_model.ui_language = "en"
        
        assert "en" in changes
