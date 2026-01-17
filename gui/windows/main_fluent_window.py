# -*- coding: utf-8 -*-
"""
RenForge Main Fluent Window

Modern Fluent UI based main window using QFluentWidgets.
Replaces the legacy RenForgeGUI as the default application window.
"""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QStackedWidget
)
from PySide6.QtGui import QIcon

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF,
    setTheme, Theme, isDarkTheme
)

from renforge_logger import get_logger

logger = get_logger("gui.windows.main_fluent_window")

from controllers.review_controller import ReviewController


class MainFluentWindow(FluentWindow):
    """
    Modern Fluent UI main window for RenForge.
    
    Layout:
    - Left: Navigation sidebar (pages)
    - Center: QTableView-based content area
    - Right: Inspector panel (Row/Batch/Log tabs)
    
    Emits the same signals as RenForgeGUI for controller compatibility.
    """
    
    # ==========================================================================
    # VIEW SIGNALS (matching RenForgeGUI for bootstrap compatibility)
    # ==========================================================================
    
    # File operations
    open_project_requested = Signal()
    open_file_requested = Signal()
    save_requested = Signal()
    save_as_requested = Signal()
    save_all_requested = Signal()
    close_tab_requested = Signal(int)  # tab index
    exit_requested = Signal()
    file_loaded = Signal(str, str, list, list)  # path, mode, items, lines
    
    # Navigation
    tab_changed = Signal(int)  # tab index
    item_selected = Signal(int)  # item index
    
    # Translation operations
    translate_ai_requested = Signal()
    translate_google_requested = Signal()
    batch_ai_requested = Signal()
    batch_google_requested = Signal()
    
    # Settings changes
    target_language_changed = Signal(str)  # language code
    source_language_changed = Signal(str)  # language code
    model_changed = Signal(str)  # model name
    
    # Project/File lifecycle (for FilesPage and other listeners)
    project_opened = Signal(str)  # project root path
    file_opened = Signal(str)  # file path (emitted when NEW file opened)
    file_closed = Signal(str)  # file path (emitted when file closed)
    active_file_changed = Signal(str)  # file path (emitted on switch, empty if none)
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize state (compatible with RenForgeGUI)
        self.file_data = {}
        self.tab_data = {}
        self.current_file_path = None
        self.last_open_directory = None  # For file dialog
        self.last_open_project_directory = None  # For project dialog
        self.current_project_path = None  # Current project path
        self._block_item_changed_signal = False  # For batch updates
        
        # Multi-file tab management
        self._file_tabs = {}  # {file_path: {'model': Model, 'proxy': Proxy, 'tab_idx': int}}
        
        # Settings reference (from SettingsModel singleton)
        from models.settings_model import SettingsModel
        self.settings = SettingsModel.instance()
        
        # Controllers (set by bootstrap)
        self._app_controller = None
        self.batch_controller = None
        self.project_controller = None
        
        # Setup window
        self._setup_window()
        self._init_compatibility_widgets()  # Stub widgets for main.py compatibility
        self._init_navigation()
        self._init_content_area()
        self._init_shortcuts()
        
        logger.info("MainFluentWindow initialized")
    
    def _init_compatibility_widgets(self):
        """Create stub widgets for main.py and legacy code compatibility."""
        from qfluentwidgets import ComboBox
        from PySide6.QtWidgets import QTabWidget
        
        # Stub combo boxes - REMOVED because they conflict with properties
        # The properties now proxy to SettingsPage widgets
        
        # Stub tab widget for legacy code
        self.tab_widget = QTabWidget()
        self.tab_widget.hide()
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("RenForge")
        self.resize(1400, 900)
        
        # Center window on screen
        self._center_on_screen()
        
        # Set initial theme
        setTheme(Theme.DARK)
        
        # Configure title bar if available
        if hasattr(self, 'titleBar') and self.titleBar:
            # Set window title in title bar
            self.titleBar.setTitle("RenForge")
            
            # Delay title bar button connections - buttons may not be ready on first init
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._connect_titlebar_buttons)
    
    def showEvent(self, event):
        """Handle window show event - ensure proper activation."""
        super().showEvent(event)
        # Activate window on first show to ensure title bar buttons work
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._activate_window)
    
    def _connect_titlebar_buttons(self):
        """Verify title bar buttons are working (qframelesswindow should handle this)."""
        if not hasattr(self, 'titleBar') or not self.titleBar:
            logger.warning("No titleBar available for button check")
            return
        
        # qframelesswindow already connects buttons to window functions
        # Just log that we've verified they exist
        if hasattr(self.titleBar, 'closeBtn') and self.titleBar.closeBtn:
            logger.debug(f"closeBtn verified: {self.titleBar.closeBtn.isEnabled()}")
        if hasattr(self.titleBar, 'minBtn') and self.titleBar.minBtn:
            logger.debug(f"minBtn verified: {self.titleBar.minBtn.isEnabled()}")
    
    def _center_on_screen(self):
        """Center the window on the primary screen."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QScreen
        
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
    
    def _activate_window(self):
        """Activate window to ensure all UI elements are responsive."""
        self.activateWindow()
        self.raise_()
        # CRITICAL: keep the custom title bar above the central widgets.
        # On first show, the central widget can temporarily overlap the title bar
        # (z-order) which makes the minimize/close buttons ignore clicks until the
        # user interacts with the UI (e.g., expanding the navigation).
        try:
            tb = getattr(self, 'titleBar', None)
            if tb is not None:
                tb.raise_()
                # Some titleBar implementations expose minBtn/closeBtn
                for attr in ('minBtn', 'closeBtn', 'maxBtn'):
                    btn = getattr(tb, attr, None)
                    if btn is not None:
                        btn.raise_()
        except Exception:
            pass

        self.update()
        # Force process events to ensure title bar is responsive
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        logger.debug("Window activated and updated")
        
    def _init_navigation(self):
        """Initialize navigation sidebar with pages."""
        # Import pages (lazy to avoid circular imports)
        from gui.pages.page_files import FilesPage
        from gui.pages.page_translate import TranslatePage
        from gui.pages.page_review import ReviewPage
        from gui.pages.page_tm import TMPage
        from gui.pages.page_glossary import GlossaryPage
        from gui.pages.page_packaging import PackagingPage
        from gui.pages.page_settings import SettingsPage
        from gui.pages.page_health import HealthPage
        
        # Create page instances
        self.files_page = FilesPage(self)
        self.translate_page = TranslatePage(self)
        self.review_page = ReviewPage(self)
        self.tm_page = TMPage(self)
        self.glossary_page = GlossaryPage(self)
        self.packaging_page = PackagingPage(self)
        self.settings_page = SettingsPage(self)
        self.health_page = HealthPage(self)
        
        # Add pages to navigation
        # Primary workflow pages
        self.addSubInterface(
            self.files_page, 
            FIF.FOLDER, 
            "Dosyalar",
            NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.translate_page, 
            FIF.LANGUAGE, 
            "Çeviri",
            NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.review_page, 
            FIF.VIEW, 
            "İnceleme",
            NavigationItemPosition.TOP
        )
        
        # Tools section
        self.addSubInterface(
            self.tm_page, 
            FIF.HISTORY, 
            "TM", 
            NavigationItemPosition.SCROLL
        )
        self.addSubInterface(
            self.glossary_page, 
            FIF.DICTIONARY, 
            "Sözlük",
            NavigationItemPosition.SCROLL
        )
        self.addSubInterface(
            self.packaging_page, 
            FIF.ZIP_FOLDER, 
            "Paketleme",
            NavigationItemPosition.SCROLL
        )
        
        # Health dashboard
        self.addSubInterface(
            self.health_page,
            FIF.HEART,
            "Sağlık",
            NavigationItemPosition.SCROLL
        )
        
        # Settings at bottom
        self.addSubInterface(
            self.settings_page, 
            FIF.SETTING, 
            "Ayarlar",
            NavigationItemPosition.BOTTOM
        )
        
        # Initialize Controllers
        self.review_controller = ReviewController(self)
        
        # Connect Health page signals
        self._connect_health_signals()
        
        logger.debug("Navigation initialized with 8 pages")
    
    def _init_content_area(self):
        """Initialize the right-side inspector panel with splitter."""
        from gui.panels.inspector_panel import InspectorPanel
        
        # Create inspector panel
        self.inspector = InspectorPanel(self)
        
        # Connect visibility change to settings save
        self.inspector.visibility_changed.connect(self._on_inspector_visibility_changed)
        
        # Connect navigation (Go to Line) with safe pattern
        try:
            self.inspector.navigate_requested.disconnect(self._on_navigate_requested)
        except Exception:
            pass
        self.inspector.navigate_requested.connect(self._on_navigate_requested)
        self.inspector.navigate_row_requested.connect(self._on_navigate_row_requested)
        
        # Connect retry line (New)
        # We need to access batch controller via gui_handlers or direct property
        # Since main window initializes controllers later or via gui_action_handler,
        # we might need to defer connection or proxy it.
        # But wait, self.gui_handlers is initialized in _init_compatibility_widgets -> NO
        # gui_handlers is in main.py, but MainFluentWindow gets references?
        # Let's check how batch_controller is accessed.
        # It's usually self.gui_handlers.batch_controller (if main.py passes it) or created here.
        # The prompt says main.py creates handlers.
        # Actually MainFluentWindow.review_controller is created here. 
        # But BatchController is usually part of GuiActionHandler or separate.
        # Let's defer connection to valid point or use a proxy method.
        # Ideally, we add a proxy method _on_retry_line_requested here.
        
        self.inspector.retry_line_requested.connect(self._on_retry_line_requested)
        
        # Add to main layout (right side)
        # FluentWindow uses hBoxLayout for [Navigation, StackedWidget]
        if hasattr(self, 'hBoxLayout'):
            self.hBoxLayout.addWidget(self.inspector)
            logger.debug("Added InspectorPanel to hBoxLayout")
        else:
            logger.warning("MainFluentWindow: hBoxLayout not found, InspectorPanel may float")
        
        # CRITICAL FIX: Register Inspector panel as hit-test visible
        # QFluentWidgets/qframelesswindow intercepts mouse clicks for window dragging.
        # Without this, clicks on Inspector tabs get intercepted by titlebar hit test.
        self._register_inspector_hit_test_visible()
        
        # Connect page change to inspector visibility
        # FluentWindow has stackedWidget for pages
        if hasattr(self, 'stackedWidget'):
            self.stackedWidget.currentChanged.connect(self._on_page_changed)

    def _on_navigate_requested(self, line_num: int):
        """Handle navigation request from Inspector (Go to Line)."""
        import time
        
        # Debounce/Guard against double triggers
        current_time = time.time()
        last_line = getattr(self, '_last_nav_line', None)
        last_time = getattr(self, '_last_nav_time', 0)
        
        if last_line == line_num and (current_time - last_time < 0.5):
            logger.debug(f"Navigation to line {line_num} ignored (duplicate/debounce)")
            return
            
        self._last_nav_line = line_num
        self._last_nav_time = current_time
        
        logger.info(f"Navigating to line {line_num}")
        
        # Ensure we are on Translate page
        if hasattr(self, 'translate_page') and self.stackedWidget.currentWidget() != self.translate_page:
            # Switch to translate page
            # We should update navigation interface too
            self.stackedWidget.setCurrentWidget(self.translate_page)
            # Update nav selection if possible (optional)
            
        # Forward to translate page
        if hasattr(self, 'translate_page'):
            # Check if page has select_line method
            if hasattr(self.translate_page, 'select_line'):
                self.translate_page.select_line(line_num)
            # Or table widget directly
            elif hasattr(self.translate_page, 'table_widget'):
                 # We need to implement select_line in table widget
                 if hasattr(self.translate_page.table_widget, 'select_line'):
                     self.translate_page.table_widget.select_line(line_num)
                 else:
                     logger.warning("TranslationTableWidget missing select_line method")
        else:
             logger.warning("Translate page not available for navigation")
        
        # Restore layout state from settings
        self._restore_layout_state()
        
        # NOTE: Log bridge is now installed in app_bootstrap.py using
        # gui.logging.inspector_log_handler for cleaner architecture
        
        # The inspector needs to be accessible from pages
        # Pages will call self.window().inspector.show_row(...) etc.
        logger.debug("Inspector panel initialized")
    
    def _register_inspector_hit_test_visible(self):
        """
        Register Inspector panel and its interactive widgets as hit-test visible.
        
        This prevents qframelesswindow/titlebar from intercepting mouse clicks
        on Inspector tabs and other controls.
        
        Root Cause: QFluentWidgets FluentWindow extends qframelesswindow which
        uses nativeEvent/mouse hooks for window dragging. By default, any widget
        in the titlebar region gets its clicks intercepted. We must explicitly
        mark interactive widgets as "hit test visible" to allow normal mouse handling.
        """
        if not hasattr(self, 'titleBar'):
            logger.debug("No titleBar found, skipping hit-test registration")
            return
        
        try:
            # Register the entire Inspector panel
            self.titleBar.setHitTestVisible(self.inspector)
            logger.debug("Registered Inspector panel as hit-test visible")
            
            # Also register specific interactive widgets inside Inspector
            # Tab bar is the main problem area
            if hasattr(self.inspector, 'tabs'):
                tabs = self.inspector.tabs
                self.titleBar.setHitTestVisible(tabs)
                logger.debug("Registered Inspector tabs (QTabWidget) as hit-test visible")
                
                # Register the tab bar specifically (the actual clickable tabs)
                if hasattr(tabs, 'tabBar'):
                    tab_bar = tabs.tabBar()
                    self.titleBar.setHitTestVisible(tab_bar)
                    logger.debug("Registered Inspector tabBar as hit-test visible")
            
            # Register Inspector header (pin button etc)
            if hasattr(self.inspector, 'header_widget'):
                self.titleBar.setHitTestVisible(self.inspector.header_widget)
                logger.debug("Registered Inspector header as hit-test visible")
                
        except Exception as e:
            logger.warning(f"Failed to register Inspector as hit-test visible: {e}")
    
    def _on_page_changed(self, index: int):
        """Handle page change - show/hide inspector based on current page."""
        if not hasattr(self, 'inspector'):
            return
        
        current_widget = self.stackedWidget.currentWidget() if hasattr(self, 'stackedWidget') else None
        
        # Show inspector only on TranslatePage and ReviewPage
        # But respect user's manual hide setting
        from models.settings_model import SettingsModel
        settings = SettingsModel.instance()
        if not getattr(settings, 'inspector_visible', True):
            self.inspector.setVisible(False)
            return
        
        show_inspector = False
        if current_widget:
            widget_name = current_widget.objectName()
            if widget_name in ("TranslatePage", "ReviewPage"):
                show_inspector = True
        
        self.inspector.setVisible(show_inspector)
        logger.debug(f"Page changed to index {index}, inspector visible: {show_inspector}")
    
    def _on_inspector_visibility_changed(self, visible: bool):
        """Handle inspector visibility toggle - save to settings."""
        from models.settings_model import SettingsModel
        settings = SettingsModel.instance()
        settings.inspector_visible = visible
        settings.save()
        logger.debug(f"Inspector visibility saved: {visible}")
    
    def _restore_layout_state(self):
        """Restore layout state from settings."""
        try:
            # Inspector visibility
            if hasattr(self, 'inspector'):
                visible = self.settings.inspector_visible
                width = self.settings.inspector_width
                self.inspector.setVisible(visible)
                if width > 0:
                    self.inspector.setFixedWidth(width)
                    # Reset fixed width to allow resize
                    self.inspector.setMinimumWidth(220)
                    self.inspector.setMaximumWidth(500)
            
            logger.debug("Layout state restored from settings")
        except Exception as e:
            logger.warning(f"Failed to restore layout state: {e}")
    
    def _save_layout_state(self):
        """Save current layout state to settings."""
        try:
            # Inspector width
            if hasattr(self, 'inspector') and self.inspector.isVisible():
                self.settings.inspector_width = self.inspector.width()
            
            self.settings.save()
            logger.debug("Layout state saved to settings")
        except Exception as e:
            logger.warning(f"Failed to save layout state: {e}")
    
    def closeEvent(self, event):
        """Handle window close - save layout state."""
        self._save_layout_state()
        super().closeEvent(event)
    
    # =========================================================================
    # IMainView Protocol - Compatibility methods
    # =========================================================================
    
    def _get_current_file_data(self):
        """Get current file's ParsedFile data."""
        if self.current_file_path and self.current_file_path in self.file_data:
            return self.file_data[self.current_file_path]
        return None
    
    def _update_ui_state(self):
        """Update UI state based on current data."""
        # Delegate to pages if needed
        pass
    
    
    def _init_shortcuts(self):
        """Initialize global keyboard shortcuts via ShortcutManager."""
        from gui.shortcuts.shortcut_manager import ShortcutManager
        mgr = ShortcutManager.instance()
        
        # Bind actions
        # Using WindowShortcut context so they work globally but we filter in handlers
        mgr.bind(self, "translate.selected", self._on_shortcut_translate_selected)
        mgr.bind(self, "translate.batch", self._on_shortcut_batch_translate)
        mgr.bind(self, "batch.cancel", self._on_shortcut_cancel)
        
        mgr.bind(self, "inspector.toggle", self._on_shortcut_inspector_toggle)
        mgr.bind(self, "inspector.log", self._on_shortcut_inspector_log)
        mgr.bind(self, "inspector.batch", self._on_shortcut_inspector_batch)
        
        # Error Navigation (Stage 5.5)
        # We manually register these as they might not be in predefined shortcuts list unless added
        # Using QShortcut directly for simple F-keys or ensuring mgr supports custom
        # But since mgr wraps QShortcut, let's use QShortcut directly here for F8 if not in manager config
        # OR better, if manager allows binding arbitrary keys without config name.
        # Looking at ShortcutManager usage... valid keys needed? 
        # For safety and speed, I will use QShortcut directly in this method for these specifics.
        
        self.next_error_key = QShortcut(QKeySequence(Qt.Key_F8), self)
        self.next_error_key.activated.connect(self._on_manual_next_error)
        
        self.prev_error_key = QShortcut(QKeySequence(Qt.ShiftModifier | Qt.Key_F8), self)
        self.prev_error_key.activated.connect(self._on_manual_prev_error)
        
        logger.debug("Shortcuts initialized")

    def _on_shortcut_translate_selected(self):
        """Handle translate.selected shortcut (Ctrl+Enter)."""
        # SCOPE: Only active if TranslatePage is visible
        if not self._is_page_visible("TranslatePage"):
            return
            
        # Trigger action on page
        if hasattr(self, 'translate_page'):
            self.translate_page._on_translate_selected()

    def _on_shortcut_batch_translate(self):
        """Handle translate.batch shortcut (Ctrl+Shift+Enter)."""
        # SCOPE: Only active if TranslatePage is visible
        if not self._is_page_visible("TranslatePage"):
            return
            
        # Trigger action on page
        if hasattr(self, 'translate_page'):
            self.translate_page._on_batch_translate()

    def _on_shortcut_cancel(self):
        """Handle batch.cancel shortcut (Esc)."""
        # GUARD: Don't consume Esc if user is typing in a text input
        from PySide6.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
            return

        # Trigger cancel
        if hasattr(self, 'translate_page'):
            self.translate_page._on_cancel()

    def _on_shortcut_inspector_toggle(self):
        """Handle inspector.toggle shortcut (F6)."""
        if hasattr(self, 'inspector'):
            visible = not self.inspector.isVisible()
            self.inspector.setVisible(visible)
            # Update settings
            from models.settings_model import SettingsModel
            SettingsModel.instance().inspector_visible = visible
            SettingsModel.instance().save()

    def _on_shortcut_inspector_log(self):
        """Handle inspector.log shortcut (Ctrl+L)."""
        self._ensure_inspector_visible()
        if hasattr(self, 'inspector'):
            # Switch to Log tab (index 2)
            self.inspector.tabs.setCurrentIndex(2)

    def _on_shortcut_inspector_batch(self):
        """Handle inspector.batch shortcut (Ctrl+1)."""
        self._ensure_inspector_visible()
        if hasattr(self, 'inspector'):
            # Switch to Batch tab (index 1)
            self.inspector.tabs.setCurrentIndex(1)
            
    def _ensure_inspector_visible(self):
        """Helper to show inspector if hidden."""
        if hasattr(self, 'inspector') and not self.inspector.isVisible():
            self.inspector.setVisible(True)
            from models.settings_model import SettingsModel
            SettingsModel.instance().inspector_visible = True
            SettingsModel.instance().save()

    def _is_page_visible(self, page_object_name: str) -> bool:
        """Check if a specific page is currently visible."""
        if hasattr(self, 'stackedWidget'):
            current = self.stackedWidget.currentWidget()
            return current and current.objectName() == page_object_name
        return False

    # =========================================================================
    # HEALTH PAGE SIGNALS (Stage 8)
    # =========================================================================
    
    def _connect_health_signals(self):
        """Connect Health page signals for navigation and actions."""
        if not hasattr(self, 'health_page'):
            return
        
        self.health_page.navigate_to_translate.connect(self._on_health_navigate_translate)
        self.health_page.navigate_to_first_error.connect(self._on_health_goto_first_error)
        self.health_page.navigate_to_first_qc.connect(self._on_health_goto_first_qc)
        self.health_page.filter_by_error_category.connect(self._on_health_filter_errors)
        self.health_page.filter_by_qc_code.connect(self._on_health_filter_qc)
        
        # Stage 8.2: Row-specific navigation with filter toggle
        self.health_page.navigate_to_row_requested.connect(self._on_health_navigate_to_row)
        
        logger.debug("Health page signals connected")
    
    def _on_health_navigate_translate(self):
        """Navigate to Translate page from Health."""
        if hasattr(self, 'translate_page'):
            self.switchTo(self.translate_page)
    
    def _on_health_goto_first_error(self):
        """Navigate to first error row."""
        from core.run_history_store import RunHistoryStore
        
        # Get first error row from model
        model = self._get_table_model()
        store = RunHistoryStore.instance()
        row_id = store.get_first_error_row_id(model)
        
        if row_id is not None:
            # Navigate to Translate page
            if hasattr(self, 'translate_page'):
                self.switchTo(self.translate_page)
                # Enable error filter
                if hasattr(self.translate_page, 'error_filter_checkbox'):
                    self.translate_page.error_filter_checkbox.setChecked(True)
                # Select row
                if hasattr(self.translate_page, 'select_row_by_index'):
                    self.translate_page.select_row_by_index(row_id)
    
    def _on_health_goto_first_qc(self):
        """Navigate to first QC issue row."""
        from core.run_history_store import RunHistoryStore
        
        # Get first QC row from model
        model = self._get_table_model()
        store = RunHistoryStore.instance()
        row_id = store.get_first_qc_row_id(model)
        
        if row_id is not None:
            # Navigate to Translate page
            if hasattr(self, 'translate_page'):
                self.switchTo(self.translate_page)
                # Enable QC filter
                if hasattr(self.translate_page, 'qc_checkbox'):
                    self.translate_page.qc_checkbox.setChecked(True)
                # Select row
                if hasattr(self.translate_page, 'select_row_by_index'):
                    self.translate_page.select_row_by_index(row_id)
    
    def _on_health_filter_errors(self, category: str):
        """Filter by error category and navigate to Translate."""
        if hasattr(self, 'translate_page'):
            self.switchTo(self.translate_page)
            # Enable error filter
            if hasattr(self.translate_page, 'error_filter_checkbox'):
                self.translate_page.error_filter_checkbox.setChecked(True)
            # TODO: Could set specific category filter if implemented
            logger.info(f"Filtering by error category: {category}")
    
    def _on_health_filter_qc(self, code: str):
        """Filter by QC code and navigate to Translate."""
        if hasattr(self, 'translate_page'):
            self.switchTo(self.translate_page)
            # Enable QC filter
            if hasattr(self.translate_page, 'qc_checkbox'):
                self.translate_page.qc_checkbox.setChecked(True)
            # TODO: Could set specific QC code filter if implemented
            logger.info(f"Filtering by QC code: {code}")
    
    def _get_table_model(self):
        """Get the current table model for Health page queries."""
        if hasattr(self, 'translate_page') and self.translate_page:
            table_widget = getattr(self.translate_page, 'table_widget', None)
            if table_widget and hasattr(table_widget, 'table_view'):
                model = table_widget.table_view.model()
                if hasattr(model, 'sourceModel'):
                    return model.sourceModel()
                return model
        return None
    
    def _on_health_navigate_to_row(self, row_id: int, mode: str, apply_filter: bool):
        """
        Navigate to a specific row from Health page (Stage 8.2).
        
        Args:
            row_id: Source row index (ParsedFile index)
            mode: 'error' or 'qc' - determines which filter to apply
            apply_filter: If True, enable the corresponding filter
        """
        if not hasattr(self, 'translate_page') or not self.translate_page:
            return
        
        # Switch to Translate page
        self.switchTo(self.translate_page)
        
        # Apply filter if requested
        if apply_filter:
            if mode == "error":
                if hasattr(self.translate_page, 'error_filter_checkbox'):
                    self.translate_page.error_filter_checkbox.setChecked(True)
            elif mode == "qc":
                if hasattr(self.translate_page, 'qc_checkbox'):
                    self.translate_page.qc_checkbox.setChecked(True)
        
        # Select the row (source index) - use helper if available
        table_widget = getattr(self.translate_page, 'table_widget', None)
        if table_widget and hasattr(table_widget, 'table_view'):
            view = table_widget.table_view
            
            # Get the source model
            proxy_model = view.model()
            source_model = proxy_model
            if hasattr(proxy_model, 'sourceModel'):
                source_model = proxy_model.sourceModel()
            
            if hasattr(source_model, 'index'):
                # Map source index to proxy index for selection
                source_index = source_model.index(row_id, 0)
                
                if hasattr(proxy_model, 'mapFromSource'):
                    proxy_index = proxy_model.mapFromSource(source_index)
                    if proxy_index.isValid():
                        view.selectRow(proxy_index.row())
                        view.scrollTo(proxy_index)
                        
                        # Flash effect
                        if hasattr(view, 'flash_row'):
                            view.flash_row(proxy_index.row())
                        
                        logger.info(f"Health: Navigated to source row {row_id} (proxy row {proxy_index.row()})")
                    else:
                        # Row not visible in current filter - try disabling filter and retry
                        logger.warning(f"Health: Source row {row_id} not visible in current filter, disabling filter")
                        
                        # Disable the filter that was just enabled
                        if mode == "error":
                            if hasattr(self.translate_page, 'error_filter_checkbox'):
                                self.translate_page.error_filter_checkbox.setChecked(False)
                        elif mode == "qc":
                            if hasattr(self.translate_page, 'qc_checkbox'):
                                self.translate_page.qc_checkbox.setChecked(False)
                        
                        # Retry mapping after filter disabled
                        proxy_index = proxy_model.mapFromSource(source_index)
                        if proxy_index.isValid():
                            view.selectRow(proxy_index.row())
                            view.scrollTo(proxy_index)
                            if hasattr(view, 'flash_row'):
                                view.flash_row(proxy_index.row())
                        else:
                            # Still invalid - show warning
                            from qfluentwidgets import InfoBar
                            InfoBar.warning(
                                title="Uyarı",
                                content=f"Satır {row_id} modelde bulunamadı",
                                parent=self.translate_page,
                                duration=3000
                            )
                else:
                    # No proxy, select directly
                    view.selectRow(row_id)
                    view.scrollTo(source_index)

    def load_file_to_pages(self, parsed_file):
        """
        Load a parsed file into all relevant page tables.
        
        This is called when a file is opened to populate the Fluent UI pages
        with the real TranslationTableModel data.
        
        Args:
            parsed_file: ParsedFile instance with items to display
        """
        from gui.models.translation_table_model import TranslationTableModel
        from gui.models.translation_filter_proxy import TranslationFilterProxyModel
        from gui.views.file_table_view import parsed_items_to_table_rows
        
        # Convert ParsedItems to TableRowData
        rows = parsed_items_to_table_rows(parsed_file.items, parsed_file.mode)
        
        # Create model and proxy for this file
        model = TranslationTableModel()
        model.set_rows(rows)
        
        proxy = TranslationFilterProxyModel()
        proxy.setSourceModel(model)
        
        # Store reference for batch controller access
        self._current_table_model = model
        self._current_filter_proxy = proxy
        
        # Populate translate page table
        if hasattr(self, 'translate_page') and self.translate_page:
            self.translate_page.table_widget.set_proxy_model(proxy)
            logger.info(f"Loaded {len(rows)} items to TranslatePage")
        
        # Also populate files page and review page if they have tables
        if hasattr(self, 'files_page') and self.files_page:
            if hasattr(self.files_page, 'table_widget'):
                self.files_page.table_widget.set_proxy_model(proxy)
        
        if hasattr(self, 'review_page') and self.review_page:
            if hasattr(self.review_page, 'table_widget'):
                self.review_page.table_widget.set_proxy_model(proxy)
    
    def _update_language_model_display(self):
        """Update language/model display."""
        pass
    
    def statusBar(self):
        """Return status bar for compatibility."""
        # Create real status bar if not exists
        if not getattr(self, '_status_bar', None):
            from PySide6.QtWidgets import QStatusBar
            self._status_bar = QStatusBar(self)
            self._status_bar.setStyleSheet("background: #2b2b2b; color: #cccccc; padding: 4px;")
            
            # Standard QMainWindow way to set status bar
            if hasattr(self, 'setStatusBar'):
                self.setStatusBar(self._status_bar)
            else:
                logger.warning("MainFluentWindow does not support setStatusBar, status bar may not appear")
                
            logger.debug("Created real status bar")
        return self._status_bar
    
    def _populate_project_tree(self, project_path: str):
        """Populate project tree (stub for FluentWindow)."""
        logger.debug(f"Project tree stub: {project_path}")
        # Files page should handle project tree in FluentWindow
        if hasattr(self, 'files_page') and self.files_page:
            if hasattr(self.files_page, 'load_project'):
                self.files_page.load_project(project_path)
    
    # =========================================================================
    # VIEW ADAPTER PROPERTIES (Proxies to sub-pages)
    # =========================================================================
    
    @property
    def model_combo(self):
        """Proxy to TranslatePage model combo (source of truth for translation)."""
        return self.translate_page.model_combo if hasattr(self, 'translate_page') else None

    @property
    def source_lang_combo(self):
        """Proxy to TranslatePage source lang combo (source of truth for translation)."""
        return self.translate_page.source_lang_combo if hasattr(self, 'translate_page') else None

    @property
    def target_lang_combo(self):
        """Proxy to TranslatePage target lang combo (source of truth for translation)."""
        return self.translate_page.target_lang_combo if hasattr(self, 'translate_page') else None
    
    def get_current_source_language(self) -> str:
        """Get source language name from TranslatePage."""
        if self.source_lang_combo:
            return self.source_lang_combo.currentText().strip()
        return "English"
    
    def get_current_target_language(self) -> str:
        """Get target language name from TranslatePage."""
        if self.target_lang_combo:
            return self.target_lang_combo.currentText().strip()
        return "Turkish"
    
    def get_current_source_code(self) -> str:
        """Get source language code from TranslatePage."""
        if hasattr(self, 'translate_page') and hasattr(self.translate_page, 'get_source_language_code'):
            return self.translate_page.get_source_language_code()
        return "en"
    
    def get_current_target_code(self) -> str:
        """Get target language code from TranslatePage."""
        if hasattr(self, 'translate_page') and hasattr(self.translate_page, 'get_target_language_code'):
            return self.translate_page.get_target_language_code()
        return "tr"
    
    def get_current_model_name(self) -> str:
        """Get model name from TranslatePage."""
        if self.model_combo:
            return self.model_combo.currentText().strip()
        return "gemini-2.0-flash"
    
    # =========================================================================
    # VIEW ADAPTER METHODS (Legacy compatibility)
    # =========================================================================

    def _get_current_table(self):
        """Get current table widget for legacy compatibility."""
        # Primary: Translate Page Table
        if hasattr(self, 'translate_page') and self.translate_page:
            return self.translate_page.table_widget
        return None

    def _get_current_item_index(self) -> int:
        """Get integer index of currently selected item in the source model."""
        table = self._get_current_table()
        if table:
            # Get row IDs (may be UUIDs)
            selected = table.get_selected_row_ids()
            if selected:
                row_id = selected[0]
                # Convert row ID to integer index
                if hasattr(self, '_current_table_model') and self._current_table_model:
                    idx = self._current_table_model.get_index_by_id(str(row_id))
                    if idx is not None:
                        return idx
                # Fallback: if row_id is already an int
                if isinstance(row_id, int):
                    return row_id
                # Try to parse string to int
                try:
                    return int(row_id)
                except (ValueError, TypeError):
                    pass
        return -1

    def _set_current_item_index(self, index: int):
        """Select item at index."""
        table = self._get_current_table()
        if table:
            table.select_row(index)

    def _set_current_tab_modified(self, modified: bool):
        """Mark current tab as modified."""
        # Update current file data status
        file_data = self._get_current_file_data()
        if file_data:
            file_data.is_modified = modified
        # Trigger UI update if needed (e.g. status bar)
        self.statusBar().showMessage("Değişiklikler kaydedilmedi" if modified else "Kaydedildi", 2000)

    def _get_current_translatable_items(self):
        """Get list of items in current file."""
        file_data = self._get_current_file_data()
        return file_data.items if file_data else []
    
    def _update_model_list(self):
        """Update model list (for legacy compatibility). TranslatePage handles this."""
        # In FluentWindow, model list is managed by TranslatePage.model_combo
        # This is a no-op for compatibility with legacy gui_settings_manager calls
        pass
    
    def _update_ui_state(self):
        """Update UI state (for legacy compatibility)."""
        # TranslatePage handles its own UI state
        pass
    
    def update_row_translation(self, row_index: int, translated_text: str) -> bool:
        """
        Apply translation to a row in the current TranslationTableModel.
        Used by dialogs (Google Translate, AI Edit) to update the model.
        
        Args:
            row_index: Integer index in the source model
            translated_text: The translated text to apply
            
        Returns:
            True if successful, False otherwise
        """
        if not self._current_table_model:
            logger.warning("[update_row_translation] No current model")
            return False
        
        # Get the row data
        rows = self._current_table_model.get_all_rows()
        if not (0 <= row_index < len(rows)):
            logger.error(f"[update_row_translation] Invalid index: {row_index}")
            return False
        
        row = rows[row_index]
        
        # Update the row via model's update method
        row.update_text(translated_text)
        
        # Notify model that data changed
        model_index = self._current_table_model.index(row_index, 4)  # Column 4 is editable text
        self._current_table_model.dataChanged.emit(model_index, model_index)
        
        logger.debug(f"[update_row_translation] Updated row {row_index} with: {translated_text[:50]}...")
        return True

    def _clear_batch_results(self):
        """Clear batch results."""
        if self.batch_controller:
            self.batch_controller.clear_results()
            # Also reset inspector
            if self.inspector:
                self.inspector.clear_batch_status()
    
    def _handle_batch_item_updated(self, item_index: int, translated_text: str, item_data: dict = None):
        """Handle batch item update (delegate to controller)."""
        if self.batch_controller:
            self.batch_controller.handle_item_updated(item_index, translated_text, item_data)
    
    def _handle_batch_translate_error(self, error_msg: str):
        """Handle batch error (delegate to controller)."""
        if self.batch_controller:
            self.batch_controller.handle_error(error_msg)
    
    def _handle_batch_translate_finished(self, results: dict):
        """Handle batch finished (delegate to controller)."""
        if self.batch_controller:
            self.batch_controller.handle_finished(results)
        # Also reset translate page state
        if hasattr(self, 'translate_page') and self.translate_page:
            self.translate_page.set_batch_running(False)
    
    # =========================================================================
    # Theme control
    # =========================================================================
    
    def toggle_theme(self):
        """Toggle between dark and light theme."""
        if isDarkTheme():
            setTheme(Theme.LIGHT)
            logger.info("Theme switched to LIGHT")
        else:
            setTheme(Theme.DARK)
            logger.info("Theme switched to DARK")
    
    def set_theme(self, dark: bool):
        """Set theme explicitly."""
        setTheme(Theme.DARK if dark else Theme.LIGHT)

    # =========================================================================
    # Compatibility Properties for GUI Action Handler
    # =========================================================================
    
    @property
    def source_lang_combo(self):
        """Proxy for source language combo in TranslatePage."""
        if hasattr(self, 'translate_page') and self.translate_page:
            return self.translate_page.source_lang_combo
        return None

    @property
    def target_lang_combo(self):
        """Proxy for target language combo in TranslatePage."""
        if hasattr(self, 'translate_page') and self.translate_page:
            return self.translate_page.target_lang_combo
        return None

    @property
    def model_combo(self):
        """Proxy for AI model combo in TranslatePage."""
        if hasattr(self, 'translate_page') and self.translate_page:
            return self.translate_page.model_combo
        return None

    # =========================================================================
    # Data Properties (Sync with Settings Page)
    # =========================================================================

    @property
    def selected_model(self):
        """Get selected AI model from settings page."""
        if self.model_combo:
            text = self.model_combo.currentText()
            return text if text and text != "None" else None
        return None
    
    @selected_model.setter
    def selected_model(self, value):
        if self.model_combo and value:
            if self.model_combo.currentText() != value:
                self.model_combo.blockSignals(True)
                self.model_combo.setCurrentText(value)
                self.model_combo.blockSignals(False)

    @property
    def source_language(self):
        """Get source language code from settings page."""
        if self.source_lang_combo:
            data = self.source_lang_combo.currentData()
            return data if data else "en"
        return "en"
        
    @source_language.setter
    def source_language(self, value):
        if self.source_lang_combo and value:
             # Find index for data
             idx = self.source_lang_combo.findData(value)
             if idx >= 0 and self.source_lang_combo.currentIndex() != idx:
                 self.source_lang_combo.blockSignals(True)
                 self.source_lang_combo.setCurrentIndex(idx)
                 self.source_lang_combo.blockSignals(False)

    @property
    def target_language(self):
        """Get target language code from settings page."""
        if self.target_lang_combo:
            data = self.target_lang_combo.currentData()
            return data if data else "tr"
        return "tr"
        
    @target_language.setter
    def target_language(self, value):
        if self.target_lang_combo and value:
             idx = self.target_lang_combo.findData(value)
             if idx >= 0 and self.target_lang_combo.currentIndex() != idx:
                 self.target_lang_combo.blockSignals(True)
                 self.target_lang_combo.setCurrentIndex(idx)
                 self.target_lang_combo.blockSignals(False)

    # =========================================================================
    # MULTI-FILE TAB MANAGEMENT
    # =========================================================================
    
    def open_or_focus_file(self, file_path: str, parsed_file) -> bool:
        """
        Open a file in a new tab or focus existing tab if already open.
        
        Args:
            file_path: Path to the file
            parsed_file: ParsedFile instance
            
        Returns:
            True if file was opened/focused successfully
        """
        from gui.views.file_table_view import parsed_items_to_table_rows
        from gui.models.translation_table_model import TranslationTableModel
        from gui.models.translation_filter_proxy import TranslationFilterProxyModel
        from pathlib import Path
        
        # Check if already open -> focus existing tab
        if file_path in self._file_tabs:
            logger.info(f"[open_or_focus] File already open, focusing: {file_path}")
            self.switch_to_file(file_path)
            # Also focus the UI tab
            if hasattr(self, 'translate_page') and self.translate_page:
                self.translate_page.focus_file_tab(file_path)
            return True
        
        # Create model and proxy for this file
        rows = parsed_items_to_table_rows(parsed_file.items, parsed_file.mode)
        model = TranslationTableModel()
        model.set_rows(rows)
        
        proxy = TranslationFilterProxyModel()
        proxy.setSourceModel(model)
        
        # Store in file_tabs
        self._file_tabs[file_path] = {
            'model': model,
            'proxy': proxy,
            'parsed_file': parsed_file
        }
        
        # Store in file_data (legacy compatibility)
        self.file_data[file_path] = parsed_file
        
        # Set as current
        self.current_file_path = file_path
        self._current_table_model = model
        self._current_filter_proxy = proxy
        
        # Load into translate page
        if hasattr(self, 'translate_page') and self.translate_page:
            self.translate_page.table_widget.set_proxy_model(proxy)
            # Add UI tab
            file_name = Path(file_path).name
            self.translate_page.add_file_tab(file_path, file_name)
        
        # Update Inspector title bar to show file name
        file_name = Path(file_path).name
        logger.info(f"[open_or_focus] Opened new file tab: {file_name} ({len(rows)} rows)")
        
        # Emit lifecycle signals for FilesPage and other listeners
        self.file_opened.emit(file_path)
        self.active_file_changed.emit(file_path)
        self.tab_changed.emit(self.get_open_file_count() - 1)
        
        return True
    
    def switch_to_file(self, file_path: str) -> bool:
        """
        Switch to an already-open file tab.
        
        Args:
            file_path: Path to the file to switch to
            
        Returns:
            True if switched successfully
        """
        if file_path not in self._file_tabs:
            logger.warning(f"[switch_to_file] File not open: {file_path}")
            return False
        
        tab_info = self._file_tabs[file_path]
        
        # Update current state
        self.current_file_path = file_path
        self._current_table_model = tab_info['model']
        self._current_filter_proxy = tab_info['proxy']
        
        # Load into translate page
        if hasattr(self, 'translate_page') and self.translate_page:
            self.translate_page.table_widget.set_proxy_model(tab_info['proxy'])
        
        # Emit active file changed signal
        self.active_file_changed.emit(file_path)
        
        logger.info(f"[switch_to_file] Switched to: {file_path}")
        return True
    
    def close_file_tab(self, file_path: str) -> bool:
        """
        Close a file tab.
        
        Args:
            file_path: Path to the file to close
            
        Returns:
            True if closed successfully
        """
        if file_path not in self._file_tabs:
            logger.warning(f"[close_file_tab] File not open: {file_path}")
            return False
        
        # Remove from tabs
        tab_info = self._file_tabs.pop(file_path)
        
        # Remove from file_data (legacy)
        if file_path in self.file_data:
            del self.file_data[file_path]
        
        # Remove UI tab
        if hasattr(self, 'translate_page') and self.translate_page:
            self.translate_page.remove_file_tab(file_path)
        
        # Clear model if it has a clear method
        model = tab_info.get('model')
        if model and hasattr(model, 'clear'):
            model.clear()
        
        logger.info(f"[close_file_tab] Closed: {file_path}")
        
        # If this was the current file, switch to another or clear
        if self.current_file_path == file_path:
            remaining = list(self._file_tabs.keys())
            if remaining:
                self.switch_to_file(remaining[0])
            else:
                # No files left, clear state
                self.current_file_path = None
                self._current_table_model = None
                self._current_filter_proxy = None
                if hasattr(self, 'translate_page') and self.translate_page:
                    self.translate_page.table_widget.set_proxy_model(None)
                # Emit empty active file
                self.active_file_changed.emit("")
                logger.info("[close_file_tab] All files closed")
        
        # Emit lifecycle signals
        self.file_closed.emit(file_path)
        self.close_tab_requested.emit(0)  # Legacy signal for controller cleanup
        
        return True
    
    def get_open_file_count(self) -> int:
        """Get the number of currently open files."""
        return len(self._file_tabs)
    
    def get_open_file_paths(self) -> list:
        """Get list of all open file paths."""
        return list(self._file_tabs.keys())
    
    def is_file_open(self, file_path: str) -> bool:
        """Check if a file is currently open."""
        return file_path in self._file_tabs
    
    # =========================================================================
    # SESSION PERSISTENCE (v2)
    # =========================================================================
    
    def closeEvent(self, event):
        """Override close event to save session before exit."""
        from models.settings_model import SettingsModel
        
        # Save session state
        open_tabs = self.get_open_file_paths()
        active_tab = self.current_file_path if hasattr(self, 'current_file_path') else None
        
        settings = SettingsModel.instance()
        settings.save_session(open_tabs, active_tab)
        
        logger.info(f"Session saved on close: {len(open_tabs)} tabs")
        
        # Accept the close
        event.accept()
    
    def restore_session(self):
        """
        Restore previous session on startup.
        
        Called from app_bootstrap after window is created.
        Returns True if session was restored.
        """
        import os
        from models.settings_model import SettingsModel
        
        settings = SettingsModel.instance()
        open_tabs = settings.open_tabs
        active_tab = settings.active_tab
        
        if not open_tabs:
            logger.debug("No session to restore")
            return False
        
        # Filter to existing files only
        valid_tabs = [p for p in open_tabs if os.path.exists(p)]
        
        if not valid_tabs:
            logger.debug("Session tabs no longer exist")
            return False
        
        logger.info(f"Restoring session: {len(valid_tabs)} files")
        
        # Restore each file - this requires the file controller
        # The actual loading will be delegated to app_bootstrap
        # Here we just provide the list for external use
        self._session_tabs_to_restore = valid_tabs
        self._session_active_tab = active_tab if active_tab in valid_tabs else (valid_tabs[0] if valid_tabs else None)
        
        return True
    
    def get_session_to_restore(self):
        """Get session data for restoration by app_bootstrap."""
        tabs = getattr(self, '_session_tabs_to_restore', [])
        active = getattr(self, '_session_active_tab', None)
        return tabs, active

    def _on_retry_line_requested(self, row_index: int):
        """Handle retry request from Inspector."""
        logger.info(f"Retry requested for row {row_index}")
        
        # Access batch controller
        # It might be on self if assigned, or via gui_handlers
        batch_ctrl = getattr(self, 'batch_controller', None)
        if not batch_ctrl and hasattr(self, 'gui_handlers'):
             batch_ctrl = getattr(self.gui_handlers, 'batch_controller', None)
             
        if batch_ctrl:
             batch_ctrl.retry_single_line(row_index)
        else:
             logger.error("Batch controller not available for retry")
             from PySide6.QtWidgets import QMessageBox
             QMessageBox.warning(self, "Hata", "Toplu işlem kontrolcüsüne erişilemedi.")

    def _on_navigate_row_requested(self, row_index: int):
        """Handle navigation to specific row index."""
        logger.info(f"Navigation requested: row_id={row_index}")
        
        # Switch to translate page if needed
        if hasattr(self, 'translate_page') and self.stackedWidget.currentWidget() != self.translate_page:
            self.stackedWidget.setCurrentWidget(self.translate_page)
            
        if hasattr(self, 'translate_page'):
            if hasattr(self.translate_page, 'select_row_by_index'):
                self.translate_page.select_row_by_index(row_index)
            else:
                 logger.warning("TranslatePage missing select_row_by_index")

    
    def show_message(self, title, message, parent=None):
        """Compatibility wrapper for showing messages."""
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, title, message)

    def _on_manual_next_error(self):
        """Jump to next error via F8."""
        if hasattr(self, 'inspector_panel'):
            # Delegate to existing inspector logic which already knows layout
            self.inspector_panel._navigate_error(1)
            
    def _on_manual_prev_error(self):
        """Jump to previous error via Shift+F8."""
        if hasattr(self, 'inspector_panel'):
            self.inspector_panel._navigate_error(-1)
