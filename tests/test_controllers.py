# -*- coding: utf-8 -*-
"""
Unit Tests for RenForge Controllers

Tests for TranslationController and FileController.
"""

import pytest
from unittest.mock import Mock, patch


class TestTranslationController:
    """Tests for TranslationController."""
    
    def test_initial_state(self, translation_controller):
        """Test initial controller state."""
        assert not translation_controller.is_translating
        assert translation_controller.source_language is not None
        assert translation_controller.target_language is not None
    
    @pytest.mark.skip(reason="Requires renforge_core.translate_text implementation")
    def test_translate_single_google_success(self, translation_controller):
        """Test successful single Google translation."""
        with patch('controllers.translation_controller.core.translate_text') as mock_translate:
            mock_translate.return_value = "Merhaba"
            
            result = translation_controller.translate_single_google("Hello")
            
            assert result == "Merhaba"
            mock_translate.assert_called_once()
    
    @pytest.mark.skip(reason="Requires renforge_core.translate_text implementation")
    def test_translate_single_google_failure(self, translation_controller):
        """Test failed Google translation."""
        with patch('controllers.translation_controller.core.translate_text') as mock_translate:
            mock_translate.side_effect = Exception("API Error")
            
            result = translation_controller.translate_single_google("Hello")
            
            assert result is None
    
    def test_cancel_translation(self, translation_controller):
        """Test translation cancellation."""
        translation_controller._is_translating = True
        
        translation_controller.cancel_translation()
        
        assert not translation_controller.is_translating
    
    def test_get_translation_stats(self, translation_controller, parsed_file):
        """Test getting translation statistics."""
        stats = translation_controller.get_translation_stats(parsed_file)
        
        assert 'total' in stats
        assert 'translated' in stats
        assert 'untranslated' in stats
        assert stats['total'] == 2


class TestFileController:
    """Tests for FileController."""
    
    def test_initial_state(self, file_controller):
        """Test initial controller state."""
        assert file_controller.get_modified_files() == []
    
    def test_open_nonexistent_file(self, file_controller):
        """Test opening a file that doesn't exist."""
        result = file_controller.open_file("/nonexistent/path.rpy")
        
        assert result is None
    
    def test_open_invalid_extension(self, file_controller, tmp_path):
        """Test opening a file with wrong extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        
        result = file_controller.open_file(str(txt_file))
        
        assert result is None
    
    def test_detect_translate_mode(self, file_controller, sample_lines):
        """Test mode detection for translate mode."""
        from renforge_enums import FileMode
        
        mode = file_controller._detect_mode(sample_lines)
        
        assert mode == FileMode.TRANSLATE
    
    def test_detect_direct_mode(self, file_controller, sample_direct_lines):
        """Test mode detection for direct mode."""
        from renforge_enums import FileMode
        
        mode = file_controller._detect_mode(sample_direct_lines)
        
        assert mode == FileMode.DIRECT


class TestAppController:
    """Tests for AppController."""
    
    def test_initial_state(self, app_controller):
        """Test initial app controller state."""
        assert app_controller.project is not None
        assert app_controller.settings is not None
        assert app_controller.file_controller is not None
        assert app_controller.translation_controller is not None
    
    def test_has_sub_controllers(self, app_controller):
        """Test that sub-controllers are accessible."""
        from controllers.file_controller import FileController
        from controllers.translation_controller import TranslationController
        
        assert isinstance(app_controller.file_controller, FileController)
        assert isinstance(app_controller.translation_controller, TranslationController)
