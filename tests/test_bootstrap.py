# -*- coding: utf-8 -*-
"""
Unit Tests for RenForge Bootstrap

Tests for the application bootstrap and Phase 4 integration.
These tests verify the module structure and DI container without requiring GUI.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    from interfaces.di_container import DIContainer
    from models.settings_model import SettingsModel
    
    DIContainer.reset_instance()
    SettingsModel.reset_instance()
    yield
    DIContainer.reset_instance()
    SettingsModel.reset_instance()


class TestBootstrapModule:
    """Tests for app_bootstrap module without GUI."""
    
    def test_bootstrap_module_imports(self):
        """Test that bootstrap module imports correctly."""
        import app_bootstrap
        
        assert hasattr(app_bootstrap, 'bootstrap')
        assert hasattr(app_bootstrap, 'get_container')
        assert hasattr(app_bootstrap, 'get_app_controller')
    
    def test_di_container_accessible(self):
        """Test DI container can be accessed."""
        from app_bootstrap import get_container
        from interfaces.di_container import DIContainer
        
        container = get_container()
        assert isinstance(container, DIContainer)


class TestDIContainerIntegration:
    """Integration tests for DI container with real components."""
    
    def test_settings_model_singleton(self):
        """Test SettingsModel singleton registration."""
        from interfaces.di_container import DIContainer
        from models.settings_model import SettingsModel
        
        container = DIContainer.instance()
        settings = SettingsModel.instance()
        container.register_instance(SettingsModel, settings)
        
        resolved = container.resolve(SettingsModel)
        assert resolved is settings
    
    def test_project_model_registration(self):
        """Test ProjectModel registration."""
        from interfaces.di_container import DIContainer
        from models.project_model import ProjectModel
        
        container = DIContainer.instance()
        project = ProjectModel()
        container.register_instance(ProjectModel, project)
        
        resolved = container.resolve(ProjectModel)
        assert resolved is project
    
    def test_app_controller_creation(self):
        """Test AppController can be created."""
        from controllers.app_controller import AppController
        
        controller = AppController()
        
        assert controller is not None
        assert hasattr(controller, 'file_controller')
        assert hasattr(controller, 'translation_controller')
    
    def test_file_controller_accessible_via_app(self):
        """Test FileController is accessible via AppController."""
        from controllers.app_controller import AppController
        from controllers.file_controller import FileController
        
        controller = AppController()
        
        assert isinstance(controller.file_controller, FileController)
    
    def test_translation_controller_accessible_via_app(self):
        """Test TranslationController is accessible via AppController."""
        from controllers.app_controller import AppController
        from controllers.translation_controller import TranslationController
        
        controller = AppController()
        
        assert isinstance(controller.translation_controller, TranslationController)


class TestControllerSignals:
    """Test controller signals work properly."""
    
    def test_app_controller_has_signals(self):
        """Test AppController has expected signals."""
        from controllers.app_controller import AppController
        
        controller = AppController()
        
        assert hasattr(controller, 'app_ready')
        assert hasattr(controller, 'models_loaded')
        assert hasattr(controller, 'languages_loaded')
        assert hasattr(controller, 'status_updated')
    
    def test_file_controller_has_signals(self):
        """Test FileController has expected signals."""
        from controllers.app_controller import AppController
        
        controller = AppController()
        fc = controller.file_controller
        
        assert hasattr(fc, 'file_opened')
        assert hasattr(fc, 'file_saved')
        assert hasattr(fc, 'file_closed')
        assert hasattr(fc, 'file_error')
    
    def test_status_updated_signal_emits(self):
        """Test status_updated signal can be emitted."""
        from controllers.app_controller import AppController
        from PyQt6.QtCore import QObject
        
        controller = AppController()
        received_messages = []
        
        controller.status_updated.connect(lambda msg: received_messages.append(msg))
        controller.status_updated.emit("Test message")
        
        assert len(received_messages) == 1
        assert received_messages[0] == "Test message"


class TestInterfaceRegistrations:
    """Test interface registrations in DI container."""
    
    def test_i_app_controller_export(self):
        """Test IAppController is exported from interfaces."""
        from interfaces import IAppController
        
        assert IAppController is not None
    
    def test_i_file_controller_export(self):
        """Test IFileController is exported from interfaces."""
        from interfaces import IFileController
        
        assert IFileController is not None
    
    def test_i_translation_controller_export(self):
        """Test ITranslationController is exported from interfaces."""
        from interfaces import ITranslationController
        
        assert ITranslationController is not None
    
    def test_i_main_view_export(self):
        """Test IMainView is exported from interfaces."""
        from interfaces import IMainView
        
        assert IMainView is not None
