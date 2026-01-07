# -*- coding: utf-8 -*-
"""
RenForge App Controller

Main application controller that:
- Coordinates between View and other controllers
- Manages application lifecycle
- Handles global state and settings
"""

from typing import Optional, Dict, Any, List

from PyQt6.QtCore import QObject, pyqtSignal

from renforge_logger import get_logger
from locales import tr
from models.project_model import ProjectModel
from models.settings_model import SettingsModel
from controllers.file_controller import FileController
from controllers.translation_controller import TranslationController
import renforge_config as config
import renforge_ai as ai

logger = get_logger("controllers.app")


class AppController(QObject):
    """
    Main application controller - coordinates all other controllers.
    
    Responsibilities:
    - Application startup and shutdown
    - Global state management
    - Settings coordination
    - Controller lifecycle
    
    Signals:
        app_ready: Emitted when application is fully initialized
        models_loaded(list): Emitted with available AI model names
        languages_loaded(dict): Emitted with available languages
        status_updated(str): Emitted with status bar message
    """
    
    app_ready = pyqtSignal()
    models_loaded = pyqtSignal(list)
    languages_loaded = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    
    def __init__(
        self,
        file_controller: Optional[FileController] = None,
        translation_controller: Optional[TranslationController] = None,
        settings: Optional[SettingsModel] = None,
        project: Optional[ProjectModel] = None
    ):
        """
        Initialize the application controller.
        
        Args:
            file_controller: Injected file controller (DI)
            translation_controller: Injected translation controller (DI)
            settings: Injected settings model (DI)
            project: Injected project model (DI)
            
        If no arguments provided, falls back to creating instances internally
        for backward compatibility during migration.
        """
        super().__init__()
        
        # Use injected dependencies or create internally (backward compat)
        self._settings = settings or SettingsModel.instance()
        self._project = project or ProjectModel()
        
        # Use injected controllers or create internally (backward compat)
        self._file_controller = file_controller or FileController(
            self._project, self._settings
        )
        self._translation_controller = translation_controller or TranslationController(
            self._settings
        )
        
        # Connect sub-controller signals
        self._connect_signals()
        
        # State
        self._available_models: List[str] = []
        self._available_languages: Dict[str, str] = {}
        
        logger.debug("AppController initialized")
    
    def _connect_signals(self):
        """Connect signals from sub-controllers."""
        # File controller
        self._file_controller.file_opened.connect(self._on_file_opened)
        self._file_controller.file_saved.connect(self._on_file_saved)
        self._file_controller.file_error.connect(self._on_error)
        
        # Translation controller
        self._translation_controller.translation_completed.connect(
            self._on_translation_completed
        )
        self._translation_controller.translation_error.connect(self._on_error)
    
    # =========================================================================
    # PROPERTIES
    # =========================================================================
    
    @property
    def settings(self) -> SettingsModel:
        """Get settings model."""
        return self._settings
    
    @property
    def project(self) -> ProjectModel:
        """Get project model."""
        return self._project
    
    @property
    def file_controller(self) -> FileController:
        """Get file controller."""
        return self._file_controller
    
    @property
    def translation_controller(self) -> TranslationController:
        """Get translation controller."""
        return self._translation_controller
    
    @property
    def available_models(self) -> List[str]:
        """Get available AI models."""
        return self._available_models.copy()
    
    @property
    def available_languages(self) -> Dict[str, str]:
        """Get available languages."""
        return self._available_languages.copy()
    
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    def initialize(self):
        """
        Initialize the application.
        
        Call this after all UI is set up.
        """
        logger.info("Initializing application...")
        
        # Load languages
        self._load_languages()
        
        # Load AI models in background (non-blocking)
        self._load_models_async()
        
        self.app_ready.emit()
        logger.info("Application ready")
    
    def _load_languages(self):
        """Load available languages."""
        # Import from config or locales
        from renforge_core import SUPPORTED_LANGUAGES
        
        self._available_languages = SUPPORTED_LANGUAGES or {
            'en': 'English',
            'tr': 'Türkçe',
        }
        
        self.languages_loaded.emit(self._available_languages)
        logger.debug(f"Loaded {len(self._available_languages)} languages")
    
    def _load_models_async(self):
        """Load available AI models asynchronously."""
        try:
            models = ai.get_available_models() or []
            self._available_models = models
            self.models_loaded.emit(models)
            logger.info(f"Loaded {len(models)} AI models")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self._available_models = []
            self.models_loaded.emit([])
    
    def refresh_models(self):
        """Refresh the model list."""
        self._load_models_async()
    
    # =========================================================================
    # APPLICATION ACTIONS
    # =========================================================================
    
    def open_project(self, project_path: str) -> bool:
        """
        Open a project folder.
        
        Args:
            project_path: Path to the project folder
            
        Returns:
            True if successful
        """
        success = self._project.open_project(project_path)
        if success:
            self.status_updated.emit(tr("status_project_opened", name=self._project.project_name))
        return success
    
    def open_file(self, file_path: str, mode: Optional[str] = None):
        """
        Open a file.
        
        Args:
            file_path: Path to the file
            mode: Optional mode override
        """
        self._file_controller.open_file(file_path, mode)
    
    def save_current_file(self):
        """Save the currently active file."""
        active_file = self._project.active_file
        if active_file:
            self._file_controller.save_file(active_file)
    
    def save_all_files(self):
        """Save all modified files."""
        for parsed_file in self._project.modified_files:
            self._file_controller.save_file(parsed_file)
    
    def close_current_file(self) -> bool:
        """Close the currently active file."""
        if self._project.active_file_path:
            return self._file_controller.close_file(self._project.active_file_path)
        return True
    
    # =========================================================================
    # SETTINGS ACTIONS
    # =========================================================================
    
    def save_settings(self):
        """Save application settings."""
        self._settings.save()
        logger.debug("Settings saved")
    
    def get_window_geometry(self) -> Dict[str, Any]:
        """Get window geometry for saving."""
        return {
            'width': self._settings.window_size[0],
            'height': self._settings.window_size[1],
            'maximized': self._settings.window_maximized,
        }
    
    def save_window_geometry(self, width: int, height: int, maximized: bool):
        """Save window geometry."""
        self._settings.window_size = (width, height)
        self._settings.window_maximized = maximized
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_file_opened(self, parsed_file):
        """Handle file opened event."""
        self.status_updated.emit(
            tr("status_file_opened", name=parsed_file.filename, count=parsed_file.item_count)
        )
    
    def _on_file_saved(self, file_path: str):
        """Handle file saved event."""
        from pathlib import Path
        self.status_updated.emit(tr("status_file_saved", name=Path(file_path).name))
    
    def _on_translation_completed(self, count: int):
        """Handle translation completed event."""
        self.status_updated.emit(tr("status_translation_done", count=count))
    
    def _on_error(self, message: str):
        """Handle error from sub-controllers."""
        self.status_updated.emit(f"Error: {message}")
        logger.error(message)
    
    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    
    def shutdown(self) -> bool:
        """
        Prepare for application shutdown.
        
        Returns:
            True if shutdown can proceed (no unsaved changes or user confirmed)
        """
        if self._project.has_unsaved_changes:
            # Caller should prompt user
            return False
        
        self.save_settings()
        return True
    
    def __repr__(self) -> str:
        return f"AppController(project={self._project.project_name})"
