# -*- coding: utf-8 -*-
"""
RenForge Inspector Panel

Right-side panel with tabs for row details, batch status, and log.
"""

from PySide6.QtCore import Qt, Signal, QSize, QUrl, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLabel, QScrollArea, QFrame, QSplitter, QTabWidget
)

from qfluentwidgets import (
    BodyLabel, SubtitleLabel, StrongBodyLabel,
    TextEdit, PushButton, ProgressBar, CardWidget,
    FluentIcon as FIF, isDarkTheme
)
import re

from renforge_logger import get_logger

logger = get_logger("gui.panels.inspector")


class InspectorPanel(QWidget):
    """
    Inspector panel with 3 tabs:
    - Satır: Selected row details (original/translation/status/tag/not)
    - Toplu: Batch progress, cancel, summary
    - Log: Log stream with copy functionality
    
    API:
    - show_row(row_payload: dict) -> Updates Satır tab
    - show_batch_status(status: dict) -> Updates Toplu tab
    - append_log(text: str) -> Appends to Log tab
    - toggle_visibility() -> Show/hide panel
    """
    
    # Signals for external communication
    cancel_batch_requested = Signal()
    visibility_changed = Signal(bool)  # Yeni sinyal - görünürlük değişikliği
    navigate_requested = Signal(int)  # For "Go to Line X" (Legacy/File Line)
    navigate_row_requested = Signal(int) # For "Go to Row Index X" (New/Accurate)
    retry_line_requested = Signal(int) # For "Retry Line X"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)  # Daha dar minimum
        self.setMaximumWidth(500)  # Daha geniş maksimum
        
        self._setup_ui()
        logger.debug("InspectorPanel initialized")
    
    def _setup_ui(self):
        """Setup the tabbed interface with header."""
        import os
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Başlık çubuğu (pin/unpin butonu ile)
        self._create_header()
        layout.addWidget(self.header_widget)
        
        # Use standard QTabWidget
        self.tabs = QTabWidget(self)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(False)
        
        # Tab bar'a minimum yükseklik ve tıklanabilir alan ver
        tab_bar = self.tabs.tabBar()
        tab_bar.setMinimumHeight(36)  # Yeterli tıklanabilir alan
        tab_bar.setFixedHeight(36)    # Sabit yükseklik zorla
        tab_bar.setExpanding(False)
        
        # KRITIK: Tab bar stilini ayarla - !important ile global stillerin üzerine yaz
        # FIX: Tab height MUST equal tab bar height to make entire area clickable
        # Tab bar height = 36px, so tabs must also be 36px (not 32px)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar {
                min-height: 36px !important;
                max-height: 36px !important;
                qproperty-drawBase: 0;
                padding: 0px !important;
                margin: 0px !important;
            }
            QTabBar::tab {
                min-width: 60px !important;
                min-height: 36px !important;
                height: 36px !important;
                padding: 0px 16px !important;
                margin: 0px 2px 0px 0px !important;
                border: none !important;
                border-radius: 4px 4px 0 0 !important;
                font-size: 12px !important;
            }
            QTabBar::tab:selected {
                background: #0078d4 !important;
                color: white !important;
            }
            QTabBar::tab:!selected {
                background: #3d3d3d !important;
                color: #cccccc !important;
            }
            QTabBar::tab:hover:!selected {
                background: #4d4d4d !important;
            }
        """)
        
        # Install click forwarding filter to fix hitbox issues
        self._install_click_forwarding_filter(tab_bar)
        
        # Debug: Tab hit-test trace (environment var ile aktif)
        # Enable: set RENFORGE_TAB_HITTEST_TRACE=1
        if os.environ.get('RENFORGE_TAB_HITTEST_TRACE') == '1':
            self._install_tab_debug_filter(tab_bar)
        
        # Create tab content
        self._create_row_tab()
        self._create_batch_tab()
        self._create_log_tab()
        
        # Add tabs (widget, label)
        self.tabs.addTab(self.row_widget, "Satır")
        self.tabs.addTab(self.batch_widget, "Toplu")
        self.tabs.addTab(self.log_widget, "Log")
        
        layout.addWidget(self.tabs, 1)
    
    def _install_click_forwarding_filter(self, tab_bar):
        """
        Fix tab click area to cover ENTIRE tab button including padding.
        
        ROOT CAUSE: Child widgets or overlays may intercept mouse events
        before they reach the QTabBar. Even with WA_TransparentForMouseEvents,
        some events may not propagate correctly.
        
        SOLUTION: Install event filter on the InspectorPanel itself that
        intercepts ALL mouse events, checks if they're in the tab bar area,
        and forwards them directly to the tab switching logic.
        """
        from PySide6.QtCore import QObject, QEvent, Qt, QRect
        from PySide6.QtWidgets import QWidget
        
        class TabAreaClickFilter(QObject):
            """Event filter that catches clicks in tab bar area."""
            
            def __init__(self, inspector_panel, tab_bar_ref):
                super().__init__(inspector_panel)
                self.inspector = inspector_panel
                self.tab_bar = tab_bar_ref
            
            def eventFilter(self, obj, event):
                # Only handle mouse press events
                if event.type() != QEvent.Type.MouseButtonPress:
                    return False
                
                # Only handle left button
                if event.button() != Qt.MouseButton.LeftButton:
                    return False
                
                # Get click position in global coordinates
                if hasattr(event, 'globalPosition'):
                    global_pos = event.globalPosition().toPoint()
                elif hasattr(event, 'globalPos'):
                    global_pos = event.globalPos()
                else:
                    return False
                
                # Check if click is within tab bar's global geometry
                tab_bar_global_rect = QRect(
                    self.tab_bar.mapToGlobal(self.tab_bar.rect().topLeft()),
                    self.tab_bar.size()
                )
                
                if not tab_bar_global_rect.contains(global_pos):
                    return False  # Click is outside tab bar area
                
                # Convert to tab bar local coordinates
                local_pos = self.tab_bar.mapFromGlobal(global_pos)
                
                # Try tabAt first
                tab_index = self.tab_bar.tabAt(local_pos)
                
                if tab_index >= 0:
                    if self.tab_bar.currentIndex() != tab_index:
                        self.tab_bar.setCurrentIndex(tab_index)
                        logger.debug(f"[INSPECTOR] forwarded tab click at pos={local_pos} -> tab {tab_index}")
                    return True  # Consume the event
                
                # If tabAt failed, check each tab's full rect (including vertical expansion)
                for i in range(self.tab_bar.count()):
                    rect = self.tab_bar.tabRect(i)
                    # Expand to full height
                    full_rect = QRect(rect.x(), 0, rect.width(), self.tab_bar.height())
                    if full_rect.contains(local_pos):
                        if self.tab_bar.currentIndex() != i:
                            self.tab_bar.setCurrentIndex(i)
                            logger.debug(f"[INSPECTOR] forwarded tab click (expanded) at pos={local_pos} -> tab {i}")
                        return True
                
                return False  # Don't consume - let it pass through
        
        # Create and install filter on the InspectorPanel itself
        self._tab_click_filter = TabAreaClickFilter(self, tab_bar)
        self.installEventFilter(self._tab_click_filter)
        
        # Also install on the tabs container and all children recursively
        def install_filter_recursive(widget):
            widget.installEventFilter(self._tab_click_filter)
            for child in widget.children():
                if isinstance(child, QWidget):
                    install_filter_recursive(child)
        
        install_filter_recursive(self.tabs)
        
        # Ensure tab_bar accepts mouse events
        tab_bar.setMouseTracking(True)
        tab_bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        logger.debug(f"Tab click filter installed on InspectorPanel and {len(self.tabs.children())} children")
    
    def _install_tab_debug_filter(self, tab_bar):
        """
        Debug event filter for tab hitbox diagnosis.
        
        Enable with: RENFORGE_TAB_HITTEST_TRACE=1
        Disable with: RENFORGE_TAB_HITTEST_TRACE=0 (or unset)
        """
        from PySide6.QtCore import QObject, QEvent
        
        class TabHitTestTraceFilter(QObject):
            def __init__(self, tab_bar_ref):
                super().__init__(tab_bar_ref)
                self.tab_bar = tab_bar_ref
            
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.MouseButtonPress:
                    pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                    
                    # Map to tab_bar coordinates if needed
                    if obj != self.tab_bar:
                        global_pos = obj.mapToGlobal(pos)
                        local_pos = self.tab_bar.mapFromGlobal(global_pos)
                    else:
                        local_pos = pos
                    
                    tab_at = self.tab_bar.tabAt(local_pos)
                    
                    # Get tab rects for diagnosis
                    tab_rects = [self.tab_bar.tabRect(i) for i in range(self.tab_bar.count())]
                    
                    print(f"[TAB_HITTEST_TRACE] widget={obj.metaObject().className()}"
                          f" pos={pos} local_tab_pos={local_pos}"
                          f" tabAt={tab_at} tabBar.height={self.tab_bar.height()}"
                          f" tabRects={[(r.x(), r.y(), r.width(), r.height()) for r in tab_rects]}")
                    
                return False  # Don't consume event
        
        self._tab_debug_filter = TabHitTestTraceFilter(tab_bar)
        tab_bar.installEventFilter(self._tab_debug_filter)
        
        # Also install on tab_bar children
        from PySide6.QtWidgets import QWidget
        for child in tab_bar.children():
            if isinstance(child, QWidget):
                child.installEventFilter(self._tab_debug_filter)
        
        logger.info("Tab hit-test trace installed (RENFORGE_TAB_HITTEST_TRACE=1)")
    
    def _create_header(self):
        """Başlık çubuğu oluştur - panel adı ve pin/unpin butonu."""
        from qfluentwidgets import TransparentToolButton, FluentIcon as FIF
        from PySide6.QtWidgets import QSizePolicy
        
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(28)  # Daha kısa
        self.header_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.header_widget.setStyleSheet("background: #2d2d30; border-bottom: 1px solid #3d3d40;")
        
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(8, 2, 4, 2)  # Daha az dikey padding
        header_layout.setSpacing(4)
        
        # Panel başlığı
        title = BodyLabel("Inspector")
        title.setStyleSheet("font-weight: bold; font-size: 11px; color: #cccccc;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Pin/Unpin (gizle) butonu
        self.pin_btn = TransparentToolButton(FIF.PIN)
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setToolTip("Paneli Gizle")
        self.pin_btn.clicked.connect(self._on_pin_clicked)
        header_layout.addWidget(self.pin_btn)
    
    def _create_row_tab(self):
        """Create the row details tab."""
        self.row_widget = QWidget()
        layout = QVBoxLayout(self.row_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Row number
        self.row_number_label = SubtitleLabel("Satır: -")
        layout.addWidget(self.row_number_label)
        
        # Type & Tag
        type_layout = QHBoxLayout()
        self.row_type_label = BodyLabel("Tip: -")
        self.row_tag_label = BodyLabel("Tag: -")
        type_layout.addWidget(self.row_type_label)
        type_layout.addWidget(self.row_tag_label)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Original text
        layout.addWidget(StrongBodyLabel("Orijinal:"))
        self.original_text = TextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(100)
        layout.addWidget(self.original_text)
        
        # Translation text
        layout.addWidget(StrongBodyLabel("Çeviri:"))
        self.translation_text = TextEdit()
        self.translation_text.setMaximumHeight(100)
        layout.addWidget(self.translation_text)
        
        # Status
        status_layout = QHBoxLayout()
        self.row_status_label = BodyLabel("Durum: -")
        self.modified_label = BodyLabel("")
        status_layout.addWidget(self.row_status_label)
        status_layout.addWidget(self.modified_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # Notes (optional)
        layout.addWidget(StrongBodyLabel("Notlar:"))
        self.notes_text = TextEdit()
        self.notes_text.setMaximumHeight(60)
        self.notes_text.setPlaceholderText("Bu satır için not ekleyin...")
        layout.addWidget(self.notes_text)
        
        layout.addWidget(self.notes_text)
        
        # QC / Problem Card (Stage 6)
        # Visible only when current row has QC issues
        self.qc_card = CardWidget()
        self.qc_card.setVisible(False)
        self.qc_card.setStyleSheet("CardWidget { border: 1px solid #FF8C00; background-color: rgba(255, 140, 0, 0.05); }")
        
        qc_layout = QVBoxLayout(self.qc_card)
        qc_layout.setContentsMargins(12, 12, 12, 12)
        qc_layout.setSpacing(8)
        
        qc_header = QHBoxLayout()
        qc_icon = BodyLabel("⚠️")
        qc_title = StrongBodyLabel("Kalite Kontrol (QC)")
        qc_title.setStyleSheet("color: #FF8C00;")
        
        qc_header.addWidget(qc_icon)
        qc_header.addWidget(qc_title)
        qc_header.addStretch()
        qc_layout.addLayout(qc_header)
        
        # QC message body
        self.qc_message = BodyLabel()
        self.qc_message.setWordWrap(True)
        qc_layout.addWidget(self.qc_message)
        
        layout.addWidget(self.qc_card)
        
        layout.addStretch()
    
    def _create_batch_tab(self):
        """Create the batch status tab."""
        self.batch_widget = QWidget()
        layout = QVBoxLayout(self.batch_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Status title
        self.batch_title = SubtitleLabel("Toplu İşlem")
        layout.addWidget(self.batch_title)
        
        # Progress bar
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Progress text
        self.progress_label = BodyLabel("0 / 0")
        layout.addWidget(self.progress_label)
        
        # Stats
        stats_card = CardWidget()
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        
        self.success_label = BodyLabel("✅ Başarılı: 0")
        self.error_label = BodyLabel("❌ Hata: 0")
        self.warning_label = BodyLabel("⚠️ Uyarı: 0")
        
        stats_layout.addWidget(self.success_label)
        stats_layout.addWidget(self.error_label)
        stats_layout.addWidget(self.warning_label)
        stats_layout.addWidget(self.warning_label)
        layout.addWidget(stats_card)
        
        # Error Summary Card (Smart Error)
        self.error_card = CardWidget()
        self.error_card.setVisible(False)
        error_layout = QVBoxLayout(self.error_card)
        error_layout.setContentsMargins(12, 12, 12, 12)
        error_layout.setSpacing(8)
        
        # Title & Icon
        header_layout = QHBoxLayout()
        icon_label = BodyLabel()
        icon_label.setPixmap(FIF.INFO.icon(color="#c42b1c").pixmap(16, 16))
        
        self.error_title = StrongBodyLabel("Hata Özeti")
        self.error_title.setStyleSheet("color: #c42b1c;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(self.error_title)
        header_layout.addStretch(1)
        error_layout.addLayout(header_layout)
        
        # Message
        self.error_message = BodyLabel()
        self.error_message.setWordWrap(True)
        error_layout.addWidget(self.error_message)
        
        # Suggestions
        self.error_suggestions = BodyLabel()
        self.error_suggestions.setWordWrap(True)
        self.error_suggestions.setStyleSheet("color: #666; font-style: italic;")
        error_layout.addWidget(self.error_suggestions)
        
        # Details Expander
        # Customizing ExpandWidget is complex, simpler to use a toggle button + text edit or just text edit if always visible?
        # Requirement: "allow 'Details' expand"
        # Let's use a simplified approach: A text edit that is only visible if we have details, 
        # but maybe too much UI.
        # Let's just put the raw text in a small scroll area at bottom, limited height.
        
        self.error_raw_text = TextEdit()
        self.error_raw_text.setReadOnly(True)
        self.error_raw_text.setMaximumHeight(80)
        self.error_raw_text.setPlaceholderText("Raw error details...")
        self.error_raw_text.setVisible(False) # Toggle this?
        
        # Let's add a small button to toggle raw text
        self.toggle_details_btn = PushButton("Detayları Göster")
        self.toggle_details_btn.setCheckable(True)
        self.toggle_details_btn.setFixedHeight(24)
        self.toggle_details_btn.clicked.connect(lambda c: self.error_raw_text.setVisible(c))
        
        # Go to line button (Hidden by default)
        self.goto_line_btn = PushButton("Hata Satırına Git")
        self.goto_line_btn.setIcon(FIF.RETURN) # Icon for navigation
        try:
            self.goto_line_btn.clicked.disconnect()
        except:
            pass
        self.goto_line_btn.clicked.connect(self._on_goto_line_clicked)
        self.goto_line_btn.setVisible(False)
        self._target_line_for_nav = None
        self._target_row_for_nav = None
        
        # Error Navigation (Stage 5.4)
        self._structured_errors = []
        self._current_error_index = -1
        
        # Nav Buttons Layout
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)
        
        self.prev_error_btn = PushButton("◀")
        self.prev_error_btn.setFixedWidth(32)
        self.prev_error_btn.clicked.connect(lambda: self._navigate_error(-1))
        self.prev_error_btn.setVisible(False)
        
        self.error_counter_label = BodyLabel("0/0")
        self.error_counter_label.setVisible(False)
        
        self.next_error_btn = PushButton("▶")
        self.next_error_btn.setFixedWidth(32)
        self.next_error_btn.clicked.connect(lambda: self._navigate_error(1))
        self.next_error_btn.setVisible(False)
        
        nav_layout.addWidget(self.prev_error_btn)
        nav_layout.addWidget(self.error_counter_label)
        nav_layout.addWidget(self.next_error_btn)
        nav_layout.addStretch()
        
        # Retry Line Button (New)
        self.retry_line_btn = PushButton("Bu satırı yeniden dene")
        self.retry_line_btn.setIcon(FIF.SYNC)
        self.retry_line_btn.clicked.connect(self._on_retry_line_clicked)
        self.retry_line_btn.setVisible(False)
        
        error_layout.addLayout(nav_layout) # Add nav layout
        error_layout.addWidget(self.goto_line_btn)
        error_layout.addWidget(self.retry_line_btn)
        error_layout.addWidget(self.toggle_details_btn) # Moved toggle down
        error_layout.addWidget(self.error_raw_text)
        
        layout.addWidget(self.error_card)
        
        # Cancel button
        self.cancel_btn = PushButton("İptal", self)
        self.cancel_btn.setIcon(FIF.CLOSE)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_batch_requested.emit)
        layout.addWidget(self.cancel_btn)
        
        layout.addStretch()
    
    def _create_log_tab(self):
        """Create the log tab."""
        self.log_widget = QWidget()
        layout = QVBoxLayout(self.log_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Log title
        layout.addWidget(SubtitleLabel("Log"))
        
        # Log text area
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Copy button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.copy_log_btn = PushButton("Kopyala", self)
        self.copy_log_btn.setIcon(FIF.COPY)
        self.copy_log_btn.clicked.connect(self._copy_log)
        btn_layout.addWidget(self.copy_log_btn)
        
        self.clear_log_btn = PushButton("Temizle", self)
        self.clear_log_btn.setIcon(FIF.DELETE)
        self.clear_log_btn.clicked.connect(self._clear_log)
        btn_layout.addWidget(self.clear_log_btn)
        
        layout.addLayout(btn_layout)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def show_row(self, row_payload: dict):
        """
        Update the Satır tab with row details.
        
        Args:
            row_payload: dict with keys:
                - row_id: int
                - line_num: str
                - item_type: str
                - tag: str
                - original: str
                - translation: str
                - is_modified: bool
                - batch_marker: str (optional)
        """
        self.tabs.setCurrentIndex(0)  # Switch to Satır tab
        
        self.row_number_label.setText(f"Satır: {row_payload.get('line_num', '-')}")
        self.row_type_label.setText(f"Tip: {row_payload.get('item_type', '-')}")
        self.row_tag_label.setText(f"Tag: {row_payload.get('tag', '-')}")
        
        self.original_text.setPlainText(row_payload.get('original', ''))
        self.translation_text.setPlainText(row_payload.get('translation', ''))
        
        # Status
        is_modified = row_payload.get('is_modified', False)
        marker = row_payload.get('batch_marker', '')
        # Stage 6: QC
        qc_flag = row_payload.get('qc_flag', False)
        
        status_text = "Durum: "
        if marker == "AI_FAIL":
            status_text += "Hata"
            self.row_status_label.setText(status_text)
            self.row_status_label.setStyleSheet(f"color: #c42b1c; font-weight: bold;")
        elif qc_flag: # Stage 6
            status_text += "Sorunlu (QC)"
            self.row_status_label.setText(status_text)
            self.row_status_label.setStyleSheet(f"color: #FF8C00; font-weight: bold;") 
        elif is_modified:
            status_text += "Düzenlendi"
            self.row_status_label.setText(status_text)
            self.row_status_label.setStyleSheet(f"color: #0078d4; font-weight: bold;")
        else:
            status_text += "Çevrildi" if row_payload.get('translation') else "Bekliyor"
            self.row_status_label.setText(status_text)
            self.row_status_label.setStyleSheet("color: #000000;" if not isDarkTheme() else "color: #ffffff;")
            
        # Notes
        self.notes_text.setText("") 
        
        # QC Content Update (Stage 6)
        # Note: qc_flag was retrieved above
        qc_summary = row_payload.get('qc_summary', "")
        
        if qc_flag and qc_summary:
            self.qc_card.setVisible(True)
            self.qc_message.setText(qc_summary)
        else:
            self.qc_card.setVisible(False)
            

        logger.debug(f"Inspector showing row: {row_payload.get('row_id', '?')}")
    
    def show_batch_status(self, status: dict):
        """
        Update the Toplu tab with batch status.
        
        Args:
            status: dict with keys:
                - running: bool
                - processed: int
                - total: int
                - success: int
                - failed: int
                - chunk_index: int
                - chunk_total: int
                - errors: int (legacy)
                - warnings: int (legacy)
        """
        # NOTE: Do NOT auto-switch to Toplu tab - let user control their view
        # User reported this as annoying UX: cannot browse other tabs during batch
        
        processed = status.get('processed', 0)
        total = status.get('total', 0)
        running = status.get('running', status.get('is_running', False))
        
        # Update progress
        if total > 0:
            percent = int((processed / total) * 100)
            self.progress_bar.setValue(percent)
        else:
            self.progress_bar.setValue(0)
        
        # Progress text with chunk info
        chunk_idx = status.get('chunk_index', 0)
        chunk_total = status.get('chunk_total', 0)
        if chunk_total > 0:
            self.progress_label.setText(f"{processed} / {total}  (Chunk {chunk_idx + 1}/{chunk_total})")
        else:
            self.progress_label.setText(f"{processed} / {total}")
        
        # Update stats
        success = status.get('success', 0)
        failed = status.get('failed', status.get('errors', 0))
        warnings = status.get('warnings', 0)
        
        self.success_label.setText(f"✅ Başarılı: {success}")
        self.error_label.setText(f"❌ Hata: {failed}")
        self.warning_label.setText(f"⚠️ Uyarı: {warnings}")
        
        # === Smart Error Summary ===
        self.warning_label.setText(f"⚠️ Uyarı: {warnings}")
        
        # Store errors for navigation
        self._structured_errors = status.get('structured_errors', [])
        # Only reset index if different errors or empty? 
        # Actually keep index if valid, else reset to 0
        if not self._structured_errors:
            self._current_error_index = -1
        elif self._current_error_index < 0 or self._current_error_index >= len(self._structured_errors):
            self._current_error_index = 0
            
        # Update Nav Controls visibility
        has_nav = len(self._structured_errors) > 1
        self.prev_error_btn.setVisible(has_nav)
        self.next_error_btn.setVisible(has_nav)
        self.error_counter_label.setVisible(has_nav)
        
        if self._structured_errors:
             self.error_counter_label.setText(f"{self._current_error_index + 1}/{len(self._structured_errors)}")
        
        # === Smart Error Summary ===
        error_summary = status.get('error_summary')
        
        # If we have structured errors and specific index, OVERRIDE summary to show THAT error
        # This allows "Next/Prev" to actually cycle content in the card
        if self._structured_errors and self._current_error_index >= 0:
             # Create ad-hoc summary for the current error
             curr_err = self._structured_errors[self._current_error_index]
             # Parse it
             # Dict keys: row_id, file_line, message, code
             # We can reuse ErrorExplainer logic or manual mapping
             self._update_error_card_from_struct(curr_err)
        elif error_summary:
             self._update_error_card_from_summary(error_summary)
        else:
             self.error_card.setVisible(False)
             
    def _update_error_card_from_struct(self, err_struct: dict):
        """Update error card from a single structured error dict."""
        self.error_card.setVisible(True)
        self.error_title.setText(f"Hata ({err_struct.get('code', 'UNKNOWN')})")
        self.error_message.setText(err_struct.get('message', 'Detay yok.'))
        self.error_suggestions.setVisible(False) # Individual errors might not have sophisticated suggestions yet
        
        # Setup Nav Targets
        row_id = err_struct.get('row_id')
        file_line = err_struct.get('file_line')
        
        if row_id is not None:
             self._target_row_for_nav = row_id
             self._target_line_for_nav = file_line if file_line is not None else (row_id + 1)
             
             display_line = file_line if file_line is not None else "?"
             display_row = row_id + 1
             
             btn_text = f"Hata Satırına Git (Tablo: {display_row} • Dosya: {display_line})"
             self.goto_line_btn.setText(btn_text)
             self.goto_line_btn.setVisible(True)
             self.retry_line_btn.setVisible(True)
        else:
             self.goto_line_btn.setVisible(False)
             self.retry_line_btn.setVisible(False)
             
    def _update_error_card_from_summary(self, error_summary):
        """Standard update from overall summary."""
        if error_summary:
            self.error_card.setVisible(True)
            self.error_title.setText(error_summary.get('title', "Hata"))
            self.error_message.setText(error_summary.get('message', ""))
            
            suggestions = error_summary.get('suggestions', [])
            if suggestions:
                s_text = "Öneriler:\n" + "\n".join([f"• {s}" for s in suggestions])
                self.error_suggestions.setText(s_text)
                self.error_suggestions.setVisible(True)
            else:
                self.error_suggestions.setVisible(False)
                
            raw = error_summary.get('raw_sample')
            if raw:
                self.error_raw_text.setText(str(raw))
                self.toggle_details_btn.setVisible(True)
                
                # Check for structured row/line info first
                row_id = error_summary.get('row_id')
                file_line = error_summary.get('file_line')
                
                if row_id is not None:
                     # Structured error available
                     self._target_row_for_nav = row_id
                     self._target_line_for_nav = file_line if file_line is not None else (row_id + 1)
                     
                     display_line = file_line if file_line is not None else "?"
                     display_row = row_id + 1
                     
                     btn_text = f"Hata Satırına Git (Tablo: {display_row} • Dosya: {display_line})"
                     self.goto_line_btn.setText(btn_text)
                     self.goto_line_btn.setVisible(True)
                     self.retry_line_btn.setVisible(True)
                     
                else:
                    # Legacy fallback: Try to extract line number from string
                    # Matches: "Line 123:", "Line 123", "at line 123", etc.
                    match = re.search(r'(?:line|satır)\s*(\d+)', str(raw), re.IGNORECASE)
                    if match:
                        line_num = int(match.group(1))
                        self._target_line_for_nav = line_num
                        self._target_row_for_nav = None # No sure way to know row index from just line number without model access
                        # Fallback: assume 1-1 mapping or just use file navigation if supported
                        # But for "Accurate Navigation" we prefer row index.
                        # If we lack row_id, disable strict row nav or try best effort.
                        
                        self.goto_line_btn.setText(f"Hata Satırına Git ({line_num})")
                        self.goto_line_btn.setVisible(True)
                        self.retry_line_btn.setVisible(True)
                    else:
                        self._target_line_for_nav = None
                        self._target_row_for_nav = None
                        self.goto_line_btn.setVisible(False)
                        self.retry_line_btn.setVisible(False)
            else:
                self.toggle_details_btn.setVisible(False)
                self.goto_line_btn.setVisible(False)
                self.retry_line_btn.setVisible(False)
        else:
            self.error_card.setVisible(False)
    
    def _navigate_error(self, direction):
        """Navigate to next/prev error in list."""
        if not self._structured_errors:
            return
            
        new_idx = self._current_error_index + direction
        # Cycle
        if new_idx < 0:
            new_idx = len(self._structured_errors) - 1
        elif new_idx >= len(self._structured_errors):
            new_idx = 0
            
        self._current_error_index = new_idx
        
        # Update counter
        self.error_counter_label.setText(f"{self._current_error_index + 1}/{len(self._structured_errors)}")
        
        # Update card content immediately
        curr_err = self._structured_errors[self._current_error_index]
        self._update_error_card_from_struct(curr_err)
        
        # Auto-navigate to that row! (Requirement A: "Each click triggers navigation")
        if self._target_row_for_nav is not None:
             self.navigate_row_requested.emit(self._target_row_for_nav)
    
    def append_log(self, text: str):
        """
        Append text to the log tab.
        
        Ring buffer behavior: Keeps max 1000 lines, removes oldest when exceeded.
        
        Args:
            text: Log message to append
        """
        from PySide6.QtGui import QTextCursor
        
        MAX_LOG_LINES = 1000
        
        self.log_text.append(text)
        
        # Ring buffer: remove oldest lines if exceeded
        doc = self.log_text.document()
        if doc.blockCount() > MAX_LOG_LINES:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            # Remove excess lines from the beginning
            lines_to_remove = doc.blockCount() - MAX_LOG_LINES
            for _ in range(lines_to_remove):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # Remove the newline
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_batch_status(self):
        """Reset batch status display."""
        self.show_batch_status({
            'processed': 0,
            'total': 0,
            'success': 0,
            'errors': 0,
            'warnings': 0,
            'is_running': False
        })
        self.batch_title.setText("Toplu İşlem")
    
    # =========================================================================
    # PRIVATE
    # =========================================================================
    
    def _on_goto_line_clicked(self):
        """Handle go to line/row clicked."""
        if self._target_row_for_nav is not None:
             self.navigate_row_requested.emit(self._target_row_for_nav)
        elif self._target_line_for_nav is not None:
             self.navigate_requested.emit(self._target_line_for_nav)

    def _on_retry_line_clicked(self):
        """Handle retry line clicked."""
        row_id = -1
        if self._target_row_for_nav is not None:
             row_id = self._target_row_for_nav
        elif self._target_line_for_nav is not None:
             row_id = self._target_line_for_nav - 1
             
        if row_id >= 0:
            self.retry_line_btn.setEnabled(False) # Disable to prevent double click
            self.retry_line_requested.emit(row_id)
            QTimer.singleShot(2000, lambda: self.retry_line_btn.setEnabled(True))
             
    def _copy_log(self):
        """Copy log contents to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        logger.debug("Log copied to clipboard")
    
    def _clear_log(self):
        """Clear log contents."""
        self.log_text.clear()
        logger.debug("Log cleared")
    
    def _on_pin_clicked(self):
        """Pin/unpin butonu tıklandığında paneli gizle."""
        self.toggle_visibility()
    
    def toggle_visibility(self):
        """Panel görünürlüğünü değiştir."""
        new_visible = not self.isVisible()
        self.setVisible(new_visible)
        self.visibility_changed.emit(new_visible)
        logger.debug(f"Inspector visibility toggled: {new_visible}")
    
    def show_empty_state(self):
        """Satır seçili değilken empty state göster."""
        self.row_number_label.setText("Satır: -")
        self.row_type_label.setText("Tip: -")
        self.row_tag_label.setText("Tag: -")
        self.original_text.setPlainText("")
        self.translation_text.setPlainText("")
        self.status_label.setText("Durum: Satır seçilmedi")
        self.modified_label.setText("")
        self.notes_text.setPlainText("")

