# -*- coding: utf-8 -*-
"""
RenForge Review Page

Review and approval page with command bar for review actions.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    SubtitleLabel, PushButton, PrimaryPushButton, BodyLabel,
    FluentIcon as FIF
)

from gui.widgets.shared_table_view import TranslationTableWidget
from renforge_logger import get_logger

logger = get_logger("gui.pages.review")


class ReviewPage(QWidget):
    """
    Review page with command bar.
    
    Command bar actions:
    - Onayla
    - Geri Al (AI / Toplu)
    - İşaretçi ekle / sonraki / temizle
    - Sorunlu satıra git
    """
    
    # Signals
    approve_requested = Signal()
    undo_requested = Signal()
    next_issue_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ReviewPage")
        
        self._setup_ui()
        logger.debug("ReviewPage initialized")
    
    def _setup_ui(self):
        """Setup the page UI."""
        from PySide6.QtWidgets import QStackedWidget
        from qfluentwidgets import CardWidget, BodyLabel
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)  # Kompakt margins
        layout.setSpacing(12)  # Tutarlı spacing
        
        # Command bar
        self._setup_command_bar()
        layout.addLayout(self.command_bar_layout)
        
        # Stacked widget for empty/content states
        self.stack = QStackedWidget()
        
        # State 0: Empty state (no file open) - Kompakt
        empty_card = CardWidget()
        empty_layout = QVBoxLayout(empty_card)
        empty_layout.setContentsMargins(30, 40, 30, 40)  # Daha kompakt
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = BodyLabel("📋")
        empty_icon.setStyleSheet("font-size: 36px;")  # Daha küçük
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_title = BodyLabel("İncelenecek Dosya Yok")
        empty_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        
        empty_desc = BodyLabel("Çeviri sayfasından bir dosya açın.")
        empty_desc.setStyleSheet("color: #888888;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_desc)
        
        self.stack.addWidget(empty_card)
        
        # State 1: Translation table (filtered to show review items)
        self.table_widget = TranslationTableWidget(self)
        self.table_widget.selection_changed.connect(self._on_selection_changed)
        self.stack.addWidget(self.table_widget)
        
        layout.addWidget(self.stack)
        
        # Start with empty state
        self.stack.setCurrentIndex(0)
    
    def _setup_command_bar(self):
        """Setup the command bar with review actions."""
        self.command_bar_layout = QHBoxLayout()
        self.command_bar_layout.setSpacing(8)
        
        # Title
        title = SubtitleLabel("İnceleme")
        self.command_bar_layout.addWidget(title)
        self.command_bar_layout.addSpacing(20)
        
        # Onayla
        self.approve_btn = PrimaryPushButton("Onayla")
        self.approve_btn.setIcon(FIF.ACCEPT)
        self.approve_btn.setShortcut("Ctrl+Return")
        self.approve_btn.clicked.connect(self._on_approve)
        self.command_bar_layout.addWidget(self.approve_btn)
        
        # Geri Al
        self.undo_btn = PushButton("Geri Al")
        self.undo_btn.setIcon(FIF.HISTORY)
        self.undo_btn.setShortcut("Ctrl+Z")
        self.undo_btn.clicked.connect(self._on_undo)
        self.command_bar_layout.addWidget(self.undo_btn)
        
        # Separator
        self.command_bar_layout.addSpacing(16)
        
        # İşaretçi grup
        self.add_marker_btn = PushButton("İşaretle")
        self.add_marker_btn.setIcon(FIF.FLAG)
        self.add_marker_btn.clicked.connect(self._on_add_marker)
        self.command_bar_layout.addWidget(self.add_marker_btn)
        
        self.next_marker_btn = PushButton("Sonraki")
        self.next_marker_btn.setIcon(FIF.DOWN)
        self.next_marker_btn.clicked.connect(self._on_next_marker)
        self.command_bar_layout.addWidget(self.next_marker_btn)
        
        self.clear_markers_btn = PushButton("Temizle")
        self.clear_markers_btn.setIcon(FIF.DELETE)
        self.clear_markers_btn.clicked.connect(self._on_clear_markers)
        self.command_bar_layout.addWidget(self.clear_markers_btn)
        
        # Separator
        self.command_bar_layout.addSpacing(16)
        
        # Sorunlu satıra git
        self.next_issue_btn = PushButton("Sonraki Sorunlu")
        self.next_issue_btn.setIcon(FIF.CARE_RIGHT_SOLID)
        self.next_issue_btn.clicked.connect(self._on_next_issue)
        self.command_bar_layout.addWidget(self.next_issue_btn)
        
        self.command_bar_layout.addStretch()
        
        # Selection indicator
        self.selection_label = BodyLabel("0 satır seçili")
        self.selection_label.setStyleSheet("color: #888888;")
        self.command_bar_layout.addWidget(self.selection_label)
        
        self.command_bar_layout.addSpacing(12)
        
        # Stats
        self.stats_label = BodyLabel("Onaylı: 0 | Sorunlu: 0")
        self.command_bar_layout.addWidget(self.stats_label)
        
        # Başlangıç state'i ayarla
        self._update_action_states()
    
    # =========================================================================
    # ACTION HANDLERS
    # =========================================================================
    
    def _on_approve(self):
        """Handle approve action."""
        self.approve_requested.emit()
        logger.debug("Approve requested")
    
    def _on_undo(self):
        """Handle undo action."""
        self.undo_requested.emit()
        logger.debug("Undo requested")
    
    def _on_add_marker(self):
        """Handle add marker action."""
        logger.debug("Add marker (stub)")
    
    def _on_next_marker(self):
        """Handle next marker action."""
        logger.debug("Next marker (stub)")
    
    def _on_clear_markers(self):
        """Handle clear markers action."""
        logger.debug("Clear markers (stub)")
    
    def _on_next_issue(self):
        """Handle next issue action."""
        self.next_issue_requested.emit()
        # Filter to show issues
        self.table_widget.filter_segment.setCurrentItem(TranslationTableWidget.FILTER_PROBLEMS)
        logger.debug("Next issue requested")
    
    def _on_selection_changed(self, row_data: dict):
        """Handle table selection changed."""
        # Merkezi state güncelleme
        self._update_action_states()
        
        # Update inspector
        main_window = self.window()
        if hasattr(main_window, 'inspector'):
            main_window.inspector.show_row(row_data)
    
    def _update_action_states(self):
        """
        Merkezi buton state güncelleme metodu.
        """
        # Selection count
        selection_count = 0
        if hasattr(self, 'table_widget') and hasattr(self.table_widget, 'table_view'):
            selection = self.table_widget.table_view.selectionModel()
            if selection:
                selection_count = len(selection.selectedRows(0))
        
        # File state
        main_window = self.window()
        has_file = False
        
        if main_window and hasattr(main_window, 'current_file_path'):
            has_file = bool(main_window.current_file_path)
        
        # === BUTON KURALLARI ===
        
        # Onayla: dosya açık VE seçim var
        self.approve_btn.setEnabled(has_file and selection_count > 0)
        
        # Geri Al: dosya açık
        self.undo_btn.setEnabled(has_file)
        
        # İşaretle: dosya açık VE seçim var
        self.add_marker_btn.setEnabled(has_file and selection_count > 0)
        
        # Sonraki: dosya açık
        self.next_marker_btn.setEnabled(has_file)
        
        # Temizle: dosya açık
        self.clear_markers_btn.setEnabled(has_file)
        
        # Sonraki Sorunlu: dosya açık
        self.next_issue_btn.setEnabled(has_file)
        
        # Selection label güncelle
        if hasattr(self, 'selection_label'):
            self.selection_label.setText(f"{selection_count} satır seçili")
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def update_stats(self, approved: int, issues: int):
        """Update the stats label."""
        self.stats_label.setText(f"Onaylı: {approved} | Sorunlu: {issues}")
    
    def set_has_file(self, has_file: bool):
        """Set whether there's an active file to review."""
        if has_file:
            self.stack.setCurrentIndex(1)  # Show table
            # Default to showing problems
            self.table_widget.filter_segment.setCurrentItem(TranslationTableWidget.FILTER_PROBLEMS)
        else:
            self.stack.setCurrentIndex(0)  # Show empty state
    
    def showEvent(self, event):
        """Override to check for active file when page shown."""
        super().showEvent(event)
        main_window = self.window()
        if main_window and hasattr(main_window, 'current_file_path'):
            has_file = bool(main_window.current_file_path)
            self.set_has_file(has_file)
            
            # Sync table with current file's proxy if available
            if has_file and hasattr(main_window, '_current_filter_proxy'):
                self.table_widget.set_proxy_model(main_window._current_filter_proxy)
                # Re-apply filter after setting proxy
                self.table_widget.filter_segment.setCurrentItem(TranslationTableWidget.FILTER_PROBLEMS)
