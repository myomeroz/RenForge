# -*- coding: utf-8 -*-
"""
RenForge Health Page

Dashboard showing project health, run history, and quick actions.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QFrame
)

from qfluentwidgets import (
    BodyLabel, SubtitleLabel, StrongBodyLabel, TitleLabel,
    PushButton, CardWidget, FluentIcon as FIF,
    InfoBar, InfoBarPosition
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.health")


class KPICard(CardWidget):
    """Compact KPI display card."""
    
    def __init__(self, title: str, value: str = "-", icon=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setMinimumWidth(150)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Title row
        title_layout = QHBoxLayout()
        if icon:
            icon_label = BodyLabel()
            icon_label.setPixmap(icon.icon().pixmap(16, 16))
            title_layout.addWidget(icon_label)
        
        self.title_label = BodyLabel(title)
        self.title_label.setStyleSheet("color: #888;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Value
        self.value_label = TitleLabel(value)
        layout.addWidget(self.value_label)
        
        layout.addStretch()
    
    def set_value(self, value: str):
        """Update the displayed value."""
        self.value_label.setText(value)


class CategoryListCard(CardWidget):
    """Card showing top categories with click action."""
    
    category_clicked = Signal(str, str)  # (category_type, category_name)
    
    def __init__(self, title: str, category_type: str, parent=None):
        super().__init__(parent)
        self._category_type = category_type
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header
        self.title_label = StrongBodyLabel(title)
        layout.addWidget(self.title_label)
        
        # Items container
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(4)
        layout.addLayout(self.items_layout)
        
        # Empty state
        self.empty_label = BodyLabel("Veri yok")
        self.empty_label.setStyleSheet("color: #888; font-style: italic;")
        self.items_layout.addWidget(self.empty_label)
        
        layout.addStretch()
    
    def set_items(self, items: list):
        """
        Update items list.
        
        Args:
            items: List of (name, count) tuples
        """
        # Clear existing
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not items:
            self.empty_label = BodyLabel("Veri yok")
            self.empty_label.setStyleSheet("color: #888; font-style: italic;")
            self.items_layout.addWidget(self.empty_label)
            return
        
        for name, count in items:
            row = QHBoxLayout()
            
            # Clickable name
            name_btn = PushButton(name)
            name_btn.setFlat(True)
            name_btn.setStyleSheet("text-align: left; padding: 2px 4px;")
            name_btn.clicked.connect(lambda checked, n=name: self._on_item_clicked(n))
            row.addWidget(name_btn)
            
            row.addStretch()
            
            # Count badge
            count_label = BodyLabel(str(count))
            count_label.setStyleSheet(
                "background: #444; color: #fff; padding: 2px 8px; border-radius: 10px;"
            )
            row.addWidget(count_label)
            
            container = QWidget()
            container.setLayout(row)
            self.items_layout.addWidget(container)
    
    def _on_item_clicked(self, name: str):
        """Emit signal when category clicked."""
        self.category_clicked.emit(self._category_type, name)


class TrendListCard(CardWidget):
    """Card showing run history trend as a simple list."""
    
    # Signal emitted when user selects a run
    run_selected = Signal(int)  # (run_index)
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        
        self._selected_index = 0  # Currently selected run
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header
        self.title_label = StrongBodyLabel(title)
        layout.addWidget(self.title_label)
        
        # Column headers
        header_layout = QHBoxLayout()
        header_layout.addWidget(BodyLabel("Tarih"))
        header_layout.addStretch()
        header_layout.addWidget(BodyLabel("Hata"))
        header_layout.addWidget(BodyLabel("QC"))
        layout.addLayout(header_layout)
        
        # Items container
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(2)
        layout.addLayout(self.items_layout)
        
        layout.addStretch()
    
    def set_runs(self, runs: list):
        """
        Update trend list with runs.
        
        Args:
            runs: List of RunRecord objects
        """
        # Clear existing
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not runs:
            empty = BodyLabel("Henüz çalıştırma yok")
            empty.setStyleSheet("color: #888; font-style: italic;")
            self.items_layout.addWidget(empty)
            return
        
        self._run_widgets = []  # Store for selection highlighting
        
        for idx, run in enumerate(runs):
            row = QHBoxLayout()
            
            # Timestamp (short format)
            ts = run.timestamp
            if ' ' in ts:
                ts = ts.split(' ')[0]  # Just date
            
            # Make timestamp clickable
            ts_btn = PushButton(ts[:10] if len(ts) >= 10 else ts)
            ts_btn.setFlat(True)
            ts_btn.setStyleSheet("text-align: left; padding: 2px 4px;")
            ts_btn.clicked.connect(lambda checked, i=idx: self._on_run_clicked(i))
            row.addWidget(ts_btn)
            
            row.addStretch()
            
            # Error count
            err_label = BodyLabel(str(run.errors_count))
            if run.errors_count > 0:
                err_label.setStyleSheet("color: #f44336; font-weight: bold;")
            row.addWidget(err_label)
            
            # QC count
            qc_label = BodyLabel(str(run.qc_count_updated))
            if run.qc_count_updated > 0:
                qc_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            row.addWidget(qc_label)
            
            container = QWidget()
            container.setLayout(row)
            
            # Highlight selected row
            if idx == self._selected_index:
                container.setStyleSheet("background: rgba(100, 100, 255, 0.2); border-radius: 4px;")
            
            self._run_widgets.append(container)
            self.items_layout.addWidget(container)
    
    def _on_run_clicked(self, index: int):
        """Handle run row click."""
        self._selected_index = index
        self.run_selected.emit(index)
        
        # Update visual selection
        for i, widget in enumerate(self._run_widgets):
            if i == index:
                widget.setStyleSheet("background: rgba(100, 100, 255, 0.2); border-radius: 4px;")
            else:
                widget.setStyleSheet("")


class HealthPage(QWidget):
    """
    Health dashboard page showing project stats and run history.
    """
    
    # Signals for navigation
    navigate_to_translate = Signal()
    navigate_to_first_error = Signal()
    navigate_to_first_qc = Signal()
    filter_by_error_category = Signal(str)  # category name
    filter_by_qc_code = Signal(str)  # QC code
    
    # New signal for row-specific navigation (Stage 8.2)
    # Args: (row_id: int, mode: str, apply_filter: bool)
    navigate_to_row_requested = Signal(int, str, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("healthPage")
        
        # Selected run tracking (Stage 8.2)
        self._selected_run_index = 0  # 0 = latest run
        self._selected_run = None     # Current selected RunRecord
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the health dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = TitleLabel("Proje Sağlığı")
        layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)
        
        # === KPI Cards Row ===
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)
        
        self.kpi_success = KPICard("Başarılı", "-", FIF.ACCEPT)
        self.kpi_errors = KPICard("Hata", "-", FIF.CLOSE)
        self.kpi_qc = KPICard("QC Sorun", "-", FIF.INFO)
        self.kpi_duration = KPICard("Süre", "-", FIF.SPEED_OFF)
        
        kpi_layout.addWidget(self.kpi_success)
        kpi_layout.addWidget(self.kpi_errors)
        kpi_layout.addWidget(self.kpi_qc)
        kpi_layout.addWidget(self.kpi_duration)
        kpi_layout.addStretch()
        
        content_layout.addLayout(kpi_layout)
        
        # === Quick Actions Row ===
        actions_card = CardWidget()
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(16, 12, 16, 12)
        actions_layout.setSpacing(8)
        
        actions_label = StrongBodyLabel("Hızlı Eylemler:")
        actions_layout.addWidget(actions_label)
        
        self.copy_report_btn = PushButton("Raporu Kopyala")
        self.copy_report_btn.setIcon(FIF.COPY)
        self.copy_report_btn.clicked.connect(self._on_copy_report)
        actions_layout.addWidget(self.copy_report_btn)
        
        # Error navigation buttons
        self.goto_first_error_btn = PushButton("İlk Hataya Git")
        self.goto_first_error_btn.setIcon(FIF.CLOSE)
        self.goto_first_error_btn.clicked.connect(self._on_goto_first_error)
        actions_layout.addWidget(self.goto_first_error_btn)
        
        self.goto_last_error_btn = PushButton("Son Hataya Git")
        self.goto_last_error_btn.setIcon(FIF.CLOSE)
        self.goto_last_error_btn.clicked.connect(self._on_goto_last_error)
        actions_layout.addWidget(self.goto_last_error_btn)
        
        # QC navigation buttons
        self.goto_first_qc_btn = PushButton("İlk QC'ye Git")
        self.goto_first_qc_btn.setIcon(FIF.INFO)
        self.goto_first_qc_btn.clicked.connect(self._on_goto_first_qc)
        actions_layout.addWidget(self.goto_first_qc_btn)
        
        self.goto_last_qc_btn = PushButton("Son QC'ye Git")
        self.goto_last_qc_btn.setIcon(FIF.INFO)
        self.goto_last_qc_btn.clicked.connect(self._on_goto_last_qc)
        actions_layout.addWidget(self.goto_last_qc_btn)
        
        actions_layout.addStretch()
        content_layout.addWidget(actions_card)
        
        # === Main Content Grid ===
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(16)
        
        # Left column: Categories
        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        
        self.error_categories = CategoryListCard("En Çok Görülen Hatalar", "error")
        self.error_categories.category_clicked.connect(self._on_category_clicked)
        left_col.addWidget(self.error_categories)
        
        self.qc_categories = CategoryListCard("En Çok Görülen QC Sorunları", "qc")
        self.qc_categories.category_clicked.connect(self._on_category_clicked)
        left_col.addWidget(self.qc_categories)
        
        left_col.addStretch()
        grid_layout.addLayout(left_col, 1)
        
        # Right column: Trend
        self.trend_card = TrendListCard("Son Çalıştırmalar")
        grid_layout.addWidget(self.trend_card, 1)
        
        content_layout.addLayout(grid_layout)
        
        # Empty state (shown when no data)
        self.empty_state = CardWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 48, 24, 48)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = BodyLabel("📊")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_text = SubtitleLabel("Henüz çalıştırma verisi yok")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text)
        
        empty_hint = BodyLabel("Bir dosya açın ve toplu çeviri yapın")
        empty_hint.setStyleSheet("color: #888;")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_hint)
        
        self.empty_state.setVisible(False)
        content_layout.addWidget(self.empty_state)
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _connect_signals(self):
        """Connect internal signals."""
        # Connect run selection from trend list
        self.trend_card.run_selected.connect(self._on_run_selected)
    
    def _on_run_selected(self, index: int):
        """Handle run selection from trend list."""
        self._selected_run_index = index
        self.refresh()  # Refresh to update KPIs for selected run
    
    def _format_duration_ms(self, ms: int) -> str:
        """
        Format milliseconds to human-readable duration.
        
        d=days (86400000ms), h=hours (3600000ms), m=minutes (60000ms), s=seconds (1000ms)
        """
        if ms < 1000:
            return f"{ms}ms"
        
        secs = ms // 1000
        if secs < 60:
            return f"{secs}s"
        
        mins = secs // 60
        secs = secs % 60
        if mins < 60:
            return f"{mins}m {secs}s"
        
        hours = mins // 60
        mins = mins % 60
        if hours < 24:
            return f"{hours}h {mins}m"
        
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h"
    
    def refresh(self):
        """Refresh the dashboard with latest data."""
        from core.run_history_store import RunHistoryStore
        
        store = RunHistoryStore.instance()
        store.ensure_loaded()
        
        runs = store.get_runs(10)
        stats = store.get_aggregated_stats(10)
        
        # Get selected run (default to latest)
        if runs and self._selected_run_index < len(runs):
            self._selected_run = runs[self._selected_run_index]
        else:
            self._selected_run = runs[0] if runs else None
            self._selected_run_index = 0
        
        # Update empty state
        has_data = len(runs) > 0
        self.empty_state.setVisible(not has_data)
        
        # Update KPIs from selected run
        if self._selected_run:
            run = self._selected_run
            self.kpi_success.set_value(str(run.success_updated))
            self.kpi_errors.set_value(str(run.errors_count))
            self.kpi_qc.set_value(str(run.qc_count_updated))
            
            # Duration formatting
            duration_str = self._format_duration_ms(run.duration_ms)
            self.kpi_duration.set_value(duration_str)
            
            # Enable action buttons based on selected run
            self.copy_report_btn.setEnabled(True)
            has_errors = run.errors_count > 0 or len(run.error_row_ids) > 0
            has_qc = run.qc_count_updated > 0 or len(run.qc_row_ids) > 0
            
            self.goto_first_error_btn.setEnabled(has_errors)
            self.goto_last_error_btn.setEnabled(has_errors)
            self.goto_first_qc_btn.setEnabled(has_qc)
            self.goto_last_qc_btn.setEnabled(has_qc)
        else:
            self.kpi_success.set_value("-")
            self.kpi_errors.set_value("-")
            self.kpi_qc.set_value("-")
            self.kpi_duration.set_value("-")
            
            self.copy_report_btn.setEnabled(False)
            self.goto_first_error_btn.setEnabled(False)
            self.goto_last_error_btn.setEnabled(False)
            self.goto_first_qc_btn.setEnabled(False)
            self.goto_last_qc_btn.setEnabled(False)
        
        # Update categories
        self.error_categories.set_items(stats.get('error_category_totals', []))
        self.qc_categories.set_items(stats.get('qc_code_totals', []))
        
        # Update trend
        self.trend_card.set_runs(runs)
        
        logger.debug(f"Health page refreshed: {len(runs)} runs")
    
    def showEvent(self, event):
        """Refresh when page is shown."""
        super().showEvent(event)
        self.refresh()
    
    def _on_copy_report(self):
        """Copy last run report to clipboard."""
        main_window = self.window()
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            if main_window.batch_controller.copy_report_markdown():
                InfoBar.success(
                    title="Kopyalandı",
                    content="Rapor panoya kopyalandı",
                    parent=self
                )
            else:
                InfoBar.warning(
                    title="Uyarı",
                    content="Kopyalanacak rapor bulunamadı",
                    parent=self
                )
    
    def _on_goto_first_error(self):
        """Navigate to first error row using row ID."""
        if self._selected_run and self._selected_run.error_row_ids:
            row_id = self._selected_run.error_row_ids[0]  # First error
            self.navigate_to_row_requested.emit(row_id, "error", True)
        else:
            self.navigate_to_first_error.emit()  # Fallback to old behavior
    
    def _on_goto_last_error(self):
        """Navigate to last error row using row ID."""
        if self._selected_run and self._selected_run.error_row_ids:
            row_id = self._selected_run.error_row_ids[-1]  # Last error
            self.navigate_to_row_requested.emit(row_id, "error", True)
        else:
            # No row IDs stored (old run) - show warning
            InfoBar.warning(
                title="Uyarı",
                content="Bu çalışma için satır bilgisi yok (eski run)",
                parent=self,
                duration=3000
            )
    
    def _on_goto_first_qc(self):
        """Navigate to first QC issue row using row ID."""
        if self._selected_run and self._selected_run.qc_row_ids:
            row_id = self._selected_run.qc_row_ids[0]  # First QC
            self.navigate_to_row_requested.emit(row_id, "qc", True)
        else:
            self.navigate_to_first_qc.emit()  # Fallback to old behavior
    
    def _on_goto_last_qc(self):
        """Navigate to last QC issue row using row ID."""
        if self._selected_run and self._selected_run.qc_row_ids:
            row_id = self._selected_run.qc_row_ids[-1]  # Last QC
            self.navigate_to_row_requested.emit(row_id, "qc", True)
        else:
            # No row IDs stored (old run) - show warning
            InfoBar.warning(
                title="Uyarı",
                content="Bu çalışma için satır bilgisi yok (eski run)",
                parent=self,
                duration=3000
            )
    
    def _on_category_clicked(self, category_type: str, category_name: str):
        """Handle category item click."""
        if category_type == "error":
            self.filter_by_error_category.emit(category_name)
        elif category_type == "qc":
            self.filter_by_qc_code.emit(category_name)
