# -*- coding: utf-8 -*-
"""
RenForge Project Controller
Handles project tree navigation, panel visibility, and file opening from the tree.
"""

import os

from renforge_logger import get_logger
logger = get_logger("controllers.project_controller")

from PySide6.QtCore import QDir

import gui.gui_file_manager as file_manager
import gui.gui_tab_manager as tab_manager
import gui.gui_settings_manager as settings_manager


class ProjectController:
    """
    Controls project-related functionality:
    - Opening project folders
    - Populating and navigating the project tree
    - Managing left panel visibility
    - Handling activity bar toggles
    """
    
    def __init__(self, main_window):
        """
        Initialize ProjectController with reference to the main window.
        
        Args:
            main_window: The RenForgeGUI instance
        """
        self.main = main_window
    
    def handle_open_project(self):
        """Open project folder dialog."""
        file_manager.open_project_dialog(self.main)
    
    def populate_project_tree(self, project_path: str):
        """
        Populate the project tree view with files from the given path.
        
        Args:
            project_path: Path to the project folder
        """
        if not project_path or not os.path.isdir(project_path):
            logger.error(f"Invalid project path provided: {project_path}")
            self.main.current_project_path = None
            self._toggle_project_panel(False)
            self.main._update_ui_state()
            return
        
        self.main.current_project_path = project_path
        logger.debug(f"Populating project tree for: {project_path}")
        
        # Configure file system model
        self.main.file_system_model.setRootPath(project_path)
        self.main.file_system_model.setFilter(
            QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files
        )
        self.main.file_system_model.setNameFilters(["*.rpy"])
        self.main.file_system_model.setNameFilterDisables(False)
        
        # Set up tree view
        self.main.project_tree_view.setModel(self.main.file_system_model)
        root_index = self.main.file_system_model.index(project_path)
        self.main.project_tree_view.setRootIndex(root_index)
        
        # Hide extra columns (size, date, etc.)
        for i in range(1, self.main.file_system_model.columnCount()):
            self.main.project_tree_view.hideColumn(i)
        
        # Show project panel
        self.main.project_view_button.setChecked(True)
    
    def handle_tree_item_activated(self, index):
        """
        Handle activation (double-click/Enter) of a tree view item.
        
        Args:
            index: QModelIndex of the activated item
        """
        if not self.main.file_system_model:
            return
        
        file_path = self.main.file_system_model.filePath(index)
        is_dir = self.main.file_system_model.isDir(index)
        
        # Ignore directories
        if is_dir:
            return
        
        # Only handle .rpy files
        if file_path and file_path.lower().endswith(".rpy"):
            logger.debug(f"Tree item activated: {file_path}")
            
            # Check if already open in a tab
            existing_tab_index = tab_manager.find_tab_by_path(self.main, file_path)
            if existing_tab_index is not None:
                logger.debug(f"File already open in tab {existing_tab_index}. Switching.")
                self.main.tab_widget.setCurrentIndex(existing_tab_index)
                return
            
            logger.debug("File not open. Determining mode and loading...")
            
            # Ensure mode setting is configured
            if not settings_manager.ensure_mode_setting_chosen(self.main):
                self.main.statusBar().showMessage(
                    "File opening canceled. Mode setting must be selected.", 5000
                )
                return
            
            # Determine mode and load file
            final_mode = file_manager.determine_file_mode(self.main, file_path)
            if final_mode:
                file_manager.load_file(self.main, file_path, final_mode)
            else:
                logger.debug("File loading cancelled (mode selection).")
        else:
            logger.debug(f"Ignoring activation for non-rpy file: {file_path}")
    
    def handle_activity_bar_toggle(self, checked: bool):
        """
        Handle toggle of activity bar buttons (project view only).
        
        Args:
            checked: Whether the button is now checked
        """
        sender_button = self.main.sender()
        
        logger.debug(f"Activity Bar Toggle: Button '{sender_button.objectName()}' -> Checked: {checked}")
        
        # Only Project View remains in Activity Bar
        if sender_button is self.main.project_view_button:
            self.set_left_panel_visibility(checked)
        
        self.main._update_ui_state()
    
    def set_left_panel_visibility(self, visible: bool):
        """
        Set the visibility of the left panel container.
        
        Args:
            visible: Whether the panel should be visible
        """
        if self.main.left_panel_container.isVisible() == visible:
            return
        
        logger.debug(f"Setting left panel visibility to: {visible}")
        self.main.left_panel_container.setVisible(visible)
        
        # Enable/disable splitter handle
        self.main.splitter.handle(1).setDisabled(not visible)
        
        if visible:
            # Ensure panel has reasonable width
            current_sizes = self.main.splitter.sizes()
            if current_sizes[0] < 50:
                total_width = sum(current_sizes)
                left_width = 250
                right_width = max(200, total_width - left_width)
                self.main.splitter.setSizes([left_width, right_width])
                logger.debug(f"  Splitter sizes reset to: {[left_width, right_width]}")
            else:
                logger.debug(f"  Splitter sizes remain: {current_sizes}")
        else:
            # Collapse left panel
            current_sizes = self.main.splitter.sizes()
            if current_sizes[0] > 0:
                total_width = sum(current_sizes)
                self.main.splitter.setSizes([0, total_width])
                logger.debug(f"  Splitter sizes set to hide left panel: {[0, total_width]}")
    
    def _toggle_project_panel(self, show: bool):
        """Helper to toggle project panel visibility via button."""
        self.main.project_view_button.setChecked(show)
