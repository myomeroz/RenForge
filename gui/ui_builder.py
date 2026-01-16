# -*- coding: utf-8 -*-
"""
RenForge UI Builder
Responsible for creating all UI widgets and layouts for the main window.
"""

import os
from renforge_logger import get_logger
logger = get_logger("gui.ui_builder")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTabWidget, QGroupBox, QCheckBox, QSplitter, QSizePolicy,
    QToolButton, QStackedLayout, QTreeView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

import renforge_config as config
from locales import tr

# These will be imported by the main window and passed to handlers
import gui.gui_file_manager as file_manager
import gui.gui_tab_manager as tab_manager
import gui.gui_table_manager as table_manager
import gui.gui_action_handler as action_handler
import gui.gui_settings_manager as settings_manager


def safe_icon(relative_path: str) -> QIcon:
    """
    Gracefully load an icon, returning empty QIcon if file doesn't exist.
    Prevents Qt warnings about missing SVG files.
    """
    full_path = config.resource_path(relative_path)
    if os.path.isfile(full_path):
        return QIcon(full_path)
    else:
        # Log once but don't spam - icons are optional
        logger.debug(f"Icon not found (optional): {relative_path}")
        return QIcon()


class UIBuilder:
    """
    Builds all UI components for the RenForgeGUI main window.
    
    Usage:
        builder = UIBuilder(main_window)
        builder.build_activity_bar()
        builder.build_left_panel()
        builder.build_main_content()
        builder.build_tools_group()
        builder.assemble_layout()
        builder.build_menu_bar()
    """
    
    def __init__(self, main_window):
        """
        Initialize UIBuilder with reference to the main window.
        
        Args:
            main_window: The RenForgeGUI instance
        """
        self.main = main_window
    
    def build_activity_bar(self) -> QWidget:
        """Build the left activity bar with view toggle buttons."""
        activity_bar = QWidget()
        activity_bar.setObjectName("activityBar")
        layout = QVBoxLayout(activity_bar)
        layout.setContentsMargins(2, 5, 2, 5)
        layout.setSpacing(5)
        
        # Project view button
        self.main.project_view_button = QToolButton()
        self.main.project_view_button.setObjectName("projectViewButton")
        self.main.project_view_button.setIcon(safe_icon("pics/project.svg"))
        self.main.project_view_button.setToolTip("Show/hide project panel")
        self.main.project_view_button.setCheckable(True)
        self.main.project_view_button.setChecked(True)
        # We need to update this handler since we removed stack
        self.main.project_view_button.toggled.connect(self.main._set_left_panel_visibility)
        layout.addWidget(self.main.project_view_button)
        
        # Search button REMOVED (Moved to Translation Dock)
        
        layout.addStretch()
        
        self.main.activity_bar = activity_bar
        return activity_bar
    
    def build_left_panel(self) -> QWidget:
        """Build the left panel container with project tree."""
        # Container
        container = QWidget()
        container.setObjectName("leftPanelContainer")
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        container.setMinimumWidth(200)
        
        # Previously StackedLayout, now just VBox for project tree
        panel_layout = QVBoxLayout(container)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        
        # Project panel
        project_panel = QWidget()
        project_panel.setObjectName("projectPanel")
        project_layout = QVBoxLayout(project_panel)
        project_layout.setContentsMargins(5, 5, 5, 5)
        
        self.main.project_tree_view = QTreeView()
        self.main.project_tree_view.setHeaderHidden(True)
        self.main.project_tree_view.activated.connect(self.main._handle_tree_item_activated)
        project_layout.addWidget(self.main.project_tree_view)
        
        panel_layout.addWidget(project_panel)
        
        # No search panel here anymore
        
        # Defaults to visible? Or rely on saved state.
        # container.hide() # Let controller manage visibility
        
        self.main.left_panel_container = container
        self.main.project_panel = project_panel
        
        return container
        
    def build_search_panel(self) -> QWidget:
        """Build the search and replace panel widget (independent)."""
        search_panel = QWidget()
        search_panel.setObjectName("searchReplacePanel")
        search_layout = QVBoxLayout(search_panel)
        search_layout.setContentsMargins(5, 5, 5, 5)
        search_layout.setSpacing(5)
        
        # Search input
        search_layout.addWidget(QLabel(tr("toolbar_find")))
        self.main.search_input = QLineEdit()
        self.main.search_input.setPlaceholderText(tr("toolbar_search_placeholder"))
        search_layout.addWidget(self.main.search_input)
        
        # Replace input
        search_layout.addWidget(QLabel(tr("toolbar_replace_with")))
        self.main.replace_input = QLineEdit()
        self.main.replace_input.setPlaceholderText(tr("toolbar_replace_placeholder"))
        search_layout.addWidget(self.main.replace_input)
        
        # Options
        options_layout = QVBoxLayout()
        
        # Scope Selector
        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel(tr("search_scope_label")))
        self.main.search_scope_combo = QComboBox()
        self.main.search_scope_combo.addItem(tr("search_scope_visible"), "visible")
        self.main.search_scope_combo.addItem(tr("search_scope_all"), "all")
        scope_layout.addWidget(self.main.search_scope_combo)
        options_layout.addLayout(scope_layout)

        # Checkboxes
        checks_layout = QHBoxLayout()
        self.main.regex_checkbox = QCheckBox(tr("toolbar_regex"))
        self.main.regex_checkbox.setToolTip("Use regular expressions for search")
        checks_layout.addWidget(self.main.regex_checkbox)

        self.main.search_safe_mode_chk = QCheckBox(tr("search_safe_mode"))
        self.main.search_safe_mode_chk.setToolTip("Prevent breaking Ren'Py tokens")
        self.main.search_safe_mode_chk.setChecked(True)
        checks_layout.addWidget(self.main.search_safe_mode_chk)
        
        options_layout.addLayout(checks_layout)
        search_layout.addLayout(options_layout)
        
        # Match Info
        self.main.search_info_label = QLabel(tr("search_no_matches"))
        self.main.search_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main.search_info_label.setStyleSheet("color: gray; font-size: 11px;")
        search_layout.addWidget(self.main.search_info_label)

        # Buttons
        buttons_layout = QVBoxLayout()
        
        nav_layout = QHBoxLayout()
        # Find Prev
        self.main.find_prev_btn = QPushButton(tr("btn_find_prev"))
        self.main.find_prev_btn.setToolTip("Find previous occurrence")
        self.main.find_prev_btn.clicked.connect(lambda: action_handler.handle_find_prev(self.main)) 
        nav_layout.addWidget(self.main.find_prev_btn)
        
        # Find Next
        self.main.find_next_btn = QPushButton(tr("btn_find_next"))
        self.main.find_next_btn.setIcon(safe_icon("pics/find_next.svg"))
        self.main.find_next_btn.setToolTip("Find next occurrence")
        self.main.find_next_btn.clicked.connect(lambda: action_handler.handle_find_next(self.main))
        nav_layout.addWidget(self.main.find_next_btn)
        
        buttons_layout.addLayout(nav_layout)
        
        self.main.replace_btn = QPushButton(tr("btn_replace"))
        self.main.replace_btn.setIcon(safe_icon("pics/replace.svg"))
        self.main.replace_btn.setToolTip("Replace current and find next")
        self.main.replace_btn.clicked.connect(lambda: action_handler.handle_replace(self.main))
        buttons_layout.addWidget(self.main.replace_btn)
        
        self.main.replace_all_btn = QPushButton(tr("btn_replace_all"))
        self.main.replace_all_btn.setIcon(safe_icon("pics/replace.svg"))
        self.main.replace_all_btn.setToolTip("Replace all occurrences")
        self.main.replace_all_btn.clicked.connect(lambda: action_handler.handle_replace_all(self.main))
        buttons_layout.addWidget(self.main.replace_all_btn)
        
        search_layout.addLayout(buttons_layout)
        search_layout.addStretch()
        
        self.main.search_replace_panel = search_panel
        return search_panel
    
    def build_settings_group(self) -> QGroupBox:
        """Build the top settings toolbar group."""
        group = QGroupBox(tr("group_global_settings"))
        layout = QHBoxLayout(group)
        
        # Mode display
        self.main.mode_label = QLabel(tr("toolbar_mode"))
        self.main.mode_display_label = QLabel(tr("no_open_files"))
        self.main.mode_display_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.main.mode_label)
        layout.addWidget(self.main.mode_display_label)
        layout.addStretch(1)
        
        # Target language
        self.main.target_lang_label = QLabel(tr("toolbar_target"))
        self.main.target_lang_combo = QComboBox()
        self.main.target_lang_combo.setToolTip("Target translation language")
        
        # Source language
        self.main.source_lang_label = QLabel(tr("toolbar_source"))
        self.main.source_lang_combo = QComboBox()
        self.main.source_lang_combo.setToolTip("Original source language")
        
        # Populate languages
        if self.main.SUPPORTED_LANGUAGES:
            sorted_langs = sorted(self.main.SUPPORTED_LANGUAGES.items(), key=lambda x: x[1])
            for code, name in sorted_langs:
                self.main.source_lang_combo.addItem(name, code)
                self.main.target_lang_combo.addItem(name, code)
            
            src_idx = self.main.source_lang_combo.findData(self.main.source_language)
            self.main.source_lang_combo.setCurrentIndex(src_idx if src_idx != -1 else 0)
            tgt_idx = self.main.target_lang_combo.findData(self.main.target_language)
            self.main.target_lang_combo.setCurrentIndex(tgt_idx if tgt_idx != -1 else 0)
        else:
            self.main.source_lang_combo.addItem(f"{config.DEFAULT_SOURCE_LANG} (default)", config.DEFAULT_SOURCE_LANG)
            self.main.target_lang_combo.addItem(f"{config.DEFAULT_TARGET_LANG} (default)", config.DEFAULT_TARGET_LANG)
        
        self.main.target_lang_combo.currentIndexChanged.connect(
            lambda: settings_manager.handle_target_language_changed(self.main))
        self.main.source_lang_combo.currentIndexChanged.connect(
            lambda: settings_manager.handle_source_language_changed(self.main))
        
        layout.addWidget(self.main.target_lang_label)
        layout.addWidget(self.main.target_lang_combo)
        layout.addWidget(self.main.source_lang_label)
        layout.addWidget(self.main.source_lang_combo)
        layout.addStretch(1)
        
        # Model selection
        self.main.model_label = QLabel(tr("toolbar_model"))
        self.main.model_combo = QComboBox()
        self.main.model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.main.model_combo.setToolTip("Google Gemini model to use")
        self.main.model_combo.addItem("Loading models...")
        self.main.model_combo.setEnabled(False)
        self.main.model_combo.currentIndexChanged.connect(
            lambda: settings_manager.handle_model_changed(self.main))
        
        layout.addWidget(self.main.model_label)
        layout.addWidget(self.main.model_combo)
        
        return group
    
    def build_tab_widget(self) -> QTabWidget:
        """Build the main tab widget for file editing."""
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        tab_widget.setTabsClosable(True)
        tab_widget.setMovable(True)
        tab_widget.currentChanged.connect(lambda index: tab_manager.handle_tab_changed(self.main, index))
        tab_widget.tabCloseRequested.connect(lambda index: tab_manager.close_tab(self.main, index))
        tab_widget.tabBar().setExpanding(True)
        
        self.main.tab_widget = tab_widget
        return tab_widget
    
    def build_tools_group(self) -> QGroupBox:
        """Build the bottom tools and navigation group."""
        group = QGroupBox(tr("group_tools_nav"))
        main_layout = QVBoxLayout(group)
        main_layout.setSpacing(2)
        
        # Row 1: AI, Translate, Batch, Revert
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        # AI Edit button - ONLY emit signal, handler in app_bootstrap
        self.main.ai_edit_btn = QPushButton(tr("btn_ai"))
        self.main.ai_edit_btn.setIcon(safe_icon("pics/ai.svg"))
        self.main.ai_edit_btn.setToolTip("Edit selected line with Gemini")
        self.main.ai_edit_btn.clicked.connect(lambda: self.main.translate_ai_requested.emit())
        row1.addWidget(self.main.ai_edit_btn)
        
        # Google Translate button - ONLY emit signal, handler in app_bootstrap
        self.main.gt_translate_btn = QPushButton(tr("btn_gtranslate"))
        self.main.gt_translate_btn.setIcon(safe_icon("pics/gt.svg"))
        self.main.gt_translate_btn.setToolTip("Translate with Google Translate")
        self.main.gt_translate_btn.clicked.connect(lambda: self.main.translate_google_requested.emit())
        row1.addWidget(self.main.gt_translate_btn)
        
        # Batch Google Translate button - ONLY emit signal, handler in app_bootstrap
        self.main.batch_gt_btn = QPushButton(tr("btn_batch_gtranslate"))
        self.main.batch_gt_btn.setIcon(safe_icon("pics/batch.svg"))
        self.main.batch_gt_btn.setToolTip("Batch translate selected lines with Google")
        self.main.batch_gt_btn.clicked.connect(lambda: self.main.batch_google_requested.emit())
        row1.addWidget(self.main.batch_gt_btn)
        
        # Batch AI button - ONLY emit signal, handler in app_bootstrap
        self.main.batch_ai_btn = QPushButton(tr("btn_batch_ai"))
        self.main.batch_ai_btn.setIcon(safe_icon("pics/ai.svg"))
        self.main.batch_ai_btn.setToolTip("Batch translate selected lines with Gemini AI")
        self.main.batch_ai_btn.clicked.connect(lambda: self.main.batch_ai_requested.emit())
        row1.addWidget(self.main.batch_ai_btn)
        
        self.main.revert_btn = QPushButton(f"↶ {tr('btn_revert_row')}")
        self.main.revert_btn.setIcon(safe_icon("pics/revert.svg"))
        self.main.revert_btn.setToolTip(tr('tip_revert_row'))
        self.main.revert_btn.clicked.connect(lambda: table_manager.revert_selected_items(self.main))
        row1.addWidget(self.main.revert_btn)
        
        self.main.revert_all_btn = QPushButton(f"↺ {tr('btn_revert_all')}")
        self.main.revert_all_btn.setIcon(safe_icon("pics/revert_all.svg"))
        self.main.revert_all_btn.setToolTip(tr('tip_revert_all'))
        self.main.revert_all_btn.clicked.connect(lambda: table_manager.revert_all_items(self.main))
        row1.addWidget(self.main.revert_all_btn)
        
        row1.addStretch()
        main_layout.addLayout(row1)
        
        # Row 2: Markers, Direct mode actions
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.main.toggle_bp_btn = QPushButton(tr("btn_marker"))
        self.main.toggle_bp_btn.setIcon(safe_icon("pics/breakpoint.svg"))
        self.main.toggle_bp_btn.setToolTip(f"Set/unset marker ({config.BREAKPOINT_MARKER})")
        self.main.toggle_bp_btn.clicked.connect(lambda: action_handler.toggle_breakpoint(self.main))
        row2.addWidget(self.main.toggle_bp_btn)
        
        self.main.go_to_bp_btn = QPushButton(tr("btn_next_marker"))
        self.main.go_to_bp_btn.setIcon(safe_icon("pics/goto.svg"))
        self.main.go_to_bp_btn.setToolTip("Go to next marker")
        self.main.go_to_bp_btn.clicked.connect(lambda: action_handler.go_to_next_breakpoint(self.main))
        row2.addWidget(self.main.go_to_bp_btn)
        
        self.main.clear_bp_btn = QPushButton(tr("btn_clear_markers"))
        self.main.clear_bp_btn.setIcon(safe_icon("pics/breakpoint_clear.svg"))
        self.main.clear_bp_btn.setToolTip("Clear all markers")
        self.main.clear_bp_btn.clicked.connect(lambda: action_handler.clear_all_breakpoints(self.main))
        row2.addWidget(self.main.clear_bp_btn)
        
        row2.addStretch()
        
        row2.addWidget(QLabel(tr("mode_direct") + ":"))
        
        self.main.insert_btn = QPushButton(tr("btn_add"))
        self.main.insert_btn.setIcon(safe_icon("pics/add.svg"))
        self.main.insert_btn.setToolTip("Insert new line (direct mode)")
        self.main.insert_btn.clicked.connect(lambda: action_handler.insert_line(self.main))
        row2.addWidget(self.main.insert_btn)
        
        self.main.delete_btn = QPushButton(tr("btn_delete"))
        self.main.delete_btn.setIcon(safe_icon("pics/remove.svg"))
        self.main.delete_btn.setToolTip("Delete selected line (direct mode)")
        self.main.delete_btn.clicked.connect(lambda: action_handler.delete_line(self.main))
        row2.addWidget(self.main.delete_btn)
        
        main_layout.addLayout(row2)
        
        return group
    
    def build_main_content_area(self) -> QWidget:
        """Build the main content area with settings, tabs, and tools."""
        area = QWidget()
        area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.setMinimumWidth(400)
        layout = QVBoxLayout(area)
        layout.setContentsMargins(4, 0, 0, 0)
        
        # Layout Order: Toolbar -> Filter -> Tabs -> Settings (or Settings -> Toolbar?)
        # User requested: "Menubar on top, toolbar below, main content below."
        
        # 1. Tools (Toolbar)
        layout.addWidget(self.build_tools_group())
        
        # 2. Filter Toolbar (Stage 5)
        if hasattr(self.main, 'filter_toolbar'):
            layout.addWidget(self.main.filter_toolbar)
            self.main.filter_toolbar.show() # Ensure visible
            
        # 3. Main Content (Tabs)
        layout.addWidget(self.build_tab_widget(), 1)
        
        # 4. Settings (Bottom - less clutter at top)
        layout.addWidget(self.build_settings_group())
        
        return area
    
    def assemble_layout(self):
        """Assemble all UI components into the main window."""
        activity_bar = self.build_activity_bar()
        left_panel = self.build_left_panel()
        main_content = self.build_main_content_area()
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(main_content)
        splitter.setCollapsible(0, True)
        splitter.setCollapsible(1, False)
        splitter.handle(1).setDisabled(True)
        
        self.main.splitter = splitter
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(activity_bar)
        main_layout.addWidget(splitter)
        
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.main.setCentralWidget(central_widget)
        
        self.main.statusBar().showMessage(tr("ready"))
    
    def build_menu_bar(self):
        """Build the application menu bar."""
        menu_bar = self.main.menuBar()
        
        # =================================================================
        # FILE MENU - with signal emission for MVC architecture
        # =================================================================
        file_menu = menu_bar.addMenu(tr("menu_file"))
        
        # Open Project - ONLY emit signal, handler in app_bootstrap
        open_project = file_menu.addAction(tr("menu_open_project"))
        open_project.triggered.connect(lambda: self.main.open_project_requested.emit())
        self.main.open_project_action = open_project
        
        # Open File - ONLY emit signal, handler in app_bootstrap
        open_file = file_menu.addAction(tr("menu_open_file"))
        open_file.setShortcut("Ctrl+O")
        open_file.triggered.connect(lambda: self.main.open_file_requested.emit())
        
        file_menu.addSeparator()
        
        # Save - ONLY emit signal, controller handles the rest
        save = file_menu.addAction(tr("menu_save"))
        save.setShortcut("Ctrl+S")
        save.triggered.connect(lambda: self.main.save_requested.emit())
        self.main.save_action = save
        
        # Save As
        save_as = file_menu.addAction(tr("menu_save_as"))
        save_as.triggered.connect(lambda: file_manager.save_file_dialog(self.main))
        self.main.save_as_action = save_as
        
        # Save All - ONLY emit signal, controller handles the rest
        save_all = file_menu.addAction(tr("menu_save_all"))
        save_all.setShortcut("Ctrl+Shift+S")
        save_all.triggered.connect(lambda: self.main.save_all_requested.emit())
        self.main.save_all_action = save_all
        
        file_menu.addSeparator()
        
        # Close Tab - ONLY emit signal, controller handles the rest
        close_tab = file_menu.addAction(tr("menu_close_tab"))
        close_tab.setShortcut("Ctrl+W")
        def on_close_tab():
            idx = self.main.tab_widget.currentIndex()
            self.main.close_tab_requested.emit(idx)
        close_tab.triggered.connect(on_close_tab)
        self.main.close_tab_action = close_tab
        
        file_menu.addSeparator()
        
        # Packaging
        export_pack = file_menu.addAction(tr("menu_file_export_pack"))
        export_pack.triggered.connect(lambda: self.main._handle_export_pack())
        
        import_pack = file_menu.addAction(tr("menu_file_import_pack"))
        import_pack.triggered.connect(lambda: self.main._handle_import_pack())
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = file_menu.addAction(tr("menu_exit"))
        exit_action.setShortcut("Ctrl+Q")
        def on_exit():
            self.main.exit_requested.emit()  # Signal for controllers
            self.main.close()  # Actual close
        exit_action.triggered.connect(on_exit)
        
        # =================================================================
        # EDIT MENU - with signal emission for MVC architecture
        # =================================================================
        edit_menu = menu_bar.addMenu(tr("menu_edit"))
        
        revert = edit_menu.addAction(tr("menu_revert_item"))
        revert.setToolTip("Revert unsaved changes for selected line")
        revert.triggered.connect(lambda: table_manager.revert_single_item_menu(self.main))
        self.main.revert_action_menu = revert
        
        # AI Edit - ONLY emit signal, handler in app_bootstrap
        ai_edit = edit_menu.addAction(tr("menu_edit_ai"))
        ai_edit.triggered.connect(lambda: self.main.translate_ai_requested.emit())
        self.main.ai_edit_action_menu = ai_edit
        
        # Google Translate - ONLY emit signal, handler in app_bootstrap
        gt = edit_menu.addAction(tr("menu_translate_google"))
        gt.triggered.connect(lambda: self.main.translate_google_requested.emit())
        self.main.gt_action_menu = gt
        
        # Navigation menu
        nav_menu = menu_bar.addMenu(tr("menu_navigation"))
        
        prev_item = nav_menu.addAction(tr("menu_prev_item"))
        prev_item.setShortcut("Ctrl+Up")
        prev_item.triggered.connect(lambda: action_handler.navigate_prev(self.main))
        self.main.prev_action = prev_item
        
        next_item = nav_menu.addAction(tr("menu_next_item"))
        next_item.setShortcut("Ctrl+Down")
        next_item.triggered.connect(lambda: action_handler.navigate_next(self.main))
        self.main.next_action = next_item
        
        nav_menu.addSeparator()
        
        next_bp = nav_menu.addAction(tr("menu_next_breakpoint"))
        next_bp.setShortcut("F2")
        next_bp.triggered.connect(lambda: action_handler.go_to_next_breakpoint(self.main))
        self.main.next_bp_action = next_bp
        
        # Tools menu
        tools_menu = menu_bar.addMenu(tr("menu_tools"))
        
        toggle_bp = tools_menu.addAction(tr("menu_toggle_marker"))
        toggle_bp.setShortcut("F3")
        toggle_bp.triggered.connect(lambda: action_handler.toggle_breakpoint(self.main))
        self.main.toggle_bp_action_menu = toggle_bp
        
        clear_bp = tools_menu.addAction(tr("menu_clear_markers"))
        clear_bp.triggered.connect(lambda: action_handler.clear_all_breakpoints(self.main))
        self.main.clear_bp_action_menu = clear_bp
        
        tools_menu.addSeparator()
        
        insert = tools_menu.addAction(tr("menu_insert_line"))
        insert.triggered.connect(lambda: action_handler.insert_line(self.main))
        self.main.insert_action_menu = insert
        
        delete = tools_menu.addAction(tr("menu_delete_line"))
        delete.triggered.connect(lambda: action_handler.delete_line(self.main))
        self.main.delete_action_menu = delete
        
        # Settings menu
        settings_menu = menu_bar.addMenu(tr("menu_settings"))
        
        general = settings_menu.addAction(tr("menu_settings_general"))
        general.triggered.connect(lambda: settings_manager.show_settings_dialog(self.main))
        
        api_key = settings_menu.addAction(tr("menu_settings_apikey"))
        def safe_show_api():
            try:
                settings_manager.show_api_key_dialog(self.main)
            except Exception as e:
                QMessageBox.critical(self.main, tr("error"), f"API Dialog Error: {e}")
        api_key.triggered.connect(safe_show_api)
        
        # View menu
        view_menu = menu_bar.addMenu(tr("menu_view"))
        
        toggle_project = view_menu.addAction(tr("menu_view_project"))
        toggle_project.setCheckable(True)
        toggle_project.setChecked(False)
        toggle_project.triggered.connect(self.main.project_view_button.click)
        self.main.project_view_button.toggled.connect(toggle_project.setChecked)
        self.main.toggle_project_panel_action = toggle_project
        
        view_menu.addSeparator()
        
        # Workspace Menu (Stage 14)
        workspace_menu = view_menu.addMenu(tr("workspace_settings")) # Reusing key or new one
        
        # Reset Layout
        reset_layout = workspace_menu.addAction("Reset Layout") # Transform to tr key later if needed
        def reset_workspace():
             # Basic reset logic or restore default sizes
             self.main.restoreState(self.main.settings.get("window_state", b""))
             # Ensure docks are tabified if reset breaks it? 
             # For now, just a placeholder or simple state restore if we had a default state.
             pass
        # reset_layout.triggered.connect(reset_workspace) 
        
        # Shortcuts for Docks
        # We add them as hidden actions to the main window or view menu to enable shortcuts
        dock_actions = [
            (self.main.workspace_docks['translation'], "Ctrl+1"),
            (self.main.workspace_docks['review'], "Ctrl+2"),
            (self.main.workspace_docks['quality'], "Ctrl+3"),
            (self.main.workspace_docks['consistency'], "Ctrl+4"),
            (self.main.workspace_docks['settings'], "Ctrl+5"),
        ]
        
        for dock, shortcut in dock_actions:
            action = view_menu.addAction(dock.windowTitle())
            action.setShortcut(shortcut)
            # Create a closure to capture 'dock' correctly
            def make_trigger(d):
                return lambda: d.raise_()
            action.triggered.connect(make_trigger(dock))
            
            # Also valid to just toggle visibility? Tabbed docks are usually always visible as a group.
            # But the dock itself might be hidden. 
            # Ideally: Ensure Right Dock Area is visible, then raise the dock.

        
        # Stage 6: Glossary View Toggle
        view_menu.addSeparator()
        if hasattr(self.main, 'glossary_panel'):
            toggle_glossary = view_menu.addAction(tr("glossary_title"))
            toggle_glossary.setCheckable(True)
            toggle_glossary.setChecked(False)
            toggle_glossary.triggered.connect(lambda checked: self.main.glossary_panel.setVisible(checked))
            # Sync check state when panel is closed via X/dock
            self.main.glossary_panel.visibilityChanged.connect(toggle_glossary.setChecked)
        
        # Help menu
        help_menu = menu_bar.addMenu(tr("menu_help"))
        about = help_menu.addAction(tr("menu_about"))
        about.triggered.connect(self.main._show_about)
