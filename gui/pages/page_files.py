# -*- coding: utf-8 -*-
"""
RenForge Files Page (Session Manager)

Shows:
- Project info card
- Open Files list (synced with TranslatePage tabs)
- Recent Files list (persisted in settings)
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidgetItem, QListWidget, QListWidgetItem
)

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PushButton, TreeWidget, PrimaryPushButton,
    FluentIcon as FIF, CardWidget, IconWidget, TransparentPushButton
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.files")


class FilesPage(QWidget):
    """
    Files page - Session Manager.
    
    Shows project info, open files (synced with tabs), and recent files.
    """
    
    # Signal when user wants to open a file from the list
    file_open_requested = Signal(str)  # file_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FilesPage")
        
        self._project_path = None
        
        # Load recents from settings for persistence
        from models.settings_model import SettingsModel
        self._settings = SettingsModel.instance()
        self._recent_files = self._settings.recent_files.copy()
        
        self._setup_ui()
        logger.debug("FilesPage initialized")
    
    def _setup_ui(self):
        """Setup the page UI as a compact Session Manager."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # Kompakt margins
        layout.setSpacing(12)  # Tutarlı 12px spacing
        
        # Kompakt header with title and action buttons
        header = QHBoxLayout()
        header.setSpacing(8)
        
        self.title_label = SubtitleLabel("Oturum Yöneticisi")
        header.addWidget(self.title_label)
        header.addStretch()
        
        # Open file button (daha kompakt)
        self.open_btn = PrimaryPushButton("Dosya Aç", self)
        self.open_btn.setIcon(FIF.FOLDER_ADD)
        self.open_btn.setFixedHeight(32)
        self.open_btn.clicked.connect(self._on_open_file)
        header.addWidget(self.open_btn)
        
        # Open project button (secondary)
        self.project_btn = PushButton("Proje Aç", self)
        self.project_btn.setIcon(FIF.FOLDER)
        self.project_btn.setFixedHeight(32)
        self.project_btn.clicked.connect(self._on_open_project)
        header.addWidget(self.project_btn)
        
        layout.addLayout(header)
        
        # Main content - two-column layout
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left column: Open Files (kompakt)
        left_card = CardWidget()
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)
        
        open_header = BodyLabel("📂 Açık Dosyalar")
        open_header.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(open_header)
        
        self.open_files_list = QListWidget()
        self.open_files_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
                margin: 1px 0;
            }
            QListWidget::item:selected {
                background: #0078d4;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background: #3d3d3d;
            }
        """)
        self.open_files_list.itemClicked.connect(self._on_open_file_clicked)
        self.open_files_list.itemDoubleClicked.connect(self._on_open_file_double_clicked)
        left_layout.addWidget(self.open_files_list)
        
        # Kompakt empty state for open files
        self.open_empty_label = BodyLabel("📭 Dosya açılmadı. Yukarıdan 'Dosya Aç' tıklayın.")
        self.open_empty_label.setStyleSheet("color: #666666; font-size: 11px;")
        self.open_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.open_empty_label)
        
        content_splitter.addWidget(left_card)
        
        # Right column: Recent Files (kompakt)
        right_card = CardWidget()
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)
        
        # Kompakt header row with title and clear button
        recent_header_row = QHBoxLayout()
        recent_header_row.setSpacing(8)
        
        recent_header = BodyLabel("🕐 Son Açılan Dosyalar")
        recent_header.setStyleSheet("font-weight: bold; font-size: 13px;")
        recent_header_row.addWidget(recent_header)
        
        recent_header_row.addStretch()
        
        # Kompakt clear button
        self.clear_recent_btn = TransparentPushButton("Temizle")
        self.clear_recent_btn.setFixedHeight(24)
        self.clear_recent_btn.clicked.connect(self._on_clear_recent_files)
        recent_header_row.addWidget(self.clear_recent_btn)
        
        right_layout.addLayout(recent_header_row)
        
        self.recent_files_list = QListWidget()
        self.recent_files_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
                margin: 1px 0;
            }
            QListWidget::item:hover {
                background: #3d3d3d;
            }
        """)
        self.recent_files_list.itemDoubleClicked.connect(self._on_recent_file_double_clicked)
        right_layout.addWidget(self.recent_files_list)
        
        # Kompakt empty state for recent files
        self.recent_empty_label = BodyLabel("📭 Henüz dosya geçmişi yok.")
        self.recent_empty_label.setStyleSheet("color: #666666; font-size: 11px;")
        self.recent_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.recent_empty_label)
        
        content_splitter.addWidget(right_card)
        
        # Set splitter proportions (50/50)
        content_splitter.setSizes([500, 500])
        
        layout.addWidget(content_splitter)
        
        # Populate lists
        self._refresh_open_files_list()
        self._refresh_recent_list()
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_open_file(self):
        """Handle open file button click."""
        main_window = self.window()
        if hasattr(main_window, 'open_file_requested'):
            main_window.open_file_requested.emit()
    
    def _on_open_project(self):
        """Handle open project button click."""
        main_window = self.window()
        if hasattr(main_window, 'open_project_requested'):
            main_window.open_project_requested.emit()
    
    def _on_clear_recent_files(self):
        """Clear all recent files."""
        self._recent_files.clear()
        
        # Clear from settings too
        if hasattr(self._settings, 'clear_recent_files'):
            self._settings.clear_recent_files()
        else:
            # Fallback: set recent_files to empty list in settings
            self._settings.recent_files = []
            if hasattr(self._settings, 'save'):
                self._settings.save()
        
        # Refresh UI
        self._refresh_recent_list()
        logger.info("Recent files list cleared")
    
    def _on_open_file_clicked(self, item):
        """Handle open files list single click - just select."""
        pass  # Single click just selects
    
    def _on_open_file_double_clicked(self, item):
        """Handle open files list double-click - switch to file and go to Translate."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self._switch_to_file_and_navigate(file_path)
    
    def _on_recent_file_double_clicked(self, item):
        """Handle recent files list double-click - open/focus file."""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self._open_file_and_navigate(file_path)
    
    def _switch_to_file_and_navigate(self, file_path: str):
        """Switch to an open file and navigate to Translate page."""
        main_window = self.window()
        if hasattr(main_window, 'switch_to_file'):
            main_window.switch_to_file(file_path)
        # Navigate to Translate page
        if hasattr(main_window, 'switchTo') and hasattr(main_window, 'translate_page'):
            main_window.switchTo(main_window.translate_page)
        logger.debug(f"Switched to file: {file_path}")
    
    def _open_file_and_navigate(self, file_path: str):
        """Open/focus a file and navigate to Translate page."""
        main_window = self.window()
        
        # Check if file exists
        if not Path(file_path).exists():
            logger.warning(f"Recent file no longer exists: {file_path}")
            return
        
        # Use controller to open file
        if hasattr(main_window, '_app_controller') and main_window._app_controller:
            controller = main_window._app_controller
            if hasattr(controller, 'file_controller'):
                try:
                    controller.file_controller.open_file(file_path, mode='translate')
                    # Navigate to Translate page
                    if hasattr(main_window, 'switchTo') and hasattr(main_window, 'translate_page'):
                        main_window.switchTo(main_window.translate_page)
                    logger.info(f"Opened recent file: {file_path}")
                    return
                except Exception as e:
                    logger.error(f"Failed to open file: {e}")
    
    # =========================================================================
    # SIGNAL HANDLERS (connected to MainFluentWindow signals)
    # =========================================================================
    
    def _on_file_opened_signal(self, file_path: str):
        """Handle file opened signal from MainFluentWindow."""
        self._refresh_open_files_list()
        self.add_recent_file(file_path)
    
    def _on_file_closed_signal(self, file_path: str):
        """Handle file closed signal from MainFluentWindow."""
        self._refresh_open_files_list()
    
    def _on_active_file_changed_signal(self, file_path: str):
        """Handle active file changed signal - highlight in list."""
        self._highlight_active_file(file_path)
    
    # =========================================================================
    # UI REFRESH METHODS
    # =========================================================================
    
    def _refresh_open_files_list(self):
        """Refresh the open files list from MainFluentWindow state."""
        self.open_files_list.clear()
        
        main_window = self.window()
        if not main_window or not hasattr(main_window, 'get_open_file_paths'):
            self.open_empty_label.setVisible(True)
            self.open_files_list.setVisible(False)
            return
        
        open_paths = main_window.get_open_file_paths()
        
        if not open_paths:
            self.open_empty_label.setVisible(True)
            self.open_files_list.setVisible(False)
            return
        
        self.open_empty_label.setVisible(False)
        self.open_files_list.setVisible(True)
        
        active_path = main_window.current_file_path if hasattr(main_window, 'current_file_path') else None
        
        for file_path in open_paths:
            path = Path(file_path)
            item = QListWidgetItem(f"📄 {path.name}")
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setToolTip(file_path)
            self.open_files_list.addItem(item)
            
            # Highlight active file
            if file_path == active_path:
                self.open_files_list.setCurrentItem(item)
    
    def _refresh_recent_list(self):
        """Refresh the recent files list."""
        self.recent_files_list.clear()
        
        # Filter to only existing files
        valid_recents = [f for f in self._recent_files if Path(f).exists()]
        
        if not valid_recents:
            self.recent_empty_label.setVisible(True)
            self.recent_files_list.setVisible(False)
            return
        
        self.recent_empty_label.setVisible(False)
        self.recent_files_list.setVisible(True)
        
        for file_path in valid_recents:
            path = Path(file_path)
            item = QListWidgetItem(f"📄 {path.name}")
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setToolTip(file_path)
            self.recent_files_list.addItem(item)
    
    def _highlight_active_file(self, file_path: str):
        """Highlight the active file in the open files list."""
        for i in range(self.open_files_list.count()):
            item = self.open_files_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self.open_files_list.setCurrentItem(item)
                break
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def add_recent_file(self, file_path: str):
        """Add a file to recent files list and persist."""
        # Remove if already in list
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        
        # Add to front
        self._recent_files.insert(0, file_path)
        
        # Limit to 20
        self._recent_files = self._recent_files[:20]
        
        # Persist to settings
        self._settings.add_recent_file(file_path)
        
        # Update UI
        self._refresh_recent_list()
    
    def connect_to_main_window(self):
        """Connect to MainFluentWindow signals for file lifecycle events."""
        main_window = self.window()
        if not main_window:
            return
        
        # Connect to lifecycle signals if they exist
        if hasattr(main_window, 'file_opened'):
            main_window.file_opened.connect(self._on_file_opened_signal)
        if hasattr(main_window, 'file_closed'):
            main_window.file_closed.connect(self._on_file_closed_signal)
        if hasattr(main_window, 'active_file_changed'):
            main_window.active_file_changed.connect(self._on_active_file_changed_signal)
        
        logger.debug("FilesPage connected to MainFluentWindow signals")
    
    def showEvent(self, event):
        """Override showEvent to connect signals and refresh on show."""
        super().showEvent(event)
        
        # Connect signals on first show
        if not hasattr(self, '_signals_connected'):
            self._signals_connected = True
            self.connect_to_main_window()
        
        # Always refresh lists when shown
        self._refresh_open_files_list()
        self._refresh_recent_list()
