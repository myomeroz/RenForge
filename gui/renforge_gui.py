import sys
import os
import gc 
import time

# Import logger early for critical errors
from renforge_logger import get_logger
logger = get_logger("gui")

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QMessageBox, QTabWidget, QSplitter, QTableWidget,
                               QDockWidget, QLabel, QTableView) 
    from PySide6.QtCore import Qt, QTimer, Signal, QSize, Slot, QDir
    from PySide6.QtGui import QFont, QIcon, QFileSystemModel 
    GUI_AVAILABLE = True
except ImportError:
    logger.critical("PySide6 is required for the GUI but not found.")
    logger.critical("Please install it: pip install PySide6")
    GUI_AVAILABLE = False
    sys.exit(1)

try:

    import renforge_config as config
    import renforge_core as core
    import renforge_ai as ai 
    import parser.core as parser
    from renforge_settings import save_settings, load_settings
    from locales import tr 
    from models.parsed_file import ParsedFile, ParsedItem
    from renforge_enums import FileMode, ItemType 

    from gui.renforge_gui_dialog import (AIEditDialog, GoogleTranslateDialog, ApiKeyDialog,
                                       ModeSelectionDialog, InsertLineDialog, SettingsDialog)
    from gui.renforge_gui_styles import DARK_STYLE_SHEET
    from gui.ui_builder import UIBuilder
    # NOTE: ProjectController and BatchController are now imported and instantiated
    # in app_bootstrap.py via DI container, not directly here.

    import gui.gui_file_manager as file_manager
    import gui.gui_tab_manager as tab_manager
    import gui.gui_table_manager as table_manager
    import gui.gui_action_handler as action_handler
    import gui.gui_settings_manager as settings_manager
    import gui.gui_status_updater as status_updater
    import gui.views.settings_view as settings_view
    from gui.widgets.batch_summary_panel import BatchSummaryPanel
    from gui.widgets.filter_toolbar import FilterToolbar
    from gui.widgets.glossary_panel import GlossaryPanel
    from gui.widgets.qa_panel import QAPanel
    from gui.widgets.review_panel import ReviewPanel
    from gui.widgets.preflight_panel import PreflightPanel
    from gui.widgets.tm_panel import TMPanel
    from gui.widgets.plugin_settings_widget import PluginSettingsWidget
    from models.batch_undo import get_undo_manager

except ImportError as e:
     logger.critical(f"Failed to import required renforge modules or GUI managers: {e}")
     try:
          if QApplication.instance():
               QMessageBox.critical(None, "Module Import Error",
                                    f"Failed to import necessary RenForge modules or GUI managers:\n{e}\n\n"
                                    "Ensure all files (*.py, gui/*.py) are in the correct locations.")
     except Exception as msg_e:
          logger.error(f"Could not show GUI error message: {msg_e}")
     sys.exit(1)

SUPPORTED_LANGUAGES = {}

