# -*- coding: utf-8 -*-
"""
RenForge UI Builder
Responsible for creating all UI widgets and layouts for the main window.
"""

from renforge_logger import get_logger
logger = get_logger("gui.ui_builder")

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTabWidget, QGroupBox, QCheckBox, QSplitter, QSizePolicy,
    QToolButton, QStackedLayout, QTreeView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

import renforge_config as config
from locales import tr

# These will be imported by the main window and passed to handlers
import gui.gui_file_manager as file_manager
import gui.gui_tab_manager as tab_manager
import gui.gui_table_manager as table_manager
import gui.gui_action_handler as action_handler
import gui.gui_settings_manager as settings_manager


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
        self.main.project_view_button.setIcon(QIcon(config.resource_path("pics/project.svg")))
        self.main.project_view_button.setToolTip("Show/hide project panel")
        self.main.project_view_button.setCheckable(True)
        self.main.project_view_button.setChecked(False)
        self.main.project_view_button.toggled.connect(self.main._handle_activity_bar_toggle)
        layout.addWidget(self.main.project_view_button)
        
        # Search view button
        self.main.search_view_button = QToolButton()
        self.main.search_view_button.setObjectName("searchViewButton")
        self.main.search_view_button.setIcon(QIcon(config.resource_path("pics/search.svg")))
        self.main.search_view_button.setToolTip("Show/hide search and replace panel")
        self.main.search_view_button.setCheckable(True)
        self.main.search_view_button.setChecked(False)
        self.main.search_view_button.toggled.connect(self.main._handle_activity_bar_toggle)
        layout.addWidget(self.main.search_view_button)
        
        layout.addStretch()
        
        self.main.activity_bar = activity_bar
        return activity_bar
    
    def build_left_panel(self) -> QWidget:
        """Build the left panel container with project tree and search/replace panel."""
        # Container
        container = QWidget()
        container.setObjectName("leftPanelContainer")
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        container.setMinimumWidth(200)
        
        panel_layout = QStackedLayout(container)
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
        
        # Search/Replace panel
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
        options_layout = QHBoxLayout()
        self.main.regex_checkbox = QCheckBox(tr("toolbar_regex"))
        self.main.regex_checkbox.setToolTip("Use regular expressions for search")
        options_layout.addWidget(self.main.regex_checkbox)
        options_layout.addStretch()
        search_layout.addLayout(options_layout)
        
        # Buttons
        buttons_layout = QVBoxLayout()
        
        self.main.find_next_btn = QPushButton(tr("btn_find_next"))
        self.main.find_next_btn.setIcon(QIcon(config.resource_path("pics/find_next.svg")))
        self.main.find_next_btn.setToolTip("Find next occurrence")
        self.main.find_next_btn.clicked.connect(lambda: action_handler.handle_find_next(self.main))
        buttons_layout.addWidget(self.main.find_next_btn)
        
        self.main.replace_btn = QPushButton(tr("btn_replace"))
        self.main.replace_btn.setIcon(QIcon(config.resource_path("pics/replace.svg")))
        self.main.replace_btn.setToolTip("Replace current and find next")
        self.main.replace_btn.clicked.connect(lambda: action_handler.handle_replace(self.main))
        buttons_layout.addWidget(self.main.replace_btn)
        
        self.main.replace_all_btn = QPushButton(tr("btn_replace_all"))
        self.main.replace_all_btn.setIcon(QIcon(config.resource_path("pics/replace.svg")))
        self.main.replace_all_btn.setToolTip("Replace all occurrences")
        self.main.replace_all_btn.clicked.connect(lambda: action_handler.handle_replace_all(self.main))
        buttons_layout.addWidget(self.main.replace_all_btn)
        
        search_layout.addLayout(buttons_layout)
        search_layout.addStretch()
        
        panel_layout.addWidget(search_panel)
        
        container.hide()
        
        self.main.left_panel_container = container
        self.main.left_panel_layout = panel_layout
        self.main.project_panel = project_panel
        self.main.search_replace_panel = search_panel
        
        return container
    
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
        
        self.main.ai_edit_btn = QPushButton(tr("btn_ai"))
        self.main.ai_edit_btn.setIcon(QIcon(config.resource_path("pics/ai.svg")))
        self.main.ai_edit_btn.setToolTip("Edit selected line with Gemini")
        self.main.ai_edit_btn.clicked.connect(lambda: action_handler.edit_with_ai(self.main))
        row1.addWidget(self.main.ai_edit_btn)
        
        self.main.gt_translate_btn = QPushButton(tr("btn_gtranslate"))
        self.main.gt_translate_btn.setIcon(QIcon(config.resource_path("pics/gt.svg")))
        self.main.gt_translate_btn.setToolTip("Translate with Google Translate")
        self.main.gt_translate_btn.clicked.connect(lambda: action_handler.translate_with_google(self.main))
        row1.addWidget(self.main.gt_translate_btn)
        
        self.main.batch_gt_btn = QPushButton(tr("btn_batch_gtranslate"))
        self.main.batch_gt_btn.setIcon(QIcon(config.resource_path("pics/batch.svg")))
        self.main.batch_gt_btn.setToolTip("Batch translate selected lines")
        self.main.batch_gt_btn.clicked.connect(lambda: action_handler.batch_translate_google(self.main))
        row1.addWidget(self.main.batch_gt_btn)
        
        self.main.revert_btn = QPushButton(tr("btn_revert"))
        self.main.revert_btn.setIcon(QIcon(config.resource_path("pics/revert.svg")))
        self.main.revert_btn.setToolTip("Revert selected lines")
        self.main.revert_btn.clicked.connect(lambda: table_manager.revert_selected_items(self.main))
        row1.addWidget(self.main.revert_btn)
        
        self.main.revert_all_btn = QPushButton(tr("btn_revert_all"))
        self.main.revert_all_btn.setIcon(QIcon(config.resource_path("pics/revert_all.svg")))
        self.main.revert_all_btn.setToolTip("Revert all unsaved changes")
        self.main.revert_all_btn.clicked.connect(lambda: table_manager.revert_all_items(self.main))
        row1.addWidget(self.main.revert_all_btn)
        
        row1.addStretch()
        main_layout.addLayout(row1)
        
        # Row 2: Markers, Direct mode actions
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.main.toggle_bp_btn = QPushButton(tr("btn_marker"))
        self.main.toggle_bp_btn.setIcon(QIcon(config.resource_path("pics/breakpoint.svg")))
        self.main.toggle_bp_btn.setToolTip(f"Set/unset marker ({config.BREAKPOINT_MARKER})")
        self.main.toggle_bp_btn.clicked.connect(lambda: action_handler.toggle_breakpoint(self.main))
        row2.addWidget(self.main.toggle_bp_btn)
        
        self.main.go_to_bp_btn = QPushButton(tr("btn_next_marker"))
        self.main.go_to_bp_btn.setIcon(QIcon(config.resource_path("pics/goto.svg")))
        self.main.go_to_bp_btn.setToolTip("Go to next marker")
        self.main.go_to_bp_btn.clicked.connect(lambda: action_handler.go_to_next_breakpoint(self.main))
        row2.addWidget(self.main.go_to_bp_btn)
        
        self.main.clear_bp_btn = QPushButton(tr("btn_clear_markers"))
        self.main.clear_bp_btn.setIcon(QIcon(config.resource_path("pics/breakpoint_clear.svg")))
        self.main.clear_bp_btn.setToolTip("Clear all markers")
        self.main.clear_bp_btn.clicked.connect(lambda: action_handler.clear_all_breakpoints(self.main))
        row2.addWidget(self.main.clear_bp_btn)
        
        row2.addStretch()
        
        row2.addWidget(QLabel(tr("mode_direct") + ":"))
        
        self.main.insert_btn = QPushButton(tr("btn_add"))
        self.main.insert_btn.setIcon(QIcon(config.resource_path("pics/add.svg")))
        self.main.insert_btn.setToolTip("Insert new line (direct mode)")
        self.main.insert_btn.clicked.connect(lambda: action_handler.insert_line(self.main))
        row2.addWidget(self.main.insert_btn)
        
        self.main.delete_btn = QPushButton(tr("btn_delete"))
        self.main.delete_btn.setIcon(QIcon(config.resource_path("pics/remove.svg")))
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
        
        layout.addWidget(self.build_settings_group())
        layout.addWidget(self.build_tab_widget(), 1)
        layout.addWidget(self.build_tools_group())
        
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
        
        # File menu
        file_menu = menu_bar.addMenu(tr("menu_file"))
        
        open_project = file_menu.addAction(tr("menu_open_project"))
        open_project.triggered.connect(self.main._handle_open_project)
        self.main.open_project_action = open_project
        
        open_file = file_menu.addAction(tr("menu_open_file"))
        open_file.setShortcut("Ctrl+O")
        open_file.triggered.connect(lambda: file_manager.open_file_dialog(self.main))
        
        file_menu.addSeparator()
        
        save = file_menu.addAction(tr("menu_save"))
        save.setShortcut("Ctrl+S")
        save.triggered.connect(lambda: file_manager.save_changes(self.main))
        self.main.save_action = save
        
        save_as = file_menu.addAction(tr("menu_save_as"))
        save_as.triggered.connect(lambda: file_manager.save_file_dialog(self.main))
        self.main.save_as_action = save_as
        
        save_all = file_menu.addAction(tr("menu_save_all"))
        save_all.setShortcut("Ctrl+Shift+S")
        save_all.triggered.connect(lambda: file_manager.save_all_files(self.main))
        self.main.save_all_action = save_all
        
        file_menu.addSeparator()
        
        close_tab = file_menu.addAction(tr("menu_close_tab"))
        close_tab.setShortcut("Ctrl+W")
        close_tab.triggered.connect(lambda: tab_manager.close_current_tab(self.main))
        self.main.close_tab_action = close_tab
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction(tr("menu_exit"))
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.main.close)
        
        # Edit menu
        edit_menu = menu_bar.addMenu(tr("menu_edit"))
        
        revert = edit_menu.addAction(tr("menu_revert_item"))
        revert.setToolTip("Revert unsaved changes for selected line")
        revert.triggered.connect(lambda: table_manager.revert_single_item_menu(self.main))
        self.main.revert_action_menu = revert
        
        ai_edit = edit_menu.addAction(tr("menu_edit_ai"))
        ai_edit.triggered.connect(lambda: action_handler.edit_with_ai(self.main))
        self.main.ai_edit_action_menu = ai_edit
        
        gt = edit_menu.addAction(tr("menu_translate_google"))
        gt.triggered.connect(lambda: action_handler.translate_with_google(self.main))
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
        
        toggle_search = view_menu.addAction(tr("menu_view_search"))
        toggle_search.setCheckable(True)
        toggle_search.setChecked(False)
        toggle_search.triggered.connect(self.main.search_view_button.click)
        self.main.search_view_button.toggled.connect(toggle_search.setChecked)
        self.main.toggle_search_panel_action = toggle_search
        
        # Help menu
        help_menu = menu_bar.addMenu(tr("menu_help"))
        about = help_menu.addAction(tr("menu_about"))
        about.triggered.connect(self.main._show_about)
