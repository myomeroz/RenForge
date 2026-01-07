# -*- coding: utf-8 -*-
"""
RenForge Controller Interfaces

Protocol definitions for Controller layer components.
"""

from typing import Protocol, Optional, List, Dict, Any, Callable, runtime_checkable
from PyQt6.QtCore import pyqtSignal


@runtime_checkable
class IFileController(Protocol):
    """
    Protocol for file controller.
    
    Defines the interface for file operations.
    """
    
    # Signals
    file_opened: pyqtSignal
    file_saved: pyqtSignal
    file_closed: pyqtSignal
    file_error: pyqtSignal
    
    # Methods
    def open_file(
        self, 
        file_path: str, 
        mode: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Any]:
        """Open and parse a file."""
        ...
    
    def save_file(self, parsed_file: Any) -> bool:
        """Save a file to disk."""
        ...
    
    def close_file(self, file_path: str, force: bool = False) -> bool:
        """Close a file."""
        ...
    
    def is_file_modified(self, file_path: str) -> bool:
        """Check if a file has unsaved changes."""
        ...
    
    def get_modified_files(self) -> List[Any]:
        """Get all files with unsaved changes."""
        ...


@runtime_checkable
class ITranslationController(Protocol):
    """
    Protocol for translation controller.
    
    Defines the interface for translation operations.
    """
    
    # Signals
    translation_started: pyqtSignal
    translation_progress: pyqtSignal
    translation_completed: pyqtSignal
    translation_error: pyqtSignal
    item_translated: pyqtSignal
    
    # Properties
    @property
    def is_translating(self) -> bool:
        """Check if a translation is in progress."""
        ...
    
    @property
    def source_language(self) -> str:
        """Get default source language."""
        ...
    
    @property
    def target_language(self) -> str:
        """Get default target language."""
        ...
    
    # Methods
    def translate_single_google(
        self, 
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> Optional[str]:
        """Translate a single text with Google Translate."""
        ...
    
    def translate_single_ai(
        self,
        text: str,
        model: Optional[str] = None,
        context: Optional[str] = None
    ) -> Optional[str]:
        """Translate/edit a single text with AI."""
        ...
    
    def translate_batch_google(
        self,
        parsed_file: Any,
        indices: List[int],
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Translate multiple items with Google Translate."""
        ...
    
    def translate_batch_ai(
        self,
        parsed_file: Any,
        indices: List[int],
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Translate multiple items with AI."""
        ...
    
    def cancel_translation(self) -> None:
        """Cancel ongoing translation."""
        ...


@runtime_checkable
class IAppController(Protocol):
    """
    Protocol for main application controller.
    """
    
    # Signals
    app_ready: pyqtSignal
    models_loaded: pyqtSignal
    languages_loaded: pyqtSignal
    status_updated: pyqtSignal
    
    # Properties
    @property
    def file_controller(self) -> IFileController:
        """Get file controller."""
        ...
    
    @property
    def translation_controller(self) -> ITranslationController:
        """Get translation controller."""
        ...
    
    # Methods
    def initialize(self) -> None:
        """Initialize the application."""
        ...
    
    def open_project(self, project_path: str) -> bool:
        """Open a project folder."""
        ...
    
    def open_file(self, file_path: str, mode: Optional[str] = None) -> None:
        """Open a file."""
        ...
    
    def save_current_file(self) -> None:
        """Save the currently active file."""
        ...
    
    def save_all_files(self) -> None:
        """Save all modified files."""
        ...
    
    def shutdown(self) -> bool:
        """Prepare for application shutdown."""
        ...


@runtime_checkable
class IBatchController(Protocol):
    """
    Protocol for batch translation controller.
    
    Defines the interface for batch translation operations.
    """
    
    # Properties
    @property
    def errors(self) -> List[str]:
        """Get list of errors from batch operation."""
        ...
    
    @property
    def warnings(self) -> List[str]:
        """Get list of warnings from batch operation."""
        ...
    
    # Methods
    def clear_results(self) -> None:
        """Clear all batch result tracking data."""
        ...
    
    def handle_item_updated(
        self, 
        item_index: int, 
        translated_text: str, 
        updated_item_data: Dict[str, Any]
    ) -> None:
        """Handle batch item update signal from worker."""
        ...
    
    def handle_error(self, details: str) -> None:
        """Handle batch translation error signal."""
        ...
    
    def handle_warning(self, details: str) -> None:
        """Handle batch translation warning signal."""
        ...
    
    def handle_finished(self, results: Dict[str, Any]) -> None:
        """Handle batch translation finished signal."""
        ...


@runtime_checkable
class IProjectController(Protocol):
    """
    Protocol for project controller.
    
    Defines the interface for project tree and panel management.
    """
    
    # Methods
    def handle_open_project(self) -> None:
        """Open project folder dialog."""
        ...
    
    def populate_project_tree(self, project_path: str) -> None:
        """Populate the project tree view with files."""
        ...
    
    def handle_tree_item_activated(self, index: Any) -> None:
        """Handle activation of a tree view item."""
        ...
    
    def handle_activity_bar_toggle(self, checked: bool) -> None:
        """Handle toggle of activity bar buttons."""
        ...
    
    def set_left_panel_visibility(self, visible: bool) -> None:
        """Set the visibility of the left panel container."""
        ...

