# -*- coding: utf-8 -*-
"""
RenForge View Interfaces

Protocol definitions for View layer components.
These protocols define the contract that views must fulfill.
"""

from typing import Protocol, Optional, Dict, List, Any, runtime_checkable
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


@runtime_checkable
class IMainView(Protocol):
    """
    Protocol for main application view.
    
    Defines the interface that the main window must implement.
    Controllers should depend on this interface, not concrete views.
    """
    
    # =========================================================================
    # SIGNALS (expected to be present)
    # =========================================================================
    
    # File operations
    open_project_requested: pyqtSignal
    open_file_requested: pyqtSignal
    save_requested: pyqtSignal
    save_all_requested: pyqtSignal
    close_tab_requested: pyqtSignal
    exit_requested: pyqtSignal
    
    # Navigation
    tab_changed: pyqtSignal
    item_selected: pyqtSignal
    
    # Translation
    translate_google_requested: pyqtSignal
    translate_ai_requested: pyqtSignal
    batch_google_requested: pyqtSignal
    batch_ai_requested: pyqtSignal
    
    # Settings
    target_language_changed: pyqtSignal
    source_language_changed: pyqtSignal
    model_changed: pyqtSignal
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def show_status_message(self, message: str, timeout: int = 0) -> None:
        """Show a message in the status bar."""
        ...
    
    def show_info_dialog(self, title: str, message: str) -> None:
        """Show an information dialog."""
        ...
    
    def show_warning_dialog(self, title: str, message: str) -> None:
        """Show a warning dialog."""
        ...
    
    def show_error_dialog(self, title: str, message: str) -> None:
        """Show an error dialog."""
        ...
    
    def show_question_dialog(self, title: str, message: str) -> bool:
        """Show a Yes/No question dialog. Returns True for Yes."""
        ...
    
    def update_window_title(self, suffix: str = "") -> None:
        """Update window title."""
        ...
    
    # Tab operations
    def add_tab(self, widget: QWidget, title: str) -> int:
        """Add a tab and return its index."""
        ...
    
    def remove_tab(self, index: int) -> None:
        """Remove a tab by index."""
        ...
    
    def set_current_tab(self, index: int) -> None:
        """Set the current tab."""
        ...
    
    def get_current_tab_index(self) -> int:
        """Get the current tab index."""
        ...
    
    def set_tab_text(self, index: int, text: str) -> None:
        """Set tab title text."""
        ...
    
    # Combo operations
    def populate_languages(self, languages: Dict[str, str]) -> None:
        """Populate language combo boxes."""
        ...
    
    def populate_models(self, models: List[str], current: Optional[str] = None) -> None:
        """Populate model combo box."""
        ...
    
    def get_target_language(self) -> Optional[str]:
        """Get selected target language code."""
        ...
    
    def get_source_language(self) -> Optional[str]:
        """Get selected source language code."""
        ...
    
    def get_selected_model(self) -> Optional[str]:
        """Get selected model name."""
        ...


@runtime_checkable
class ITableView(Protocol):
    """
    Protocol for translation table view.
    """
    
    # Signals
    item_selected: pyqtSignal
    cell_edited: pyqtSignal
    
    # Methods
    def get_selected_rows(self) -> List[int]:
        """Get list of selected row indices."""
        ...
    
    def get_selected_row(self) -> int:
        """Get the first selected row, or -1 if none."""
        ...
    
    def select_row(self, row: int) -> None:
        """Select a specific row."""
        ...
    
    def set_cell_text(self, row: int, column: int, text: str) -> None:
        """Set text in a cell."""
        ...
    
    def add_row(self, data: List[str], editable_columns: Optional[List[int]] = None) -> int:
        """Add a new row with data."""
        ...
    
    def clear_contents_only(self) -> None:
        """Clear contents but keep column configuration."""
        ...


@runtime_checkable
class IDialogView(Protocol):
    """
    Protocol for dialog views.
    Base interface that all dialog views should follow.
    """
    
    def exec(self) -> int:
        """Show the dialog modally and return result code."""
        ...
    
    def accept(self) -> None:
        """Accept and close the dialog."""
        ...
    
    def reject(self) -> None:
        """Reject and close the dialog."""
        ...
