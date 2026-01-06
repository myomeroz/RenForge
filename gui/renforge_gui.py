import sys
import os
import gc 
import time

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QComboBox, QFileDialog, QTextEdit,
                              QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                              QSplitter, QLineEdit,
                              QMessageBox, QTabWidget, QGroupBox, QRadioButton, QCheckBox,
                              QGridLayout, QDialog, QDialogButtonBox, QScrollArea, QFrame,
                              QProgressDialog, QSizePolicy, QTabBar,
                              QTreeView, QDockWidget, QToolButton,
                              QButtonGroup, QStackedLayout) 
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, pyqtSlot, QDir
    from PyQt6.QtGui import QFont, QColor, QIcon, QTextCursor, QFileSystemModel 
    GUI_AVAILABLE = True
except ImportError:
    print("CRITICAL ERROR: PyQt6 is required for the GUI but not found.")
    print("Please install it: pip install PyQt6")
    GUI_AVAILABLE = False
    sys.exit(1)

try:

    import renforge_config as config
    import renforge_core as core
    import renforge_ai as ai 
    import renforge_parser as parser
    from renforge_settings import save_settings
    from locales import tr 

    from gui.renforge_gui_dialog import (AIEditDialog, GoogleTranslateDialog, ApiKeyDialog,
                                       ModeSelectionDialog, InsertLineDialog, SettingsDialog)
    from gui.renforge_gui_styles import DARK_STYLE_SHEET

    import gui.gui_file_manager as file_manager
    import gui.gui_tab_manager as tab_manager
    import gui.gui_table_manager as table_manager
    import gui.gui_action_handler as action_handler
    import gui.gui_settings_manager as settings_manager
    import gui.gui_status_updater as status_updater

except ImportError as e:
     print(f"CRITICAL ERROR: Failed to import required renforge modules or GUI managers: {e}")
     try:
          if QApplication.instance():
               QMessageBox.critical(None, "Module Import Error",
                                    f"Failed to import necessary RenForge modules or GUI managers:\n{e}\n\n"
                                    "Ensure all files (*.py, gui/*.py) are in the correct locations.")
     except Exception as msg_e:
          print(f"Could not show GUI error message: {msg_e}")
     sys.exit(1)

SUPPORTED_LANGUAGES = {}

class RenForgeGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title", version=config.VERSION))

        self.resize(1200, 800)

        self.current_file_path = None 
        self.current_project_path = None 
        self.file_data = {} 
        self.tab_data = {}  
        self.settings = {}  
        self.last_open_directory = None 
        self.last_open_project_directory = None 
        self.activity_bar_group = None 
        self.left_panel_container = None 
        self.project_panel = None      
        self.search_replace_panel = None 
        self.left_panel_layout = None 

        self.search_input = None
        self.replace_input = None
        self.regex_checkbox = None

        self._batch_errors = []
        self._batch_warnings = []
        self._batch_total_processed = 0
        self._batch_success_count = 0

        self.SUPPORTED_LANGUAGES = {} 

        settings_manager.load_initial_settings(self)

        self._restore_window_geometry() 

        self.target_language = self.settings.get("default_target_language", config.DEFAULT_TARGET_LANG)
        self.source_language = self.settings.get("default_source_language", config.DEFAULT_SOURCE_LANG)
        self.selected_model = self.settings.get("default_selected_model", config.DEFAULT_MODEL_NAME) 

        self.file_is_loaded = False 
        self._block_item_changed_signal = False 

        self._load_languages()

        self.file_system_model = QFileSystemModel()

        self._create_ui() 
        self._create_menu() 
        self.setStyleSheet(DARK_STYLE_SHEET)
        self._update_ui_state() 

        QTimer.singleShot(100, self._perform_initial_checks) 

    def _restore_window_geometry(self):

        width = self.settings.get("window_size_w", 1200)
        height = self.settings.get("window_size_h", 800)
        is_maximized = self.settings.get("window_maximized", False)

        self.resize(width, height)

        if is_maximized:
            QTimer.singleShot(0, self.showMaximized)

    def _clear_batch_results(self):

        self._batch_errors = []
        self._batch_warnings = []
        self._batch_total_processed = 0
        self._batch_success_count = 0

    @pyqtSlot(int, str, dict)
    def _handle_batch_item_updated(self, item_index, translated_text, updated_item_data_copy):

        current_file_data = self._get_current_file_data()
        if not current_file_data: return

        current_items = current_file_data.get('items')
        current_lines = current_file_data.get('lines')
        current_mode = current_file_data.get('mode')
        table_widget = current_file_data.get('table_widget')

        if not table_widget or not current_items or not current_lines or not current_mode: return
        if not (0 <= item_index < len(current_items)): return

        original_item_data = current_items[item_index]
        text_key = 'translated_text' if current_mode == 'translate' else 'current_text'
        original_item_data[text_key] = translated_text
        original_item_data['is_modified_session'] = True 

        table_manager.update_table_item_text(self, table_widget, item_index, 4, translated_text)

        table_manager.update_table_row_style(table_widget, item_index, original_item_data)

        update_line_error = False
        if current_mode == 'translate':
            line_index_to_update = original_item_data.get('translated_line_index')
            parsed_data_from_signal = updated_item_data_copy.get('parsed_data')

            if line_index_to_update is not None and 0 <= line_index_to_update < len(current_lines):
                 if parsed_data_from_signal: 

                      new_line = parser.format_line_from_components(updated_item_data_copy, translated_text)
                      if new_line is not None:
                          current_lines[line_index_to_update] = new_line

                      else:
                          update_line_error = True
                          print(f"ERROR: Failed to format line for file index {line_index_to_update}")
                 else:
                     update_line_error = True

                     print(f"ERROR: Missing 'parsed_data' in data received from worker for item {item_index} (line {line_index_to_update})")
            else:
                 update_line_error = True 
                 print(f"ERROR: Invalid line index {line_index_to_update} for item {item_index}")

            if update_line_error:

                 err_detail = f"- Error updating file line {line_index_to_update+1} for item {item_index+1}"
                 self._batch_errors.append(err_detail)

        else:

            pass

    @pyqtSlot(str)
    def _handle_batch_translate_error(self, details):

        self._batch_errors.append(details)

    @pyqtSlot(str)
    def _handle_batch_translate_warning(self, details):

        self._batch_warnings.append(details)

    @pyqtSlot()
    def _mark_tab_modified_from_worker(self):

        self._set_current_tab_modified(True)

    @pyqtSlot(dict)
    def _handle_batch_translate_finished(self, results):

        processed = results['processed']
        total = results['total']
        success = results['success']
        errors = results['errors'] + len(self._batch_errors) 
        warnings = results['warnings']
        made_changes = results['made_changes']
        canceled = results['canceled']

        summary_msg = f"Batch translation finished.\n\n"
        if canceled:
             summary_msg += f"TASK CANCELED BY USER\n\n"
        summary_msg += f"Lines processed: {processed}/{total}\n"
        summary_msg += f"Successful (text updated): {success}\n" 

        if self._batch_errors:
             errors = len(self._batch_errors) 
             summary_msg += f"\nTranslation/Update Errors: {errors}\n"
             summary_msg += "\nError Details (max 10):\n" + "\n".join(self._batch_errors[:10])
             if len(self._batch_errors) > 10: summary_msg += "\n..."

        if self._batch_warnings:
            warnings = len(self._batch_warnings) 
            summary_msg += f"\nWarnings (variables '[...]'): {warnings}\n"
            summary_msg += "\nDetails (max 10):\n" + "\n".join(self._batch_warnings[:10])
            if len(self._batch_warnings) > 10: summary_msg += "\n..."

        QMessageBox.information(self, tr("batch_result_title"), summary_msg)

        if made_changes and not canceled: 
            self._set_current_tab_modified(True) 

        status_message = "Batch translation finished."
        if canceled:
            status_message = "Batch translation canceled."
        elif errors > 0 or warnings > 0:
            status_message += " Completed with errors/warnings."

        self.statusBar().showMessage(status_message, 5000)

        self._update_ui_state()

    def _perform_initial_checks(self):

        print("--- Performing initial checks ---")

        settings_manager.check_initial_mode_setting(self)

        print("--- Triggering initial Gemini check/initialization ---")

        QTimer.singleShot(50, lambda: settings_manager.ensure_gemini_initialized(self))
        print("--- Initial checks finished ---")
        QTimer.singleShot(200, self._sync_model_selection) 

    def _sync_model_selection(self):

        print("--- [_sync_model_selection] Attempting to sync model selection... ---")
        current_selection = self.model_combo.currentText()
        if current_selection in ["Loading...", "Error loading models"]:
             print(f"--- [_sync_model_selection] Skipping sync due to placeholder: '{current_selection}' ---")
             return
        default_model = self.settings.get("default_selected_model")

        if not default_model:
            print("--- [_sync_model_selection] No default model set in settings. Skipping sync. ---")

            if self.selected_model != current_selection:
                 print(f"--- [_sync_model_selection] Updating self.selected_model to combo box value: '{current_selection}' ---")
                 self.selected_model = current_selection if current_selection not in ["Loading...", "Error loading models", "Models not found", "None"] else None
            return

        if current_selection == default_model:
            print(f"--- [_sync_model_selection] Default model '{default_model}' already selected. Sync not needed. ---")

            if self.selected_model != default_model:
                 print(f"--- [_sync_model_selection] Correcting self.selected_model to '{default_model}' ---")
                 self.selected_model = default_model
            return

        model_index = self.model_combo.findText(default_model)

        if model_index != -1:
            print(f"--- [_sync_model_selection] Found default model '{default_model}' at index {model_index}. Setting selection. ---")
            self.model_combo.blockSignals(True) 
            self.model_combo.setCurrentIndex(model_index)
            self.selected_model = default_model 
            self.model_combo.blockSignals(False) 

            self._update_ui_state()
        else:
            print(f"--- [_sync_model_selection] Default model '{default_model}' not found in the current list. Cannot sync. Current selection: '{current_selection}'. ---")

            if self.selected_model != current_selection:
                 print(f"--- [_sync_model_selection] Updating self.selected_model to combo box value: '{current_selection}' ---")
                 self.selected_model = current_selection if current_selection not in ["Loading...", "Error loading models", "Models not found", "None"] else None

    def _load_languages(self):

        temp_languages = ai.get_google_languages() 
        if temp_languages:
             self.SUPPORTED_LANGUAGES = temp_languages
             print(f"DEBUG: Loaded {len(self.SUPPORTED_LANGUAGES)} languages. Example: {list(self.SUPPORTED_LANGUAGES.items())[:5]}") 
        else:
             print("Warning: Could not load supported languages for Google Translate.")
             self.SUPPORTED_LANGUAGES = {} 

    def _create_ui(self):

        self.activity_bar = QWidget()
        self.activity_bar.setObjectName("activityBar") 
        activity_bar_layout = QVBoxLayout(self.activity_bar)
        activity_bar_layout.setContentsMargins(2, 5, 2, 5) 
        activity_bar_layout.setSpacing(5) 

        self.project_view_button = QToolButton()
        self.project_view_button.setObjectName("projectViewButton")
        self.project_view_button.setIcon(QIcon(config.resource_path("pics/project.svg")))
        self.project_view_button.setToolTip("Show/hide project panel")
        self.project_view_button.setCheckable(True)
        self.project_view_button.setChecked(False) 
        self.project_view_button.toggled.connect(self._handle_activity_bar_toggle) 
        activity_bar_layout.addWidget(self.project_view_button)

        self.search_view_button = QToolButton()
        self.search_view_button.setObjectName("searchViewButton")

        self.search_view_button.setIcon(QIcon(config.resource_path("pics/search.svg"))) 
        self.search_view_button.setToolTip("Show/hide search and replace panel")
        self.search_view_button.setCheckable(True)
        self.search_view_button.setChecked(False) 
        self.search_view_button.toggled.connect(self._handle_activity_bar_toggle) 
        activity_bar_layout.addWidget(self.search_view_button)

        activity_bar_layout.addStretch() 

        self.left_panel_container = QWidget()
        self.left_panel_container.setObjectName("leftPanelContainer")
        self.left_panel_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.left_panel_container.setMinimumWidth(200) 
        self.left_panel_layout = QStackedLayout(self.left_panel_container)
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.project_panel = QWidget()
        self.project_panel.setObjectName("projectPanel")
        project_panel_layout = QVBoxLayout(self.project_panel)
        project_panel_layout.setContentsMargins(5, 5, 5, 5) 

        self.project_tree_view = QTreeView()
        self.project_tree_view.setHeaderHidden(True)
        self.project_tree_view.activated.connect(self._handle_tree_item_activated)
        project_panel_layout.addWidget(self.project_tree_view)

        self.left_panel_layout.addWidget(self.project_panel)

        self.search_replace_panel = QWidget()
        self.search_replace_panel.setObjectName("searchReplacePanel")
        search_replace_layout = QVBoxLayout(self.search_replace_panel)
        search_replace_layout.setContentsMargins(5, 5, 5, 5) 
        search_replace_layout.setSpacing(5)

        search_label = QLabel(tr("toolbar_find"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("toolbar_search_placeholder"))
        replace_label = QLabel(tr("toolbar_replace_with"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(tr("toolbar_replace_placeholder"))

        search_options_layout = QHBoxLayout() 
        self.regex_checkbox = QCheckBox(tr("toolbar_regex"))
        self.regex_checkbox.setToolTip("Use regular expressions for search (affects 'Find', 'Replace', 'Replace All')")

        search_options_layout.addWidget(self.regex_checkbox)
        search_options_layout.addStretch() 

        search_buttons_layout = QVBoxLayout()
        self.find_next_btn = QPushButton(tr("btn_find_next"))
        self.find_next_btn.setIcon(QIcon(config.resource_path("pics/find_next.svg"))) 
        self.find_next_btn.setToolTip("Find next occurrence")
        self.find_next_btn.clicked.connect(lambda: action_handler.handle_find_next(self))
        self.replace_btn = QPushButton(tr("btn_replace"))
        self.replace_btn.setIcon(QIcon(config.resource_path("pics/replace.svg"))) 
        self.replace_btn.setToolTip("Replace current found occurrence and find next")
        self.replace_btn.clicked.connect(lambda: action_handler.handle_replace(self))
        self.replace_all_btn = QPushButton(tr("btn_replace_all"))
        self.replace_all_btn.setIcon(QIcon(config.resource_path("pics/replace.svg"))) 
        self.replace_all_btn.setToolTip("Replace all occurrences in the current file")
        self.replace_all_btn.clicked.connect(lambda: action_handler.handle_replace_all(self))
        search_buttons_layout.addWidget(self.find_next_btn)
        search_buttons_layout.addWidget(self.replace_btn)
        search_buttons_layout.addWidget(self.replace_all_btn)

        search_replace_layout.addWidget(search_label)
        search_replace_layout.addWidget(self.search_input)
        search_replace_layout.addWidget(replace_label)
        search_replace_layout.addWidget(self.replace_input)
        search_replace_layout.addLayout(search_options_layout)
        search_replace_layout.addLayout(search_buttons_layout)
        search_replace_layout.addStretch() 

        self.left_panel_layout.addWidget(self.search_replace_panel)

        self.left_panel_container.hide()

        main_content_area = QWidget()
        main_content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_content_area.setMinimumWidth(400)
        main_content_layout = QVBoxLayout(main_content_area)
        main_content_layout.setContentsMargins(4, 0, 0, 0) 

        settings_group = QGroupBox(tr("group_global_settings"))
        settings_layout = QHBoxLayout(settings_group)

        self.mode_label = QLabel(tr("toolbar_mode"))
        self.mode_display_label = QLabel(tr("no_open_files"))
        self.mode_display_label.setStyleSheet("font-weight: bold;")
        settings_layout.addWidget(self.mode_label)
        settings_layout.addWidget(self.mode_display_label)
        settings_layout.addStretch(1)

        self.target_lang_label = QLabel(tr("toolbar_target"))
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.setToolTip("Target translation language (e.g., 'Russian')\nUsed for 'translate' and as a hint for AI/GTranslate.")
        self.source_lang_label = QLabel(tr("toolbar_source"))
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.setToolTip("Original source language (e.g., 'English', 'Japanese')\nUsed for 'translate' and as a hint for AI/GTranslate.")

        if self.SUPPORTED_LANGUAGES: 
             sorted_languages = sorted(self.SUPPORTED_LANGUAGES.items(), key=lambda item: item[1])
             for code, name in sorted_languages:
                  self.source_lang_combo.addItem(name, code)
                  self.target_lang_combo.addItem(name, code)

             source_idx = self.source_lang_combo.findData(self.source_language)
             self.source_lang_combo.setCurrentIndex(source_idx if source_idx != -1 else 0)
             target_idx = self.target_lang_combo.findData(self.target_language)
             self.target_lang_combo.setCurrentIndex(target_idx if target_idx != -1 else 0)
        else:

             self.source_lang_combo.addItem(f"{config.DEFAULT_SOURCE_LANG} (default)", config.DEFAULT_SOURCE_LANG)
             self.target_lang_combo.addItem(f"{config.DEFAULT_TARGET_LANG} (default)", config.DEFAULT_TARGET_LANG)

        self.target_lang_combo.currentIndexChanged.connect(lambda: settings_manager.handle_target_language_changed(self))

        self.source_lang_combo.currentIndexChanged.connect(lambda: settings_manager.handle_source_language_changed(self))
        settings_layout.addWidget(self.target_lang_label)
        settings_layout.addWidget(self.target_lang_combo)
        settings_layout.addWidget(self.source_lang_label)
        settings_layout.addWidget(self.source_lang_combo)
        settings_layout.addStretch(1)

        self.model_label = QLabel(tr("toolbar_model"))
        self.model_combo = QComboBox()

        self.model_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.model_combo.setToolTip("Google Gemini model to use.\nList loads after API key setup.")
        self.model_combo.addItem("Loading models...") 
        self.model_combo.setEnabled(False) 

        self.model_combo.currentIndexChanged.connect(lambda: settings_manager.handle_model_changed(self))
        settings_layout.addWidget(self.model_label)
        settings_layout.addWidget(self.model_combo)

        main_content_layout.addWidget(settings_group) 

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True) 
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)

        self.tab_widget.currentChanged.connect(lambda index: tab_manager.handle_tab_changed(self, index))
        self.tab_widget.tabCloseRequested.connect(lambda index: tab_manager.close_tab(self, index))

        self.tab_widget.tabBar().setExpanding(True) 

        main_content_layout.addWidget(self.tab_widget, 1) 

        tools_group = QGroupBox(tr("group_tools_nav"))
        tools_main_layout = QVBoxLayout(tools_group)
        tools_main_layout.setSpacing(2) 

        buttons_layout_row1 = QHBoxLayout()
        buttons_layout_row1.setSpacing(4) 

        self.ai_edit_btn = QPushButton(tr("btn_ai"))
        self.ai_edit_btn.setIcon(QIcon(config.resource_path("pics/ai.svg")))
        self.ai_edit_btn.setToolTip("Open dialog to edit selected line with Gemini.")
        self.ai_edit_btn.clicked.connect(lambda: action_handler.edit_with_ai(self))
        buttons_layout_row1.addWidget(self.ai_edit_btn)

        self.gt_translate_btn = QPushButton(tr("btn_gtranslate"))
        self.gt_translate_btn.setIcon(QIcon(config.resource_path("pics/gt.svg")))
        self.gt_translate_btn.setToolTip("Open dialog to translate selected line with Google Translate.")
        self.gt_translate_btn.clicked.connect(lambda: action_handler.translate_with_google(self))
        buttons_layout_row1.addWidget(self.gt_translate_btn)

        self.batch_gt_btn = QPushButton(tr("btn_batch_gtranslate"))
        self.batch_gt_btn.setIcon(QIcon(config.resource_path("pics/batch.svg")))
        self.batch_gt_btn.setToolTip("Translate selected lines using Google Translate.")
        self.batch_gt_btn.clicked.connect(lambda: action_handler.batch_translate_google(self))
        buttons_layout_row1.addWidget(self.batch_gt_btn)

        self.revert_btn = QPushButton(tr("btn_revert"))
        self.revert_btn.setIcon(QIcon(config.resource_path("pics/revert.svg")))
        self.revert_btn.setToolTip("Revert unsaved changes for selected lines.")
        self.revert_btn.clicked.connect(lambda: table_manager.revert_selected_items(self))
        buttons_layout_row1.addWidget(self.revert_btn)

        self.revert_all_btn = QPushButton(tr("btn_revert_all"))
        self.revert_all_btn.setIcon(QIcon(config.resource_path("pics/revert_all.svg")))
        self.revert_all_btn.setToolTip("Revert all unsaved text changes in the file.")
        self.revert_all_btn.clicked.connect(lambda: table_manager.revert_all_items(self))
        buttons_layout_row1.addWidget(self.revert_all_btn)

        buttons_layout_row1.addStretch() 

        tools_main_layout.addLayout(buttons_layout_row1) 

        buttons_layout_row2 = QHBoxLayout()
        buttons_layout_row2.setSpacing(4) 

        self.toggle_bp_btn = QPushButton(tr("btn_marker"))
        self.toggle_bp_btn.setIcon(QIcon(config.resource_path("pics/breakpoint.svg")))
        self.toggle_bp_btn.setToolTip(f"Set/unset marker ({config.BREAKPOINT_MARKER}).")
        self.toggle_bp_btn.clicked.connect(lambda: action_handler.toggle_breakpoint(self))
        buttons_layout_row2.addWidget(self.toggle_bp_btn)

        self.go_to_bp_btn = QPushButton(tr("btn_next_marker"))
        self.go_to_bp_btn.setIcon(QIcon(config.resource_path("pics/goto.svg")))
        self.go_to_bp_btn.setToolTip("Go to the next line with a marker.")
        self.go_to_bp_btn.clicked.connect(lambda: action_handler.go_to_next_breakpoint(self))
        buttons_layout_row2.addWidget(self.go_to_bp_btn)

        self.clear_bp_btn = QPushButton(tr("btn_clear_markers"))
        self.clear_bp_btn.setIcon(QIcon(config.resource_path("pics/breakpoint_clear.svg")))
        self.clear_bp_btn.setToolTip("Remove all markers in the current tab.")
        self.clear_bp_btn.clicked.connect(lambda: action_handler.clear_all_breakpoints(self))
        buttons_layout_row2.addWidget(self.clear_bp_btn)

        buttons_layout_row2.addStretch() 

        direct_mode_label = QLabel(tr("mode_direct") + ":")
        buttons_layout_row2.addWidget(direct_mode_label)

        self.insert_btn = QPushButton(tr("btn_add"))
        self.insert_btn.setIcon(QIcon(config.resource_path("pics/add.svg")))
        self.insert_btn.setToolTip("Insert a new Ren'Py line ('direct' mode only).")
        self.insert_btn.clicked.connect(lambda: action_handler.insert_line(self))
        buttons_layout_row2.addWidget(self.insert_btn)

        self.delete_btn = QPushButton(tr("btn_delete"))
        self.delete_btn.setIcon(QIcon(config.resource_path("pics/remove.svg")))
        self.delete_btn.setToolTip("Delete the selected line ('direct' mode only).")
        self.delete_btn.clicked.connect(lambda: action_handler.delete_line(self))
        buttons_layout_row2.addWidget(self.delete_btn)

        tools_main_layout.addLayout(buttons_layout_row2) 
        main_content_layout.addWidget(tools_group) 

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.left_panel_container) 
        self.splitter.addWidget(main_content_area)      

        self.splitter.setCollapsible(0, True) 
        self.splitter.setCollapsible(1, False) 
        self.splitter.handle(1).setDisabled(True) 

        main_window_layout = QHBoxLayout()
        main_window_layout.setContentsMargins(0, 0, 0, 0) 
        main_window_layout.setSpacing(0) 
        main_window_layout.addWidget(self.activity_bar) 
        main_window_layout.addWidget(self.splitter) 

        central_widget = QWidget()
        central_widget.setLayout(main_window_layout)
        self.setCentralWidget(central_widget)

        self.statusBar().showMessage(tr("ready"))

    def _create_menu(self):

        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu(tr("menu_file"))

        open_project_action = file_menu.addAction(tr("menu_open_project"))

        open_project_action.triggered.connect(self._handle_open_project)
        self.open_project_action = open_project_action 

        open_action = file_menu.addAction(tr("menu_open_file"))
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(lambda: file_manager.open_file_dialog(self))

        file_menu.addSeparator()

        save_action = file_menu.addAction(tr("menu_save"))
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(lambda: file_manager.save_changes(self))
        self.save_action = save_action 

        save_as_action = file_menu.addAction(tr("menu_save_as"))
        save_as_action.triggered.connect(lambda: file_manager.save_file_dialog(self))
        self.save_as_action = save_as_action

        save_all_action = file_menu.addAction(tr("menu_save_all"))
        save_all_action.setShortcut("Ctrl+Shift+S")
        save_all_action.triggered.connect(lambda: file_manager.save_all_files(self))
        self.save_all_action = save_all_action

        file_menu.addSeparator()

        close_tab_action = file_menu.addAction(tr("menu_close_tab"))
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(lambda: tab_manager.close_current_tab(self)) 
        self.close_tab_action = close_tab_action

        file_menu.addSeparator()

        exit_action = file_menu.addAction(tr("menu_exit"))
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close) 

        edit_menu = menu_bar.addMenu(tr("menu_edit"))
        revert_action = edit_menu.addAction(tr("menu_revert_item"))
        revert_action.setToolTip("Revert unsaved changes for the selected line.")
        revert_action.triggered.connect(lambda: table_manager.revert_single_item_menu(self)) 
        self.revert_action_menu = revert_action

        ai_edit_action = edit_menu.addAction(tr("menu_edit_ai"))
        ai_edit_action.triggered.connect(lambda: action_handler.edit_with_ai(self))
        self.ai_edit_action_menu = ai_edit_action

        gt_action = edit_menu.addAction(tr("menu_translate_google"))
        gt_action.triggered.connect(lambda: action_handler.translate_with_google(self))
        self.gt_action_menu = gt_action

        nav_menu = menu_bar.addMenu(tr("menu_navigation"))
        prev_action = nav_menu.addAction(tr("menu_prev_item"))
        prev_action.setShortcut("Ctrl+Up")
        prev_action.triggered.connect(lambda: action_handler.navigate_prev(self))
        self.prev_action = prev_action

        next_action = nav_menu.addAction(tr("menu_next_item"))
        next_action.setShortcut("Ctrl+Down")
        next_action.triggered.connect(lambda: action_handler.navigate_next(self))
        self.next_action = next_action

        nav_menu.addSeparator()

        next_bp_action = nav_menu.addAction(tr("menu_next_breakpoint"))
        next_bp_action.setShortcut("F2")
        next_bp_action.triggered.connect(lambda: action_handler.go_to_next_breakpoint(self))
        self.next_bp_action = next_bp_action

        tools_menu = menu_bar.addMenu(tr("menu_tools"))
        toggle_bp_action = tools_menu.addAction(tr("menu_toggle_marker"))
        toggle_bp_action.setShortcut("F3")
        toggle_bp_action.triggered.connect(lambda: action_handler.toggle_breakpoint(self))
        self.toggle_bp_action_menu = toggle_bp_action

        clear_bp_action = tools_menu.addAction(tr("menu_clear_markers"))
        clear_bp_action.triggered.connect(lambda: action_handler.clear_all_breakpoints(self))
        self.clear_bp_action_menu = clear_bp_action

        tools_menu.addSeparator()

        insert_action = tools_menu.addAction(tr("menu_insert_line"))
        insert_action.triggered.connect(lambda: action_handler.insert_line(self))
        self.insert_action_menu = insert_action

        delete_action = tools_menu.addAction(tr("menu_delete_line"))
        delete_action.triggered.connect(lambda: action_handler.delete_line(self))
        self.delete_action_menu = delete_action

        settings_menu = menu_bar.addMenu(tr("menu_settings"))
        general_settings_action = settings_menu.addAction(tr("menu_settings_general"))
        general_settings_action.triggered.connect(lambda: settings_manager.show_settings_dialog(self))
        api_key_action = settings_menu.addAction(tr("menu_settings_apikey"))
        def safe_show_api():
            try: settings_manager.show_api_key_dialog(self)
            except Exception as e: QMessageBox.critical(self, tr("error"), f"API Dialog Error: {e}")
        api_key_action.triggered.connect(safe_show_api)

        view_menu = menu_bar.addMenu(tr("menu_view"))
        toggle_project_panel_action = view_menu.addAction(tr("menu_view_project"))
        toggle_project_panel_action.setCheckable(True)
        toggle_project_panel_action.setChecked(False) 
        toggle_project_panel_action.triggered.connect(self.project_view_button.click) 
        self.project_view_button.toggled.connect(toggle_project_panel_action.setChecked) 
        self.toggle_project_panel_action = toggle_project_panel_action 

        toggle_search_panel_action = view_menu.addAction(tr("menu_view_search"))
        toggle_search_panel_action.setCheckable(True)
        toggle_search_panel_action.setChecked(False) 
        toggle_search_panel_action.triggered.connect(self.search_view_button.click) 
        self.search_view_button.toggled.connect(toggle_search_panel_action.setChecked) 
        self.toggle_search_panel_action = toggle_search_panel_action 

        help_menu = menu_bar.addMenu(tr("menu_help"))
        about_action = help_menu.addAction(tr("menu_about"))
        about_action.triggered.connect(self._show_about) 

    def _update_model_list(self, force_refresh=False):

        print(f"--- [_update_model_list] Called. Force refresh: {force_refresh} ---")

        previous_valid_selection = None
        if self.model_combo.count() > 0 and self.model_combo.currentIndex() >= 0:
            current_text = self.model_combo.currentText()
            if current_text not in ["Loading...", "Error loading models", "Models not found", "None"]:
                previous_valid_selection = current_text

        target_model_to_select = previous_valid_selection or self.selected_model
        if not target_model_to_select:
            target_model_to_select = self.settings.get("default_selected_model") or config.DEFAULT_MODEL_NAME

        if not target_model_to_select:
            target_model_to_select = "None" 

        print(f"--- [_update_model_list] Target model for selection: '{target_model_to_select}' ---")

        try:
            self.model_combo.blockSignals(True)
        except Exception as e:
            print(f"Warning: Could not block signals for model_combo: {e}")

        self.model_combo.setEnabled(False) 
        self.model_combo.clear()
        self.model_combo.addItem("None") 
        self.model_combo.addItem("Loading...") 
        self.model_combo.setCurrentIndex(1) 
        QApplication.processEvents() 

        available_models = ai.get_available_models(force_refresh=force_refresh)

        self.model_combo.clear() 
        self.model_combo.addItem("None") 

        if available_models:
            print(f"--- [_update_model_list] Populating combo box with {len(available_models)} models. ---")
            self.model_combo.addItems(available_models)

            selected_index = 0 
            found_target = False

            if target_model_to_select and target_model_to_select != "None":

                exact_match_index = self.model_combo.findText(target_model_to_select)
                if exact_match_index != -1:
                    selected_index = exact_match_index
                    found_target = True
                    print(f"--- [_update_model_list] Found exact match for target model '{target_model_to_select}' at index {selected_index}. ---")
                else:

                    print(f"--- [_update_model_list] Exact match for '{target_model_to_select}' not found. Searching by suffix... ---")
                    for i in range(1, self.model_combo.count()): 
                        model_name_in_combo = self.model_combo.itemText(i)
                        if model_name_in_combo.endswith(target_model_to_select):
                            selected_index = i
                            target_model_to_select = model_name_in_combo 
                            found_target = True
                            print(f"--- [_update_model_list] Found model '{model_name_in_combo}' ending with target '{target_model_to_select}' at index {selected_index}. ---")
                            break 

            if not found_target and target_model_to_select != "None":
                 print(f"--- [_update_model_list] Target model '{target_model_to_select}' not found. Checking config default '{config.DEFAULT_MODEL_NAME}'... ---")
                 config_default_target = config.DEFAULT_MODEL_NAME
                 config_default_index = self.model_combo.findText(config_default_target)
                 if config_default_index != -1:
                     selected_index = config_default_index
                     target_model_to_select = config_default_target 
                     found_target = True
                     print(f"--- [_update_model_list] Found exact match for config default model '{config_default_target}'. ---")
                 else:

                     for i in range(1, self.model_combo.count()):
                         model_name_in_combo = self.model_combo.itemText(i)
                         if model_name_in_combo.endswith(config_default_target):
                             selected_index = i
                             target_model_to_select = model_name_in_combo 
                             found_target = True
                             print(f"--- [_update_model_list] Found config default model '{model_name_in_combo}' ending with '{config_default_target}'. ---")
                             break

            if not found_target and self.model_combo.count() > 1: 
                selected_index = 1 
                target_model_to_select = self.model_combo.itemText(selected_index)
                print(f"--- [_update_model_list] Neither target nor config default found. Selecting first available: '{target_model_to_select}'. ---")

            self.model_combo.setCurrentIndex(selected_index)

            current_text_selection = self.model_combo.currentText()
            print(f"--- [_update_model_list] Set combo box index to {selected_index} ('{current_text_selection}'). ---")

            self.model_combo.setEnabled(True) 
        else:

            print("--- [_update_model_list] Failed to load models or no models available. ---")

            if self.model_combo.findText("Error loading models") == -1:
                self.model_combo.addItem("Error loading models")

            self.model_combo.setCurrentIndex(self.model_combo.findText("Error loading models")) 
            self.model_combo.setEnabled(False) 
            ai.no_ai = True 

        try:
            self.model_combo.blockSignals(False)
        except Exception as e:
            print(f"Warning: Could not unblock signals for model_combo: {e}")

        self._update_ui_state()

    def _handle_open_project(self):

        file_manager.open_project_dialog(self) 

    def _populate_project_tree(self, project_path):

        if not project_path or not os.path.isdir(project_path):
            print(f"Error: Invalid project path provided: {project_path}")
            self.current_project_path = None
            self._toggle_project_panel(False) 
            self._update_ui_state() 
            return

        self.current_project_path = project_path
        print(f"Populating project tree for: {project_path}")

        self.file_system_model.setRootPath(project_path)

        self.file_system_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files)
        self.file_system_model.setNameFilters(["*.rpy"])
        self.file_system_model.setNameFilterDisables(False) 

        self.project_tree_view.setModel(self.file_system_model)
        root_index = self.file_system_model.index(project_path)
        self.project_tree_view.setRootIndex(root_index)

        for i in range(1, self.file_system_model.columnCount()):
            self.project_tree_view.hideColumn(i)

        self.project_view_button.setChecked(True) 

    def _handle_tree_item_activated(self, index):

        if not self.file_system_model:
            return

        file_path = self.file_system_model.filePath(index)
        is_dir = self.file_system_model.isDir(index)

        if is_dir:

            return

        if file_path and file_path.lower().endswith(".rpy"):
            print(f"Tree item activated: {file_path}")

            existing_tab_index = tab_manager.find_tab_by_path(self, file_path)
            if existing_tab_index is not None:
                print(f"File already open in tab {existing_tab_index}. Switching.")
                self.tab_widget.setCurrentIndex(existing_tab_index)
                return

            print("File not open. Determining mode and loading...")

            if not settings_manager.ensure_mode_setting_chosen(self):
                 self.statusBar().showMessage("File opening canceled. Mode setting must be selected.", 5000)
                 return

            final_mode = file_manager.determine_file_mode(self, file_path)
            if final_mode:
                file_manager.load_file(self, file_path, final_mode)
            else:
                print("File loading cancelled (mode selection).")
        else:
            print(f"Ignoring activation for non-rpy file or invalid path: {file_path}")

    def _handle_activity_bar_toggle(self, checked):

        sender_button = self.sender()
        buttons = [self.project_view_button, self.search_view_button] 

        print(f"--- Activity Bar Toggle: Button '{sender_button.objectName()}' -> Checked: {checked} ---")

        panel_to_show = None
        target_panel_visible = False

        if checked:

            for button in buttons:
                if button is not sender_button and button.isChecked():
                    button.blockSignals(True) 
                    button.setChecked(False)
                    button.blockSignals(False)

            if sender_button is self.project_view_button:
                panel_to_show = self.project_panel
                print("  -> Project panel requested (showing)")
            elif sender_button is self.search_view_button:
                panel_to_show = self.search_replace_panel
                print("  -> Search panel requested (showing)")

            if panel_to_show:
                self.left_panel_layout.setCurrentWidget(panel_to_show)
                target_panel_visible = True

        else:

            print(f"  -> Button '{sender_button.objectName()}' unchecked. Hiding panel.")

            target_panel_visible = False

        self._set_left_panel_visibility(target_panel_visible)

        if hasattr(self, 'toggle_project_panel_action'):
             is_proj_checked = self.project_view_button.isChecked()

             if self.toggle_project_panel_action.isChecked() != is_proj_checked:
                 self.toggle_project_panel_action.setChecked(is_proj_checked)

        if hasattr(self, 'toggle_search_panel_action'):
             is_search_checked = self.search_view_button.isChecked()
             if self.toggle_search_panel_action.isChecked() != is_search_checked:
                 self.toggle_search_panel_action.setChecked(is_search_checked)

        self._update_ui_state() 

    def _set_left_panel_visibility(self, visible):

        if self.left_panel_container.isVisible() == visible:
            return 

        print(f"--- Setting left panel visibility to: {visible} ---")
        self.left_panel_container.setVisible(visible)

        self.splitter.handle(1).setDisabled(not visible)

        if visible:

            current_sizes = self.splitter.sizes()

            if current_sizes[0] < 50:
                total_width = sum(current_sizes)
                left_width = 250 
                right_width = max(200, total_width - left_width) 
                self.splitter.setSizes([left_width, right_width])
                print(f"  Splitter sizes reset to: {[left_width, right_width]}")
            else:
                print(f"  Splitter sizes remain: {current_sizes}")
        else:

            current_sizes = self.splitter.sizes()
            if current_sizes[0] > 0:
                 total_width = sum(current_sizes)
                 self.splitter.setSizes([0, total_width])
                 print(f"  Splitter sizes set to hide left panel: {[0, total_width]}")

    def _update_language_model_display(self):

        current_file_data = self._get_current_file_data()

        default_target_lang_code = self.settings.get("default_target_language", config.DEFAULT_TARGET_LANG)
        default_source_lang_code = self.settings.get("default_source_language", config.DEFAULT_SOURCE_LANG)
        default_model = self.settings.get("default_selected_model", config.DEFAULT_MODEL_NAME)

        target_lang_code_to_set = default_target_lang_code
        source_lang_code_to_set = default_source_lang_code
        model_to_set = default_model

        if current_file_data:
            tab_mode = current_file_data.get('mode')

            tab_target_lang_code = current_file_data.get('target_language')
            tab_source_lang_code = current_file_data.get('source_language')
            tab_model = current_file_data.get('selected_model')

            use_detected_setting = self.settings.get("use_detected_target_lang", config.DEFAULT_USE_DETECTED_TARGET_LANG)

            if tab_mode == 'translate' and use_detected_setting and tab_target_lang_code:

                target_lang_code_to_set = tab_target_lang_code
            elif tab_target_lang_code:

                 target_lang_code_to_set = tab_target_lang_code

            if tab_source_lang_code:
                source_lang_code_to_set = tab_source_lang_code

            model_to_set = tab_model

        self.target_language = target_lang_code_to_set
        self.source_language = source_lang_code_to_set
        self.selected_model = model_to_set 

        self.target_lang_combo.blockSignals(True)
        self.source_lang_combo.blockSignals(True)
        self.model_combo.blockSignals(True)

        target_idx = self.target_lang_combo.findData(self.target_language)
        self.target_lang_combo.setCurrentIndex(target_idx if target_idx != -1 else 0)
        print(f"  Set target_lang_combo index to {self.target_lang_combo.currentIndex()} (found index {target_idx} for code '{self.target_language}')")

        source_idx = self.source_lang_combo.findData(self.source_language)
        self.source_lang_combo.setCurrentIndex(source_idx if source_idx != -1 else 0)
        print(f"  Set source_lang_combo index to {self.source_lang_combo.currentIndex()} (found index {source_idx} for code '{self.source_language}')")

        current_model_text_in_combo = self.model_combo.currentText()
        placeholder_texts = ["Loading...", "Error loading models"]

        if current_model_text_in_combo not in placeholder_texts:

            model_text_to_find = self.selected_model if self.selected_model else "None"
            model_idx = self.model_combo.findText(model_text_to_find)

            if model_idx != -1:
                self.model_combo.setCurrentIndex(model_idx)
                print(f"  Set model_combo index to {model_idx} for model '{model_text_to_find}'")
            elif self.model_combo.count() > 0:

                self.model_combo.setCurrentIndex(0)
                self.selected_model = None 
                print(f"  Model '{model_text_to_find}' not found, set model_combo to 'None' (index 0)")
        else:
            print(f"  Skipped setting model_combo index due to placeholder '{current_model_text_in_combo}'")

        self.target_lang_combo.blockSignals(False)
        self.source_lang_combo.blockSignals(False)
        self.model_combo.blockSignals(False)

        print(f"UI updated: Target Lang Code='{self.target_language}', Source Lang Code='{self.source_language}', Model='{self.selected_model}'")

    def _update_main_window_defaults_display(self):

        self.target_lang_combo.blockSignals(True)
        self.source_lang_combo.blockSignals(True)
        self.model_combo.blockSignals(True)

        target_idx = self.target_lang_combo.findData(self.target_language)
        self.target_lang_combo.setCurrentIndex(target_idx if target_idx != -1 else 0)

        source_idx = self.source_lang_combo.findData(self.source_language)
        self.source_lang_combo.setCurrentIndex(source_idx if source_idx != -1 else 0)

        model_to_set = self.selected_model 
        model_idx = -1
        print(f"  Model to set: '{model_to_set}'")
        if model_to_set:
             model_idx = self.model_combo.findText(model_to_set)
             print(f"  Found model index: {model_idx}")
        else:

             model_idx = 0
             print(f"  Model is None, setting index to 0 ('None')")

        model_idx = -1
        if self.selected_model:
             model_idx = self.model_combo.findText(self.selected_model)

        if model_idx != -1:
             self.model_combo.setCurrentIndex(model_idx)
        elif self.model_combo.count() > 0:

             self.model_combo.setCurrentIndex(0)

        self.target_lang_combo.blockSignals(False)
        self.source_lang_combo.blockSignals(False)
        self.model_combo.blockSignals(False)

    def _get_current_table(self) -> QTableWidget | None:

        current_widget = self.tab_widget.currentWidget()
        return current_widget if isinstance(current_widget, QTableWidget) else None

    def _get_current_file_data(self) -> dict | None:

        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index != -1:
            file_path = self.tab_data.get(current_tab_index)

            widget = self.tab_widget.widget(current_tab_index)
            widget_path = widget.property("filePath") if widget else None
            if file_path and file_path in self.file_data:

                if widget_path and file_path != widget_path:
                    print(f"Warning: Path mismatch between tab_data ('{file_path}') and widget ('{widget_path}') for index {current_tab_index}. Using tab_data path.")
                return self.file_data[file_path]
            elif widget_path and widget_path in self.file_data:

                 print(f"Warning: Correcting tab_data for index {current_tab_index} using widget path '{widget_path}'.")
                 self.tab_data[current_tab_index] = widget_path
                 return self.file_data[widget_path]

        return None

    def _get_current_translatable_items(self) -> list | None:

        data = self._get_current_file_data()
        return data.get('items') if data else None

    def _get_current_item_index(self) -> int:

        data = self._get_current_file_data()

        return data.get('item_index', -1) if data else -1

    def _set_current_item_index(self, index: int):

        data = self._get_current_file_data()
        if data:
            if data.get('item_index') != index:
                data['item_index'] = index
                self._display_current_item_status() 

    def _is_current_tab_modified(self) -> bool:

        data = self._get_current_file_data()

        return data.get('is_modified', False) if data else False

    def _set_current_tab_modified(self, modified: bool = True):

        data = self._get_current_file_data()
        if data:
            was_modified = data.get('is_modified', False)
            if was_modified != modified:
                data['is_modified'] = modified

                current_tab_index = self.tab_widget.currentIndex()
                if current_tab_index != -1 and self.current_file_path:

                    base_name = os.path.basename(data.get('output_path', self.current_file_path))
                    new_tab_text = f"{base_name}*" if modified else base_name
                    self.tab_widget.setTabText(current_tab_index, new_tab_text)

                self._update_ui_state()

    def _update_ui_state(self):

        current_table = self._get_current_table()
        current_file_data = self._get_current_file_data()
        current_items = self._get_current_translatable_items()
        current_item_idx = self._get_current_item_index()

        is_online = ai.is_internet_available() 
        if not is_online:

             current_message = self.statusBar().currentMessage()
             if "Error" not in current_message and "available" not in current_message: 
                  self.statusBar().showMessage("No internet connection.", 3000)

        has_open_tabs = self.tab_widget.count() > 0
        self.file_is_loaded = has_open_tabs

        tab_is_active = has_open_tabs and current_table is not None and current_file_data is not None
        tab_has_items = tab_is_active and current_items is not None and len(current_items) > 0
        tab_is_modified = self._is_current_tab_modified()
        project_is_open = bool(self.current_project_path) 

        self.save_action.setEnabled(tab_is_modified)
        self.save_as_action.setEnabled(tab_is_active)
        any_modified = any(data.get('is_modified', False) for data in self.file_data.values())
        self.save_all_action.setEnabled(any_modified)
        self.close_tab_action.setEnabled(has_open_tabs)

        if hasattr(self, 'toggle_project_panel_action'):
             self.toggle_project_panel_action.setEnabled(project_is_open)
        if hasattr(self, 'toggle_search_panel_action'):
             self.toggle_search_panel_action.setEnabled(has_open_tabs) 

        if self.project_view_button:
            self.project_view_button.setEnabled(project_is_open)

            if not project_is_open and self.project_view_button.isChecked():
                 self.project_view_button.setChecked(False)
        if self.search_view_button:
             self.search_view_button.setEnabled(has_open_tabs) 

             if not has_open_tabs and self.search_view_button.isChecked():
                  self.search_view_button.setChecked(False)

        if current_table:
             current_table.setEnabled(tab_has_items)

        selected_rows = []
        if current_table:
            selected_indices = current_table.selectedIndexes()
            selected_rows = sorted(list(set(index.row() for index in selected_indices)))

        has_selection = len(selected_rows) > 0
        single_item_selected = has_selection and current_item_idx >= 0 and tab_has_items 

        can_revert_selected = False
        if has_selection and current_items:
            can_revert_selected = any(
                0 <= row_idx < len(current_items) and current_items[row_idx].get('is_modified_session', False)
                for row_idx in selected_rows
            )

        self.revert_btn.setEnabled(can_revert_selected)
        self.revert_all_btn.setEnabled(tab_is_modified)

        can_revert_current_single = False
        if single_item_selected and current_items and 0 <= current_item_idx < len(current_items):
             can_revert_current_single = current_items[current_item_idx].get('is_modified_session', False)
        self.revert_action_menu.setEnabled(single_item_selected and can_revert_current_single)

        self.prev_action.setEnabled(single_item_selected and current_item_idx > 0)

        self.next_action.setEnabled(tab_has_items and single_item_selected and current_item_idx < len(current_items) - 1)

        has_breakpoints_set = False
        if tab_has_items and current_file_data and current_file_data.get('breakpoints'):
            has_breakpoints_set = bool(current_file_data.get('breakpoints'))

        self.go_to_bp_btn.setEnabled(has_breakpoints_set)
        self.next_bp_action.setEnabled(has_breakpoints_set)
        self.clear_bp_btn.setEnabled(has_breakpoints_set)
        self.clear_bp_action_menu.setEnabled(has_breakpoints_set)
        self.toggle_bp_btn.setEnabled(single_item_selected)
        self.toggle_bp_action_menu.setEnabled(single_item_selected)

        ai_available = not ai.no_ai 
        print(f"--- [_update_ui_state] AI available check: ai.no_ai = {ai.no_ai} -> ai_available = {ai_available} ---") 
        can_use_ai_edit = single_item_selected and ai_available
        self.ai_edit_btn.setEnabled(can_use_ai_edit)
        self.ai_edit_action_menu.setEnabled(can_use_ai_edit)
        print(f"--- [_update_ui_state] AI buttons enabled: {can_use_ai_edit} (single_selected={single_item_selected}, ai_available={ai_available}) ---") 

        _translator_module = ai._lazy_import_translator() 
        translator_library_ok = _translator_module is not None
        is_online = ai.is_internet_available() 
        translator_available = translator_library_ok and is_online
        print(f"--- [_update_ui_state] GTranslate check: library_ok={translator_library_ok}, is_online={is_online} -> translator_available={translator_available} ---") 
        can_use_gtranslate = single_item_selected and translator_available
        can_use_batch_gtranslate = has_selection and translator_available
        self.gt_translate_btn.setEnabled(can_use_gtranslate)
        self.gt_action_menu.setEnabled(can_use_gtranslate)
        self.batch_gt_btn.setEnabled(can_use_batch_gtranslate)
        print(f"--- [_update_ui_state] GTranslate buttons enabled: single={can_use_gtranslate}, batch={can_use_batch_gtranslate} (single_selected={single_item_selected}, has_selection={has_selection}, translator_available={translator_available}) ---") 

        is_direct_mode = tab_is_active and current_file_data.get('mode') == "direct"

        self.insert_btn.setEnabled(tab_is_active and is_direct_mode)
        self.insert_action_menu.setEnabled(tab_is_active and is_direct_mode)

        self.delete_btn.setEnabled(single_item_selected and is_direct_mode)
        self.delete_action_menu.setEnabled(single_item_selected and is_direct_mode)

        search_panel_active = self.search_replace_panel and self.search_replace_panel.isVisible()
        can_search = tab_is_active and self.search_input and bool(self.search_input.text())
        if self.find_next_btn: self.find_next_btn.setEnabled(can_search)

        if self.replace_btn: self.replace_btn.setEnabled(can_search and has_selection)
        if self.replace_all_btn: self.replace_all_btn.setEnabled(can_search)

        if self.regex_checkbox: self.regex_checkbox.setEnabled(search_panel_active and tab_is_active)

        if current_table and current_file_data:
            current_mode = current_file_data.get('mode', 'direct')

            self.mode_display_label.setText("Direct" if current_mode == "direct"
                                             else "Translate")
        elif not has_open_tabs:
             self.mode_display_label.setText("None")

    def _display_current_item_status(self):

        status_updater.update_status_bar(self)

    def _show_about(self):

        QMessageBox.about(self, f"About RenForge v{config.VERSION}", config.ABOUT_TEXT)

    def closeEvent(self, event):

        modified_files_info = []
        for file_path, data in self.file_data.items():
            if data.get('is_modified', False):
                base_name = os.path.basename(data.get('output_path', file_path))
                modified_files_info.append((base_name, file_path))

        should_exit = False 
        user_decision = "cancel" 

        if modified_files_info:
            file_list_str = "\n - ".join([info[0] for info in modified_files_info])
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr("unsaved_changes_title"))
            msg_box.setText(f"The following files have unsaved changes:\n\n - {file_list_str}")
            msg_box.setInformativeText("\nSave all before exiting?")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            save_button = msg_box.addButton(tr("btn_save_all"), QMessageBox.ButtonRole.AcceptRole)
            discard_button = msg_box.addButton(tr("btn_exit_without_saving"), QMessageBox.ButtonRole.DestructiveRole)
            cancel_button = msg_box.addButton(tr("cancel"), QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(cancel_button)

            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            if clicked_button == save_button:

                all_saved = file_manager.save_all_files(self)
                if not all_saved:
                    self.statusBar().showMessage(tr("save_failed_exit_cancelled"), 5000)
                    event.ignore()
                    return 
                else:
                    should_exit = True 
                    user_decision = "save"
            elif clicked_button == discard_button:
                should_exit = True 
                user_decision = "discard"
            else: 
                self.statusBar().showMessage(tr("exit_cancelled"), 3000)
                event.ignore()
                return 
        else:
            should_exit = True 
            user_decision = "no_changes"

        if should_exit:
            is_max = self.isMaximized()
            geo = self.geometry()
            self.settings["window_maximized"] = is_max

            if not is_max:
                self.settings["window_size_w"] = geo.width()
                self.settings["window_size_h"] = geo.height()

            if not save_settings(self.settings): 
                 print("Warning: Could not save settings (including window geometry) on exit.")

            else:
                 print("Window geometry saved.")

            event.accept() 
        else:
             event.ignore() 

if __name__ == '__main__':
    if not GUI_AVAILABLE:
        print("GUI is not available. Exiting.")
        sys.exit(1)

    app = QApplication(sys.argv)

    main_window = RenForgeGUI()
    main_window.show()
    sys.exit(app.exec())