class RenForgeGUI(QMainWindow):
    """
    Main application window - implements IMainView protocol.
    
    Emits signals for user actions, receives updates from controllers.
    """
    
    # =========================================================================
    # IMainView PROTOCOL SIGNALS
    # =========================================================================
    
    # File operations
    open_project_requested = Signal()
    open_file_requested = Signal()
    save_requested = Signal()
    save_all_requested = Signal()
    save_as_requested = Signal() # Phase 5: Added for Save As support
    file_loaded = Signal(str)  # file path (for legacy sync)
    close_tab_requested = Signal(int)  # tab index
    exit_requested = Signal()
    
    # Navigation
    tab_changed = Signal(int)  # tab index
    item_selected = Signal(int)  # item index
    
    # Translation
    translate_google_requested = Signal()
    translate_ai_requested = Signal()
    batch_google_requested = Signal()
    batch_ai_requested = Signal()
    
    # Settings
    target_language_changed = Signal(str)  # language code
    source_language_changed = Signal(str)  # language code
    model_changed = Signal(str)  # model name


    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title", version=config.VERSION))

        self.resize(1200, 800)

        self.current_file_path = None 
        self.current_project_path = None 
        self.file_data: dict[str, ParsedFile] = {} 
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
        
        # Search UI (Stage 8.1)
        self.search_scope_combo = None
        self.search_safe_mode_chk = None
        self.find_prev_btn = None
        self.search_info_label = None
        
        # Search Manager
        from core.search_manager import SearchManager
        self.search_manager = SearchManager(self)

        # Note: _batch_errors, _batch_warnings etc. are now managed by BatchController
        # and exposed as @property for backward compatibility

        # Phase 4: Controller reference (set by bootstrap)
        self._app_controller = None

        self.SUPPORTED_LANGUAGES = {} 

        settings_manager.load_initial_settings(self)

        self._restore_window_geometry() 
        # State restoration happens in _init_workspace now for docks 

        self.target_language = self.settings.get("default_target_language", config.DEFAULT_TARGET_LANG)
        self.source_language = self.settings.get("default_source_language", config.DEFAULT_SOURCE_LANG)
        self.selected_model = self.settings.get("default_selected_model", config.DEFAULT_MODEL_NAME) 

        self.file_is_loaded = False 
        self._block_item_changed_signal = False 

        self._load_languages()

        self.file_system_model = QFileSystemModel()

        # Stage 5: Create FilterToolbar (created before layout assembly)
        from gui.widgets.filter_toolbar import FilterToolbar
        self.filter_toolbar = FilterToolbar() 
        self.filter_toolbar.filter_changed.connect(self._handle_filter_changed)
        # self.filter_toolbar.hide() # Don't hide, UIBuilder will add it.

        # Use UIBuilder (instantiate mainly)
        ui_builder = UIBuilder(self)
        ui_builder.assemble_layout()
        
        # NOTE: ProjectController and BatchController are now created and assigned
        # by app_bootstrap.py via DI container. These attributes will be set there.
        # Initialize as None for early access safety before bootstrap completes.
        self.project_controller = None
        self.batch_controller = None
        
        self.setStyleSheet(DARK_STYLE_SHEET)
        
        # Stage 14: Workspace Init
        self._init_workspace()

        # Build Menus LAST so they can reference docks
        ui_builder.build_menu_bar()
        

        
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
        """Delegate to BatchController."""
        self.batch_controller.clear_results()
    
    # Expose batch controller properties for backward compatibility
    @property
    def _batch_errors(self):
        return self.batch_controller.errors
    
    @property
    def _batch_warnings(self):
        return self.batch_controller.warnings

    @Slot(int, str, dict)
    def _handle_batch_item_updated(self, item_index, translated_text, updated_item_data_copy):
        """Delegate to BatchController."""
        self.batch_controller.handle_item_updated(item_index, translated_text, updated_item_data_copy)

    @Slot(str)
    def _handle_batch_translate_error(self, details):
        """Delegate to BatchController."""
        self.batch_controller.handle_error(details)

    @Slot(str)
    def _handle_batch_translate_warning(self, details):
        """Delegate to BatchController."""
        self.batch_controller.handle_warning(details)

    @Slot()
    def _mark_tab_modified_from_worker(self):
        """Delegate to BatchController."""
        self.batch_controller.mark_tab_modified()

    @Slot(dict)
    def _handle_batch_translate_finished(self, results):
        """Delegate to BatchController and update summary panel."""
        self.batch_controller.handle_finished(results)
        
        # Update summary panel
        self.batch_summary_panel.update_summary(results)
        self.batch_summary_panel.show()
        
        # Stage 9: Auto-Run QA
        if hasattr(self, 'qa_panel') and self.qa_panel.auto_chk.isChecked():
            self.qa_panel.run_scan()
        
        # Check if undo is available
        current_file_data = self._get_current_file_data()
        if current_file_data:
            undo_mgr = get_undo_manager()
            self.batch_summary_panel.set_undo_available(
                undo_mgr.has_undo(current_file_data.file_path)
            )
    
    @Slot(str)
    def _handle_filter_changed(self, filter_type: str):
        """Handle filter selection change from FilterToolbar."""
        current_table = self._get_current_table()
        current_file_data = self._get_current_file_data()
        
        if not current_table or not current_file_data:
            return
        
        # TranslationTableView için proxy model üzerinden filtreleme
        from gui.views.translation_table_view import TranslationTableView
        
        if isinstance(current_table, TranslationTableView):
            # Yeni Model-View: Proxy model filtreleme kullanır
            from gui.views import file_table_view
            proxy = file_table_view.get_proxy_model(current_table)
            
            if proxy:
                if filter_type == "all":
                    proxy.clear_filters()
                    visible = proxy.rowCount()
                elif filter_type == "changed":
                    proxy.set_status_filter(proxy.FILTER_MODIFIED)
                    visible = proxy.rowCount()
                elif filter_type == "ai_fail":
                    proxy.set_status_filter(proxy.FILTER_FAILED)
                    visible = proxy.rowCount()
                elif filter_type == "ai_warn":
                    proxy.set_status_filter(proxy.FILTER_WARNING)
                    visible = proxy.rowCount()
                elif filter_type == "empty":
                    proxy.set_status_filter(proxy.FILTER_EMPTY)
                    visible = proxy.rowCount()
                else:
                    visible = proxy.rowCount()
                
                total = len(current_file_data.items)
                if filter_type == "all":
                    self.filter_toolbar.set_info(f"{visible} rows")
                else:
                    self.filter_toolbar.set_info(f"Showing {visible}/{total}")
        else:
            # Eski QTableWidget davranışı
            if filter_type == "all":
                visible = table_manager.clear_filter(current_table)
                self.filter_toolbar.set_info(f"{visible} rows")
            else:
                visible = table_manager.filter_table_rows(
                    current_table, current_file_data.items, filter_type
                )
                total = len(current_file_data.items)
                self.filter_toolbar.set_info(f"Showing {visible}/{total}")
    
    @Slot()
    def _handle_undo_requested(self):
        """Handle Undo Last Batch request."""
        current_file_data = self._get_current_file_data()
        current_table = self._get_current_table()
        
        if not current_file_data or not current_table:
            return
        
        undo_mgr = get_undo_manager()
        
        if not undo_mgr.has_undo(current_file_data.file_path):
            self.statusBar().showMessage(tr("msg_nothing_to_revert"), 3000)
            return
        
        snapshot = undo_mgr.get_snapshot(current_file_data.file_path)
        row_count = snapshot.row_count() if snapshot else 0
        
        reply = QMessageBox.question(
            self, tr("confirm_undo_title"),
            tr("confirm_undo_msg", count=row_count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Perform restore
        affected_indices = list(snapshot.affected_rows.keys()) if snapshot else []
        
        if undo_mgr.restore(current_file_data.file_path, current_file_data.items):
            # Update only affected rows and sync file lines (Data Consistency)
            current_lines = current_file_data.lines
            
            for row_idx in affected_indices:
                if 0 <= row_idx < len(current_file_data.items):
                    item = current_file_data.items[row_idx]
                    
                    # 1. Update Table UI
                    table_manager.update_table_item_text(
                        self, current_table, row_idx, 4, item.current_text or ""
                    )
                    table_manager.update_table_row_style(current_table, row_idx, item)
                    table_manager.update_row_batch_marker(
                        current_table, row_idx, 
                        item.batch_marker, item.batch_tooltip
                    )
                    
                    # 2. Sync File Lines (Critical Fix)
                    if current_file_data.mode == "translate" and item.line_index is not None:
                        if 0 <= item.line_index < len(current_lines):
                            new_line = parser.format_line_from_components(item, item.current_text)
                            if new_line is not None:
                                current_lines[item.line_index] = new_line
                            else:
                                logger.warning(f"Could not format line {item.line_index} during undo")
            
            # 3. Recompute Tab Modified State correctly
            any_text_modified = any(item.is_modified_session for item in current_file_data.items)
            breakpoint_modified = getattr(current_file_data, 'breakpoint_modified', False)
            
            tab_modified = any_text_modified or breakpoint_modified
            self._set_current_tab_modified(tab_modified)
            
            self.statusBar().showMessage(tr("msg_reverted_n_rows", count=row_count), 4000)
            
            # Update undo button state
            self.batch_summary_panel.set_undo_available(False)
        else:
            self.statusBar().showMessage(tr("undo_failed"), 4000)

    def _perform_initial_checks(self):

        logger.debug("Performing initial checks")

        settings_manager.check_initial_mode_setting(self)

        logger.debug("Triggering initial Gemini check/initialization")

        QTimer.singleShot(50, lambda: settings_manager.ensure_gemini_initialized(self))
        logger.debug("Initial checks finished")
        QTimer.singleShot(200, self._sync_model_selection) 

    def _sync_model_selection(self):
        settings_view.sync_model_selection(self)

    def _load_languages(self):
        settings_view.load_languages(self) 


    # NOTE: _create_ui() and _create_menu() have been moved to gui/ui_builder.py
    # They are now called via UIBuilder.assemble_layout() and UIBuilder.build_menu_bar()

    def _update_model_list(self, force_refresh=False):
        settings_view.update_model_list(self, force_refresh)

    def _handle_open_project(self):
        """Delegate to ProjectController."""
        self.project_controller.handle_open_project()

    def _populate_project_tree(self, project_path):
        """Delegate to ProjectController."""
        self.project_controller.populate_project_tree(project_path)
        
        # Stage 11: Init TM
        from core.tm_store import init_tm_manager
        init_tm_manager(project_path)

    def _handle_tree_item_activated(self, index):
        """Delegate to ProjectController."""
        self.project_controller.handle_tree_item_activated(index)

    def _handle_activity_bar_toggle(self, checked):
        """Delegate to ProjectController."""
        if self.project_controller:
            self.project_controller.handle_activity_bar_toggle(checked)

    def _set_left_panel_visibility(self, visible):
        """Delegate to ProjectController."""
        if self.project_controller:
            self.project_controller.set_left_panel_visibility(visible)

    def _update_language_model_display(self):

        current_file_data = self._get_current_file_data()

        # Use current window settings as starting point (preserve user's existing selection)
        target_lang_code_to_set = self.target_language
        source_lang_code_to_set = self.source_language
        model_to_set = self.selected_model
        
        # Use defaults only if no active selection exists
        if target_lang_code_to_set is None:
            target_lang_code_to_set = self.settings.get("default_target_language", config.DEFAULT_TARGET_LANG)
        if source_lang_code_to_set is None:
            source_lang_code_to_set = self.settings.get("default_source_language", config.DEFAULT_SOURCE_LANG)
        if model_to_set is None:
            model_to_set = self.settings.get("default_selected_model", config.DEFAULT_MODEL_NAME)

        if current_file_data:
            tab_mode = current_file_data.mode

            tab_target_lang_code = current_file_data.target_language
            tab_source_lang_code = current_file_data.source_language
            tab_model = current_file_data.selected_model

            use_detected_setting = self.settings.get("use_detected_target_lang", config.DEFAULT_USE_DETECTED_TARGET_LANG)

            # Only override if file has an explicit value set
            if tab_mode == 'translate' and use_detected_setting and tab_target_lang_code:
                target_lang_code_to_set = tab_target_lang_code
            elif tab_target_lang_code:
                 target_lang_code_to_set = tab_target_lang_code

            if tab_source_lang_code:
                source_lang_code_to_set = tab_source_lang_code

            # Only use tab model if explicitly set (not None)
            if tab_model is not None:
                model_to_set = tab_model

        self.target_language = target_lang_code_to_set
        self.source_language = source_lang_code_to_set
        self.selected_model = model_to_set 

        self.target_lang_combo.blockSignals(True)
        self.source_lang_combo.blockSignals(True)
        self.model_combo.blockSignals(True)

        target_idx = self.target_lang_combo.findData(self.target_language)
        self.target_lang_combo.setCurrentIndex(target_idx if target_idx != -1 else 0)
        logger.debug(f"  Set target_lang_combo index to {self.target_lang_combo.currentIndex()} (found index {target_idx} for code '{self.target_language}')")

        source_idx = self.source_lang_combo.findData(self.source_language)
        self.source_lang_combo.setCurrentIndex(source_idx if source_idx != -1 else 0)
        logger.debug(f"  Set source_lang_combo index to {self.source_lang_combo.currentIndex()} (found index {source_idx} for code '{self.source_language}')")

        current_model_text_in_combo = self.model_combo.currentText()
        placeholder_texts = ["Loading...", "Error loading models"]

        if current_model_text_in_combo not in placeholder_texts:

            model_text_to_find = self.selected_model if self.selected_model else "None"
            model_idx = self.model_combo.findText(model_text_to_find)

            if model_idx != -1:
                self.model_combo.setCurrentIndex(model_idx)
                logger.debug(f"  Set model_combo index to {model_idx} for model '{model_text_to_find}'")
            elif self.model_combo.count() > 0:

                self.model_combo.setCurrentIndex(0)
                self.selected_model = None 
                logger.debug(f"  Model '{model_text_to_find}' not found, set model_combo to 'None' (index 0)")
        else:
            logger.debug(f"  Skipped setting model_combo index due to placeholder '{current_model_text_in_combo}'")

        self.target_lang_combo.blockSignals(False)
        self.source_lang_combo.blockSignals(False)
        self.model_combo.blockSignals(False)

        logger.debug(f"UI updated: Target Lang Code='{self.target_language}', Source Lang Code='{self.source_language}', Model='{self.selected_model}'")

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
        logger.debug(f"  Model to set: '{model_to_set}'")
        if model_to_set:
             model_idx = self.model_combo.findText(model_to_set)
             logger.debug(f"  Found model index: {model_idx}")
        else:

             model_idx = 0
             logger.debug(f"  Model is None, setting index to 0 ('None')")

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

    def _get_current_table(self) -> QTableWidget | QTableView | None:
        """
        Mevcut tab'daki tablo widget'ını döndür.
        
        Hem eski QTableWidget hem de yeni TranslationTableView (QTableView) desteklenir.
        """
        current_widget = self.tab_widget.currentWidget()
        # Hem QTableWidget hem QTableView destekleniyor
        if isinstance(current_widget, (QTableWidget, QTableView)):
            return current_widget
        return None

    def _get_current_file_data(self) -> ParsedFile | None:

        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index != -1:
            file_path = self.tab_data.get(current_tab_index)

            widget = self.tab_widget.widget(current_tab_index)
            widget_path = widget.property("filePath") if widget else None
            if file_path and file_path in self.file_data:

                if widget_path and file_path != widget_path:
                    logger.warning(f"Path mismatch between tab_data ('{file_path}') and widget ('{widget_path}') for index {current_tab_index}. Using tab_data path.")
                return self.file_data[file_path]
            elif widget_path and widget_path in self.file_data:

                 logger.warning(f"Correcting tab_data for index {current_tab_index} using widget path '{widget_path}'.")
                 self.tab_data[current_tab_index] = widget_path
                 return self.file_data[widget_path]

        return None

    def _get_current_translatable_items(self) -> list | None:

        data = self._get_current_file_data()
        return data.items if data else None

    def _get_current_item_index(self) -> int:

        data = self._get_current_file_data()

        return getattr(data, 'item_index', -1) if data else -1

    def _set_current_item_index(self, index: int):

        data = self._get_current_file_data()
        if data:
            current_index = getattr(data, 'item_index', -1)
            if current_index != index:
                data.item_index = index
                self._display_current_item_status() 

    def _is_current_tab_modified(self) -> bool:

        data = self._get_current_file_data()

        return data.is_modified if data else False

    def _set_current_tab_modified(self, modified: bool = True):

        data = self._get_current_file_data()
        if data:
            data.is_modified = modified

            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index != -1 and self.current_file_path:
                base_name = os.path.basename(data.output_path or self.current_file_path)
                new_tab_text = f"{base_name}*" if modified else base_name
                
                # Update tab text if it doesn't match target state
                if self.tab_widget.tabText(current_tab_index) != new_tab_text:
                    self.tab_widget.setTabText(current_tab_index, new_tab_text)

            self._update_ui_state()
            
            # Stage 11: Update TM suggestions
            if hasattr(self, 'tm_panel'):
                self.tm_panel.on_selection_changed()

    def _init_workspace(self):
        """
        Stage 14: Initialize Tabbed Workspace.
        Creates 5 main docks and organizes them into a tabbed layout.
        """
        self.workspace_docks = {}
        
        # 1. TRANSLATION DOCK
        self.translation_dock = QDockWidget(tr("workspace_translation"), self)
        self.translation_dock.setObjectName("dock_translation")
        
        # Move SearchWidget here (it was in left panel, now in Translation Dock)
        translation_container = QWidget()
        trans_layout = QVBoxLayout(translation_container)
        trans_layout.setContentsMargins(0, 0, 0, 0)
        
        # Instantiate SearchWidget using UIBuilder
        # Note: UIBuilder instance is local in __init__, but we need access to the method.
        # We can create a temporary builder or just call the method if it was static (it's not).
        # We access it via self.ui_builder if we saved it? We didn't save it in __init__ as an attribute.
        # We should probably save it in __init__.
        
        # FIX: Let's assume we can re-create UIBuilder temporarily or move logic.
        # But UIBuilder takes main_window.
        from gui.ui_builder import UIBuilder
        temp_builder = UIBuilder(self)
        self.search_replace_panel = temp_builder.build_search_panel()
        
        trans_layout.addWidget(self.search_replace_panel)
            
        self.translation_dock.setWidget(translation_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.translation_dock)
        self.workspace_docks['translation'] = self.translation_dock


        # 2. REVIEW DOCK
        self.review_dock = QDockWidget(tr("workspace_review"), self)
        self.review_dock.setObjectName("dock_review")
        review_container = QWidget()
        review_layout = QVBoxLayout(review_container)
        review_layout.setContentsMargins(0, 0, 0, 0)
        
        # Batch Summary
        self.batch_summary_panel = BatchSummaryPanel(self)
        self.batch_summary_panel.undo_requested.connect(self._handle_undo_requested)
        self.batch_summary_panel.open_review_requested.connect(self._handle_open_review)
        review_layout.addWidget(self.batch_summary_panel)
        
        # Review Panel
        self.review_panel = ReviewPanel(self)
        self.review_panel.request_navigation.connect(self._navigate_to_raw_index)
        review_layout.addWidget(self.review_panel)
        
        self.review_dock.setWidget(review_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.review_dock)
        self.workspace_docks['review'] = self.review_dock


        # 3. QUALITY DOCK (Tabs: QA, Preflight)
        self.quality_dock = QDockWidget(tr("workspace_quality"), self)
        self.quality_dock.setObjectName("dock_quality")
        quality_tabs = QTabWidget()
        
        # QA Panel
        self.qa_panel = QAPanel(self)
        self.qa_panel.request_navigation.connect(self._navigate_to_raw_index)
        quality_tabs.addTab(self.qa_panel, tr("qa_title"))
        
        # Preflight Panel
        self.preflight_panel = PreflightPanel(self)
        self.preflight_panel.navigate_requested.connect(self.navigate_to_file_line)
        quality_tabs.addTab(self.preflight_panel, tr("pf_title"))
        
        self.quality_dock.setWidget(quality_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.quality_dock)
        self.workspace_docks['quality'] = self.quality_dock


        # 4. CONSISTENCY DOCK (Tabs: Glossary, TM)
        self.consistency_dock = QDockWidget(tr("workspace_consistency"), self)
        self.consistency_dock.setObjectName("dock_consistency")
        consistency_tabs = QTabWidget()
        
        # Glossary
        self.glossary_panel = GlossaryPanel(self)
        consistency_tabs.addTab(self.glossary_panel, tr("glossary_title"))
        
        # TM
        from core.tm_store import init_tm_manager
        self.tm_panel = TMPanel(self)
        consistency_tabs.addTab(self.tm_panel, tr("tm_title"))
        
        self.consistency_dock.setWidget(consistency_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.consistency_dock)
        self.workspace_docks['consistency'] = self.consistency_dock


        # 5. SETTINGS DOCK (Tabs: Plugins, General??)
        self.settings_dock = QDockWidget(tr("workspace_settings"), self)
        self.settings_dock.setObjectName("dock_settings")
        settings_tabs = QTabWidget()
        
        # Plugins (Stage 7.1)
        # We need a plugin settings widget. 
        # Using PluginSettingsWidget if available, or placeholder.
        try:
             # Pass self.settings dict? PluginSettingsWidget expects settings_model object?
             # Looking at widget: self.settings = settings_model then self.settings.get() calls
             # It treats it as a dict mostly or object with get(). RenForgeGUI.settings is a dict.
             # So passing self.settings works perfectly if it expects a dict-like.
             # Wait, the error said "missing 1 required positional argument".
             # So we must pass self.settings.
             self.plugin_settings_panel = PluginSettingsWidget(self.settings)
             settings_tabs.addTab(self.plugin_settings_panel, "Plugins")
        except Exception as e:
             logger.error(f"Failed to init Plugin Settings for dock: {e}")
             settings_tabs.addTab(QLabel(f"Plugin Error: {e}"), "Plugins")
             
        # General Settings Placeholder (User uses dialog normally, but maybe quick settings here?)
        settings_tabs.addTab(QLabel("See File > Settings for more."), "General")
             
        self.settings_dock.setWidget(settings_tabs)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.settings_dock)
        self.workspace_docks['settings'] = self.settings_dock
        
        
        # TABIFY ALL DOCKS in specific order
        # We want: [Translation] [Review] [Quality] [Consistency] [Settings]
        # tabifyDockWidget(first, second) puts second on top of first.
        # Sequence:
        self.tabifyDockWidget(self.translation_dock, self.review_dock)
        self.tabifyDockWidget(self.review_dock, self.quality_dock)
        self.tabifyDockWidget(self.quality_dock, self.consistency_dock)
        self.tabifyDockWidget(self.consistency_dock, self.settings_dock)
        
        # Raise Translation by default
        self.translation_dock.raise_()
        
        # Helper aliases for legacy compatibility (tests/existing code might check self.qa_dock)
        self.qa_dock = self.quality_dock
        self.preflight_dock = self.quality_dock
        self.tm_dock = self.consistency_dock
        self.glossary_dock = self.consistency_dock
        
        # Restore dock layout state (if saved)
        self._restore_workspace_state()

    def _restore_workspace_state(self):
        """Restore dock layout and visibility from settings."""
        state_hex = self.settings.get("window_state")
        if state_hex:
            try:
                from PySide6.QtCore import QByteArray
                state = QByteArray.fromHex(str(state_hex).encode())
                self.restoreState(state)
                logger.debug("Workspace state restored from settings.")
            except Exception as e:
                logger.warning(f"Failed to restore workspace state: {e}")
        else:
             logger.debug("No workspace state saved used defaults.")

    def _navigate_to_raw_index(self, raw_index: int):
        current_table = self._get_current_table()
        if not current_table: return
        
        # QTableView/QTableWidget uyumlu row_count
        model = current_table.model() if hasattr(current_table, 'model') else None
        if model:
            row_count = model.rowCount()
        elif hasattr(current_table, 'rowCount'):
            row_count = current_table.rowCount()
        else:
            return
        
        found_row = -1
        for r in range(row_count):
            # QTableView için model.data(), QTableWidget için item().data()
            if model:
                idx = model.index(r, 0)
                item_data_idx = model.data(idx, Qt.ItemDataRole.UserRole)
            elif hasattr(current_table, 'item'):
                item = current_table.item(r, 0)
                item_data_idx = item.data(Qt.ItemDataRole.UserRole) if item else None
            else:
                continue
                
            if item_data_idx == raw_index:
                found_row = r
                break
                
        if found_row != -1:
            current_table.selectRow(found_row)
            # QTableView için scrollTo(), QTableWidget için scrollToItem()
            if hasattr(current_table, 'scrollTo') and model:
                from PySide6.QtWidgets import QAbstractItemView
                current_table.scrollTo(model.index(found_row, 0), QAbstractItemView.ScrollHint.PositionAtCenter)
            elif hasattr(current_table, 'scrollToItem') and hasattr(current_table, 'item'):
                from PySide6.QtWidgets import QAbstractItemView
                current_table.scrollToItem(current_table.item(found_row, 0), QAbstractItemView.ScrollHint.PositionAtCenter)
        else:
            self.statusBar().showMessage("QA: Item not visible in current view.", 3000)

    def navigate_to_file_line(self, file_path: str, line_num: int):
        """Open file and scroll to line."""
        # 1. Open file using AppController
        if hasattr(self, '_app_controller') and self._app_controller:
            self._app_controller.open_file(file_path, mode="translate")
        else:
            logger.error("Cannot navigate: AppController not initialized")
            return
        
        # 2. Find the tab for this file
        # We process events to ensure UI updates if file open was async/queued
        QApplication.instance().processEvents()
        
        found_tab = False
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            # Check tab.file_path (FileTableView has this property)
            if hasattr(tab, 'file_path') and os.path.normpath(tab.file_path) == os.path.normpath(file_path):
                self.tab_widget.setCurrentIndex(i)
                found_tab = True
                
                # Scroll to line
                if hasattr(tab, 'scroll_to_line'):
                     tab.scroll_to_line(line_num)
                break
                
        if not found_tab:
            logger.warning(f"Tab not found for {file_path} after open attempt.")


    def _handle_open_review(self):
        """Show and refresh the review panel/dock."""
        if not self.review_dock:
            return
            
        self.review_dock.show()
        self.review_dock.raise_()
        self.review_panel.refresh_changes()
        
    def _handle_export_pack(self):
        """Show Export Pack dialog."""
        
        # Stage 13: Preflight Recommendation
        if hasattr(self, 'preflight_panel'):
            # Check if recently run or just prompt
            # For now, always prompt if block_on_error (or user not disabled check)
            
            # Simple prompt
            reply = QMessageBox.question(self, tr("pf_export_prompt_title"), tr("pf_export_prompt_msg"),
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                       
            if reply == QMessageBox.StandardButton.Yes:
                self.preflight_dock.show()
                self.preflight_dock.raise_()
                self.preflight_panel.start_scan()
                return # Stop export to let user see results
                
            # If user said No, proceed. 
            # Ideally we check if previous run had Critical errors? 
            # But "No" implies "I check myself or I don't care".
            
        from gui.dialogs.pack_dialogs import ExportDialog
        dialog = ExportDialog(self)
        dialog.exec()
        
    def _handle_import_pack(self):
        """Show Import Pack dialog."""
        from gui.dialogs.pack_dialogs import ImportDialog
        dialog = ImportDialog(self)
        dialog.exec()

    def _update_ui_state(self):

        current_table = self._get_current_table()
        current_file_data = self._get_current_file_data()
        current_items = self._get_current_translatable_items()
        current_item_idx = self._get_current_item_index()

        # PERFORMANCE FIX: Don't check internet in update_ui_state loop!
        # It blocks the UI. We check on action execution.
        # is_online = ai.is_internet_available() 
        pass

        has_open_tabs = self.tab_widget.count() > 0
        self.file_is_loaded = has_open_tabs

        tab_is_active = has_open_tabs and current_table is not None and current_file_data is not None
        tab_has_items = tab_is_active and current_items is not None and len(current_items) > 0
        tab_is_modified = self._is_current_tab_modified()
        project_is_open = bool(self.current_project_path) 

        self.save_action.setEnabled(tab_is_modified)
        self.save_as_action.setEnabled(tab_is_active)
        any_modified = any(data.is_modified for data in self.file_data.values())
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
                 
        # Removed search_view_button logic (moved to Translation Dock)

        if current_table:
             current_table.setEnabled(tab_has_items)

        selected_rows = []
        if current_table:
            selected_indices = current_table.selectedIndexes()
            selected_rows = sorted(list(set(index.row() for index in selected_indices)))

        has_selection = len(selected_rows) > 0
        single_item_selected = has_selection and current_item_idx >= 0 and tab_has_items
        
        # Debug log: Selection durumu
        logger.debug(f"[_update_ui_state] Selection: selectedRows={len(selected_rows)}, current_item_idx={current_item_idx}, has_selection={has_selection}, single_selected={single_item_selected}") 

        can_revert_selected = False
        if has_selection and current_items:
            # Check if any selected row has text modifications
            can_revert_selected = any(
                0 <= row_idx < len(current_items) and current_items[row_idx].is_modified_session
                for row_idx in selected_rows
            )

        if hasattr(self, 'revert_btn'):
            self.revert_btn.setEnabled(can_revert_selected)
        
        can_revert_all = False
        if current_items:
            # Check if ANY item has text modifications (ignore breakpoints for Revert All)
            can_revert_all = any(item.is_modified_session for item in current_items)
            
        if hasattr(self, 'revert_all_btn'):
            self.revert_all_btn.setEnabled(can_revert_all)

        can_revert_current_single = False
        if single_item_selected and current_items and 0 <= current_item_idx < len(current_items):
             can_revert_current_single = current_items[current_item_idx].get('is_modified_session', False)
        self.revert_action_menu.setEnabled(single_item_selected and can_revert_current_single)

        self.prev_action.setEnabled(single_item_selected and current_item_idx > 0)

        self.next_action.setEnabled(tab_has_items and single_item_selected and current_item_idx < len(current_items) - 1)

        has_breakpoints_set = False
        if tab_has_items and current_file_data and current_file_data.breakpoints:
            has_breakpoints_set = bool(current_file_data.breakpoints)

        self.go_to_bp_btn.setEnabled(has_breakpoints_set)
        self.next_bp_action.setEnabled(has_breakpoints_set)
        self.clear_bp_btn.setEnabled(has_breakpoints_set)
        self.clear_bp_action_menu.setEnabled(has_breakpoints_set)
        self.toggle_bp_btn.setEnabled(single_item_selected)
        self.toggle_bp_action_menu.setEnabled(single_item_selected)

        ai_available = not ai.no_ai 
        logger.debug(f"[_update_ui_state] AI available check: ai.no_ai = {ai.no_ai} -> ai_available = {ai_available}") 
        can_use_ai_edit = single_item_selected and ai_available
        can_use_batch_ai = has_selection and ai_available  # Batch AI için selection yeterli
        self.ai_edit_btn.setEnabled(can_use_ai_edit)
        self.ai_edit_action_menu.setEnabled(can_use_ai_edit)
        
        # Batch AI butonu
        if hasattr(self, 'batch_ai_btn'):
            self.batch_ai_btn.setEnabled(can_use_batch_ai)
        
        logger.debug(f"[_update_ui_state] AI buttons enabled: single={can_use_ai_edit}, batch={can_use_batch_ai} (single_selected={single_item_selected}, has_selection={has_selection}, ai_available={ai_available})") 

        _translator_module = ai._lazy_import_translator() 
        translator_library_ok = _translator_module is not None
        # PERFORMANCE FIX: Don't check internet here. Assume online for UI state.
        # Check happens on click.
        translator_available = translator_library_ok 
        logger.debug(f"[_update_ui_state] GTranslate check: library_ok={translator_library_ok} -> translator_available={translator_available}") 
        can_use_gtranslate = single_item_selected and translator_available
        can_use_batch_gtranslate = has_selection and translator_available
        self.gt_translate_btn.setEnabled(can_use_gtranslate)
        self.gt_action_menu.setEnabled(can_use_gtranslate)
        self.batch_gt_btn.setEnabled(can_use_batch_gtranslate)
        logger.debug(f"[_update_ui_state] GTranslate buttons enabled: single={can_use_gtranslate}, batch={can_use_batch_gtranslate} (single_selected={single_item_selected}, has_selection={has_selection}, translator_available={translator_available})") 

        is_direct_mode = tab_is_active and current_file_data.mode == "direct"

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
            current_mode = current_file_data.mode

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
            if data.is_modified:
                base_name = os.path.basename(data.output_path or file_path)
                modified_files_info.append((base_name, file_path))

        should_exit = False 
        user_decision = "cancel" 

        if modified_files_info:
            file_list_str = "\n - ".join([info[0] for info in modified_files_info])
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr("unsaved_changes_title"))
            msg_box.setText(tr("close_unsaved_files", files=file_list_str))
            msg_box.setInformativeText(tr("close_save_confirm"))
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
            # FIX: Load fresh settings to avoid overwriting changes made by other components (e.g., Glossary)
            current_settings = load_settings()
            
            is_max = self.isMaximized()
            geo = self.geometry()
            
            current_settings["window_maximized"] = is_max
            if not is_max:
                current_settings["window_size_w"] = geo.width()
                current_settings["window_size_h"] = geo.height()
            
            # Stage 14.5: Save Window State (Docks/Toolbar layout)
            try:
                state = self.saveState()
                current_settings["window_state"] = state.toHex().data().decode()
            except Exception as e:
                 logger.warning(f"Failed to serialize window state: {e}")

            if not save_settings(current_settings): 
                 logger.warning("Could not save settings (including window geometry) on exit.")
            else:
                 logger.debug("Window geometry saved.")

            event.accept() 
        else:
             event.ignore() 

if __name__ == '__main__':
    if not GUI_AVAILABLE:
        logger.critical("GUI is not available. Exiting.")
        sys.exit(1)

    app = QApplication(sys.argv)

    main_window = RenForgeGUI()
    main_window.show()
    sys.exit(app.exec())