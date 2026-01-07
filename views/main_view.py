# -*- coding: utf-8 -*-
"""
RenForge Main View

The main application window View component.
Responsible for:
- UI layout and rendering
- Emitting signals for user actions
- NO business logic (delegated to controllers)
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QTabWidget, QComboBox, QLabel,
                             QLineEdit, QCheckBox, QPushButton, QStatusBar,
                             QMenuBar, QMenu, QToolBar, QMessageBox,
                             QTreeView, QDockWidget, QButtonGroup)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QFont

from renforge_logger import get_logger
from locales import tr
import renforge_config as config

logger = get_logger("views.main")


class MainView(QMainWindow):
    """
    Main application window - pure View component.
    
    This class handles ONLY:
    - UI element creation and layout
    - Signal emission for user actions
    - Display updates when requested by controllers
    
    All business logic is handled by controllers.
    
    Signals:
        # File operations
        open_project_requested: User wants to open a project
        open_file_requested: User wants to open a file
        save_requested: User wants to save current file
        save_as_requested: User wants to save as
        save_all_requested: User wants to save all
        close_tab_requested(int): User wants to close a tab
        
        # Navigation
        tab_changed(int): User switched tabs
        item_selected(int): User selected an item
        
        # Translation
        translate_google_requested: User wants Google translation
        translate_ai_requested: User wants AI translation
        batch_google_requested: User wants batch Google translation
        batch_ai_requested: User wants batch AI translation
        
        # Settings
        target_language_changed(str): Target language combo changed
        source_language_changed(str): Source language combo changed
        model_changed(str): AI model combo changed
        
        # Search
        find_next_requested(str, bool): Find next (query, is_regex)
        replace_requested(str, str, bool): Replace (find, replace, is_regex)
        replace_all_requested(str, str, bool): Replace all
    """
    
    # File operation signals
    open_project_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    save_requested = pyqtSignal()
    save_as_requested = pyqtSignal()
    save_all_requested = pyqtSignal()
    close_tab_requested = pyqtSignal(int)
    exit_requested = pyqtSignal()
    
    # Navigation signals
    tab_changed = pyqtSignal(int)
    item_selected = pyqtSignal(int)
    prev_item_requested = pyqtSignal()
    next_item_requested = pyqtSignal()
    
    # Translation signals
    translate_google_requested = pyqtSignal()
    translate_ai_requested = pyqtSignal()
    batch_google_requested = pyqtSignal()
    batch_ai_requested = pyqtSignal()
    
    # Settings signals
    target_language_changed = pyqtSignal(str)
    source_language_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    
    # Search signals
    find_next_requested = pyqtSignal(str, bool)  # query, is_regex
    replace_requested = pyqtSignal(str, str, bool)  # find, replace, is_regex
    replace_all_requested = pyqtSignal(str, str, bool)
    
    # Breakpoint signals
    toggle_breakpoint_requested = pyqtSignal()
    next_breakpoint_requested = pyqtSignal()
    clear_breakpoints_requested = pyqtSignal()
    
    # Edit signals
    revert_item_requested = pyqtSignal()
    revert_selected_requested = pyqtSignal()
    revert_all_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # UI element references (set during build)
        self.tab_widget: Optional[QTabWidget] = None
        self.source_lang_combo: Optional[QComboBox] = None
        self.target_lang_combo: Optional[QComboBox] = None
        self.model_combo: Optional[QComboBox] = None
        self.search_input: Optional[QLineEdit] = None
        self.replace_input: Optional[QLineEdit] = None
        self.regex_checkbox: Optional[QCheckBox] = None
        self.mode_display_label: Optional[QLabel] = None
        self.project_tree: Optional[QTreeView] = None
        self.left_panel_container: Optional[QWidget] = None
        self.activity_bar_group: Optional[QButtonGroup] = None
        
        # Menu/toolbar references
        self._menus: Dict[str, QMenu] = {}
        self._actions: Dict[str, QAction] = {}
        
        self._setup_window()
        logger.debug("MainView initialized")
    
    def _setup_window(self):
        """Configure basic window properties."""
        self.setWindowTitle(tr("window_title", version=config.VERSION))
        self.resize(1200, 800)
    
    # =========================================================================
    # UI BUILDING (called by UIBuilder or controller)
    # =========================================================================
    
    def set_central_layout(self, widget: QWidget):
        """Set the central widget."""
        self.setCentralWidget(widget)
    
    def set_tab_widget(self, tab_widget: QTabWidget):
        """Set and connect the tab widget."""
        self.tab_widget = tab_widget
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        self.tab_changed.emit(index)
    
    # =========================================================================
    # MENU BUILDING
    # =========================================================================
    
    def add_menu(self, name: str, title: str) -> QMenu:
        """Add a menu to the menu bar."""
        menu = self.menuBar().addMenu(title)
        self._menus[name] = menu
        return menu
    
    def get_menu(self, name: str) -> Optional[QMenu]:
        """Get a menu by name."""
        return self._menus.get(name)
    
    def add_action(self, menu_name: str, action_name: str, text: str, 
                   callback=None, shortcut: str = None) -> QAction:
        """Add an action to a menu."""
        menu = self._menus.get(menu_name)
        if not menu:
            logger.warning(f"Menu not found: {menu_name}")
            return None
        
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if callback:
            action.triggered.connect(callback)
        
        menu.addAction(action)
        self._actions[action_name] = action
        return action
    
    def get_action(self, name: str) -> Optional[QAction]:
        """Get an action by name."""
        return self._actions.get(name)
    
    def set_action_enabled(self, name: str, enabled: bool):
        """Enable or disable an action."""
        action = self._actions.get(name)
        if action:
            action.setEnabled(enabled)
    
    # =========================================================================
    # DISPLAY UPDATES
    # =========================================================================
    
    def show_status_message(self, message: str, timeout: int = 0):
        """Show a message in the status bar."""
        self.statusBar().showMessage(message, timeout)
    
    def show_info_dialog(self, title: str, message: str):
        """Show an information dialog."""
        QMessageBox.information(self, title, message)
    
    def show_warning_dialog(self, title: str, message: str):
        """Show a warning dialog."""
        QMessageBox.warning(self, title, message)
    
    def show_error_dialog(self, title: str, message: str):
        """Show an error dialog."""
        QMessageBox.critical(self, title, message)
    
    def show_question_dialog(self, title: str, message: str) -> bool:
        """Show a Yes/No question dialog. Returns True for Yes."""
        result = QMessageBox.question(self, title, message)
        return result == QMessageBox.StandardButton.Yes
    
    def update_window_title(self, suffix: str = ""):
        """Update window title with optional suffix."""
        base_title = tr("window_title", version=config.VERSION)
        if suffix:
            self.setWindowTitle(f"{base_title} - {suffix}")
        else:
            self.setWindowTitle(base_title)
    
    def set_mode_display(self, mode_text: str):
        """Update the mode display label."""
        if self.mode_display_label:
            self.mode_display_label.setText(mode_text)
    
    # =========================================================================
    # TAB OPERATIONS
    # =========================================================================
    
    def add_tab(self, widget: QWidget, title: str) -> int:
        """Add a tab and return its index."""
        if self.tab_widget:
            return self.tab_widget.addTab(widget, title)
        return -1
    
    def remove_tab(self, index: int):
        """Remove a tab by index."""
        if self.tab_widget:
            self.tab_widget.removeTab(index)
    
    def set_current_tab(self, index: int):
        """Set the current tab."""
        if self.tab_widget:
            self.tab_widget.setCurrentIndex(index)
    
    def get_current_tab_index(self) -> int:
        """Get the current tab index."""
        if self.tab_widget:
            return self.tab_widget.currentIndex()
        return -1
    
    def get_tab_count(self) -> int:
        """Get the number of tabs."""
        if self.tab_widget:
            return self.tab_widget.count()
        return 0
    
    def set_tab_text(self, index: int, text: str):
        """Set tab title text."""
        if self.tab_widget:
            self.tab_widget.setTabText(index, text)
    
    def get_current_tab_widget(self) -> Optional[QWidget]:
        """Get the widget of the current tab."""
        if self.tab_widget:
            return self.tab_widget.currentWidget()
        return None
    
    # =========================================================================
    # COMBO BOX OPERATIONS
    # =========================================================================
    
    def populate_languages(self, languages: Dict[str, str]):
        """
        Populate language combo boxes.
        
        Args:
            languages: Dict of code -> display name
        """
        for combo in [self.source_lang_combo, self.target_lang_combo]:
            if combo:
                combo.blockSignals(True)
                combo.clear()
                for code, name in languages.items():
                    combo.addItem(name, code)
                combo.blockSignals(False)
    
    def populate_models(self, models: List[str], current: Optional[str] = None):
        """
        Populate model combo box.
        
        Args:
            models: List of model names
            current: Currently selected model (optional)
        """
        if self.model_combo:
            self.model_combo.blockSignals(True)
            self.model_combo.clear()
            self.model_combo.addItems(models)
            if current and current in models:
                self.model_combo.setCurrentText(current)
            self.model_combo.blockSignals(False)
    
    def get_target_language(self) -> Optional[str]:
        """Get selected target language code."""
        if self.target_lang_combo:
            return self.target_lang_combo.currentData()
        return None
    
    def get_source_language(self) -> Optional[str]:
        """Get selected source language code."""
        if self.source_lang_combo:
            return self.source_lang_combo.currentData()
        return None
    
    def get_selected_model(self) -> Optional[str]:
        """Get selected model name."""
        if self.model_combo:
            return self.model_combo.currentText()
        return None
    
    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================
    
    def get_search_query(self) -> str:
        """Get current search query."""
        if self.search_input:
            return self.search_input.text()
        return ""
    
    def get_replace_text(self) -> str:
        """Get current replace text."""
        if self.replace_input:
            return self.replace_input.text()
        return ""
    
    def is_regex_enabled(self) -> bool:
        """Check if regex checkbox is checked."""
        if self.regex_checkbox:
            return self.regex_checkbox.isChecked()
        return False
    
    # =========================================================================
    # PROJECT PANEL
    # =========================================================================
    
    def set_left_panel_visible(self, visible: bool):
        """Show or hide the left panel."""
        if self.left_panel_container:
            self.left_panel_container.setVisible(visible)
    
    def is_left_panel_visible(self) -> bool:
        """Check if left panel is visible."""
        if self.left_panel_container:
            return self.left_panel_container.isVisible()
        return False
    
    # =========================================================================
    # WINDOW GEOMETRY
    # =========================================================================
    
    def get_window_geometry(self) -> Dict[str, Any]:
        """Get current window geometry for saving."""
        return {
            'width': self.width(),
            'height': self.height(),
            'maximized': self.isMaximized()
        }
    
    def restore_window_geometry(self, geometry: Dict[str, Any]):
        """Restore window geometry from saved data."""
        if geometry.get('maximized'):
            self.showMaximized()
        else:
            w = geometry.get('width', 1200)
            h = geometry.get('height', 800)
            self.resize(w, h)
    
    def __repr__(self) -> str:
        return f"MainView(tabs={self.get_tab_count()})"
