# -*- coding: utf-8 -*-
"""
RenForge Health Page

Dashboard showing project health, run history, and quick actions.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QFrame, QFileDialog
)

from qfluentwidgets import (
    BodyLabel, SubtitleLabel, StrongBodyLabel, TitleLabel,
    PushButton, CardWidget, FluentIcon as FIF,
    InfoBar, InfoBarPosition, ComboBox, SegmentedWidget
)

from renforge_logger import get_logger
from core.run_history_store import RunHistoryStore, RunRecord
from core.run_analytics import compute_run_deltas, compute_trends

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


class RunDetailsCard(CardWidget):
    """
    Card showing detailed information about a selected run (Stage 9).
    
    Displays context, error items list, QC items list, and report actions.
    """
    
    # Signal when user clicks an item to navigate
    item_clicked = Signal(int, str)  # (row_id, mode: 'error' or 'qc')
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Header with run info
        header_layout = QHBoxLayout()
        self.header_label = StrongBodyLabel("Çalışma Detayları")
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        
        self.timestamp_label = BodyLabel("")
        self.timestamp_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self.timestamp_label)
        layout.addLayout(header_layout)
        
        # Context grid
        self.context_grid = QGridLayout()
        self.context_grid.setSpacing(8)
        self._context_labels = {}
        
        context_items = [
            ("Sağlayıcı:", "provider"), ("Model:", "model"),
            ("Kaynak:", "source_lang"), ("Hedef:", "target_lang"),
            ("İşlenen:", "processed"), ("Başarılı:", "success"),
            ("Hata:", "errors"), ("Süre:", "duration")
        ]
        for i, (label_text, key) in enumerate(context_items):
            row, col = divmod(i, 4)
            label = BodyLabel(label_text)
            label.setStyleSheet("color: #888;")
            self.context_grid.addWidget(label, row * 2, col * 2)
            
            value_label = BodyLabel("-")
            self._context_labels[key] = value_label
            self.context_grid.addWidget(value_label, row * 2, col * 2 + 1)
        
        layout.addLayout(self.context_grid)
        
        # Errors section
        self.errors_header = StrongBodyLabel("Hatalar")
        layout.addWidget(self.errors_header)
        
        self.errors_list = QVBoxLayout()
        self.errors_list.setSpacing(4)
        layout.addLayout(self.errors_list)
        
        # QC section
        self.qc_header = StrongBodyLabel("QC Sorunları")
        layout.addWidget(self.qc_header)
        
        self.qc_list = QVBoxLayout()
        self.qc_list.setSpacing(4)
        layout.addLayout(self.qc_list)
        
        # Empty/old run message
        self.empty_label = BodyLabel("")
        self.empty_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.empty_label)
        
        # Report actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        self.copy_btn = PushButton("Kopyala")
        self.copy_btn.setIcon(FIF.COPY)
        self.copy_btn.setToolTip("Raporu kopyala (Markdown)")
        self.copy_btn.setEnabled(False)
        actions_layout.addWidget(self.copy_btn)
        
        self.save_md_btn = PushButton("Kaydet (MD)")
        self.save_md_btn.setIcon(FIF.SAVE)
        self.save_md_btn.setToolTip("Raporu kaydet (Markdown)")
        self.save_md_btn.setEnabled(False)
        actions_layout.addWidget(self.save_md_btn)
        
        self.save_json_btn = PushButton("JSON")
        self.save_json_btn.setIcon(FIF.CODE)
        self.save_json_btn.setToolTip("Raporu kaydet (JSON)")
        self.save_json_btn.setEnabled(False)
        actions_layout.addWidget(self.save_json_btn)
        
        # Separator or spacing
        actions_layout.addSpacing(8)
        
        # Debug Bundle (Stage 11)
        self.debug_bundle_btn = PushButton("Debug Bundle")
        self.debug_bundle_btn.setIcon(FIF.DEVELOPER_TOOLS)
        self.debug_bundle_btn.setToolTip("Geliştirici paketi kopyala (Loglar + Rapor)")
        self.debug_bundle_btn.setEnabled(False)
        actions_layout.addWidget(self.debug_bundle_btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def set_run(self, run, format_duration_fn=None):
        """
        Update card with run details.
        
        Args:
            run: RunRecord object or None
            format_duration_fn: Optional function to format duration_ms
        """
        self._clear_lists()
        
        if not run:
            self.header_label.setText("Çalışma Detayları")
            self.timestamp_label.setText("")
            self.empty_label.setText("Çalışma seçilmedi")
            for label in self._context_labels.values():
                label.setText("-")
            self.copy_btn.setEnabled(False)
            self.save_md_btn.setEnabled(False)
            self.save_json_btn.setEnabled(False)
            self.debug_bundle_btn.setEnabled(False)
            return
        
        # Update header
        self.header_label.setText(f"Çalışma: {run.file_name or 'Dosya'}")
        self.timestamp_label.setText(run.timestamp)
        
        # Update context
        self._context_labels['provider'].setText(run.provider or "-")
        self._context_labels['model'].setText(run.model or "-")
        self._context_labels['source_lang'].setText(run.source_lang or "-")
        self._context_labels['target_lang'].setText(run.target_lang or "-")
        self._context_labels['processed'].setText(str(run.processed))
        self._context_labels['success'].setText(str(run.success_updated))
        self._context_labels['errors'].setText(str(run.errors_count))
        
        if format_duration_fn:
            self._context_labels['duration'].setText(format_duration_fn(run.duration_ms))
        else:
            self._context_labels['duration'].setText(f"{run.duration_ms}ms")
        
        # Populate error items
        if run.error_items:
            self.empty_label.setText("")
            for err in run.error_items[:10]:  # Limit to 10
                self._add_item(
                    self.errors_list,
                    err.get('row_id', 0),
                    err.get('file_line', 0),
                    err.get('code', 'UNKNOWN'),
                    err.get('message', ''),
                    'error'
                )
        elif run.errors_count > 0:
            # Old run without detailed items
            lbl = BodyLabel("Bu çalışma eski sürümden, satır detayı yok.")
            lbl.setStyleSheet("color: #888; font-style: italic;")
            self.errors_list.addWidget(lbl)
        
        # Populate QC items
        if run.qc_items:
            for qc in run.qc_items[:10]:  # Limit to 10
                codes_str = ', '.join(qc.get('qc_codes', []))
                self._add_item(
                    self.qc_list,
                    qc.get('row_id', 0),
                    qc.get('file_line', 0),
                    codes_str,
                    qc.get('qc_summary', ''),
                    'qc'
                )
        elif run.qc_count_updated > 0:
            # Old run without detailed items
            lbl = BodyLabel("Bu çalışma eski sürümden, QC detayı yok.")
            lbl.setStyleSheet("color: #888; font-style: italic;")
            self.qc_list.addWidget(lbl)
        
        # Enable copy for runs with data
        self.copy_btn.setEnabled(True)
        self.save_md_btn.setEnabled(True)
        self.save_json_btn.setEnabled(True)
        self.debug_bundle_btn.setEnabled(True)
    
    def _add_item(self, layout, row_id: int, file_line: int, code: str, message: str, mode: str):
        """Add a clickable item row."""
        display = f"Tablo: {row_id + 1} • Dosya: {file_line} • {code}"
        if message:
            display += f" — {message[:40]}"
        
        btn = PushButton(display)
        btn.setFlat(True)
        btn.setStyleSheet("text-align: left; padding: 4px 8px;")
        btn.clicked.connect(lambda: self.item_clicked.emit(row_id, mode))
        layout.addWidget(btn)
    
    def _clear_lists(self):
        """Clear error and QC lists."""
        for layout in [self.errors_list, self.qc_list]:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

class CompareCard(CardWidget):
    """Card for comparing selected run with baseline (Stage 12)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        icon = FIF.COMPLETED.icon()
        icon_label = BodyLabel()
        icon_label.setPixmap(icon.pixmap(18, 18))
        header_layout.addWidget(icon_label)
        
        title = StrongBodyLabel("Karşılaştırma")
        header_layout.addWidget(title)
        
        self.baseline_combo = ComboBox()
        self.baseline_combo.setPlaceholderText("Referans Seçin...")
        self.baseline_combo.setMinimumWidth(200)
        self.baseline_combo.currentIndexChanged.connect(self._on_baseline_changed)
        header_layout.addStretch()
        header_layout.addWidget(self.baseline_combo)
        
        layout.addLayout(header_layout)
        
        # Content
        self.content_layout = QGridLayout()
        self.content_layout.setVerticalSpacing(8)
        self.content_layout.setHorizontalSpacing(16)
        layout.addLayout(self.content_layout)
        
        # Details (Top changes)
        self.changes_label = BodyLabel()
        self.changes_label.setWordWrap(True)
        self.changes_label.setStyleSheet("color: #666;")
        layout.addWidget(self.changes_label)
        
        self._current_run = None
        self._baseline_run = None
        self._all_runs = []
    
    def set_runs(self, current: RunRecord, all_runs: list):
        """Update the comparison view."""
        self._current_run = current
        self._all_runs = all_runs
        
        # Store mapping of combo index to run index
        self._combo_to_run_idx = {}
        
        old_selection = self.baseline_combo.currentIndex()
        
        self.baseline_combo.blockSignals(True)
        self.baseline_combo.clear()
        
        # Add "Previous Run" option (dynamic)
        self.baseline_combo.addItem("Önceki Çalıştırma (Otomatik)")
        self._combo_to_run_idx[0] = "PREVIOUS"
        
        combo_idx = 1
        for i, r in enumerate(reversed(all_runs)):  # Newest first
            if r.timestamp == current.timestamp:
                continue 
            
            # Format: "YYYY-MM-DD HH:MM | File | Model"
            label = f"{r.timestamp[:16]} | {r.file_name or 'Unknown'} | {r.model or '-'}"
            self.baseline_combo.addItem(label)
            # Store actual index in all_runs (reversed order mapping)
            actual_idx = len(all_runs) - 1 - i
            self._combo_to_run_idx[combo_idx] = actual_idx
            combo_idx += 1
            
        self.baseline_combo.blockSignals(False)
        
        # Restore selection or default
        if old_selection > 0 and old_selection < self.baseline_combo.count():
            self.baseline_combo.setCurrentIndex(old_selection)
        else:
            self.baseline_combo.setCurrentIndex(0)  # Previous
            
        self._update_display()
        
    def _on_baseline_changed(self):
        self._update_display()
        
    def _update_display(self):
        if not self._current_run or not self._all_runs:
            self._clear_display("Karşılaştırma için çalışma verisi yok.")
            return
        
        if not hasattr(self, '_combo_to_run_idx'):
            self._clear_display("Karşılaştırma verisi henüz yüklenmedi.")
            return
            
        # Determine baseline using combo index mapping
        combo_idx = self.baseline_combo.currentIndex()
        mapped_value = self._combo_to_run_idx.get(combo_idx, "PREVIOUS")
        
        baseline = None
        is_oldest_run = False
        
        if mapped_value == "PREVIOUS":
            # Find current run's position by comparing timestamps
            current_ts = self._current_run.timestamp
            current_idx = -1
            
            for i, r in enumerate(self._all_runs):
                if r.timestamp == current_ts:
                    current_idx = i
                    break
            
            if current_idx == -1:
                # Fallback: try object identity
                try:
                    current_idx = self._all_runs.index(self._current_run)
                except ValueError:
                    current_idx = -1
            
            if current_idx > 0:
                # Previous run exists (older run)
                baseline = self._all_runs[current_idx - 1]
            elif current_idx == 0:
                # This is the oldest run
                is_oldest_run = True
        else:
            # mapped_value is an index into _all_runs
            if isinstance(mapped_value, int) and 0 <= mapped_value < len(self._all_runs):
                baseline = self._all_runs[mapped_value]
            
        if not baseline:
            if is_oldest_run:
                self._clear_display("Bu çalışma için önceki bir referans yok. Karşılaştırmak için başka bir referans seçin.")
            else:
                self._clear_display("Referans çalışma bulunamadı.")
            return

        # Compute Deltas
        delta = compute_run_deltas(self._current_run, baseline)
        
        # Clear layout
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Add Delta Badges
        # Columns: Metric | Cur | Baseline | Delta
        
        headers = ["Metrik", "Seçili", "Referans", "Fark"]
        for c, h in enumerate(headers):
             l = StrongBodyLabel(h)
             self.content_layout.addWidget(l, 0, c)
             
        metrics = [
            ("Hatalar", self._current_run.errors_count, baseline.errors_count, delta.error_delta, True), # True=Lower is better
            ("QC Sorunları", self._current_run.qc_count_total, baseline.qc_count_total, delta.qc_delta, True),
            ("Süre (ms)", self._current_run.duration_ms, baseline.duration_ms, delta.duration_delta_ms, True),
            ("Başarılı", self._current_run.success_updated, baseline.success_updated, delta.success_delta, False) # Higher is better
        ]
        
        for r, (name, cur, base, chg, lower_better) in enumerate(metrics, 1):
            self.content_layout.addWidget(BodyLabel(name), r, 0)
            self.content_layout.addWidget(BodyLabel(str(cur)), r, 1)
            self.content_layout.addWidget(BodyLabel(str(base)), r, 2)
            
            # Change badge
            prefix = "+" if chg > 0 else ""
            lbl = StrongBodyLabel(f"{prefix}{chg}")
            
            # Color logic
            is_good = False
            if chg == 0:
                color = "#888" # Grey
            elif lower_better:
                is_good = chg < 0
            else:
                is_good = chg > 0
                
            if chg != 0:
                color = "#2da44e" if is_good else "#cf222e" # Green/Red matches GitHub style
                lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            else:
                lbl.setStyleSheet("color: #888;")
                
            self.content_layout.addWidget(lbl, r, 3)
            
        # Top Changes Text
        txt = ""
        if delta.is_legacy:
            txt = "Detaylı karşılaştırma için modern çalışma verisi gerekli."
        else:
            changes = []
            if delta.top_error_increases:
                changes.append("Artış (Hata): " + ", ".join([f"{c} (+{v})" for c,v in delta.top_error_increases]))
            if delta.top_error_decreases:
                changes.append("Azalış (Hata): " + ", ".join([f"{c} ({v})" for c,v in delta.top_error_decreases]))
            
            txt = "\n".join(changes) if changes else "Kategori bazında önemli değişiklik yok."
            
        self.changes_label.setText(txt)

    def _clear_display(self, msg="Karşılaştırma için veri yok."):
         # simple reset
         while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
         self.changes_label.setText(msg)

class TrendCard(CardWidget):
    """Card for trend analysis stats (Stage 12)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("Trend Analizi"))
        
        self.seg_widget = SegmentedWidget()
        self.seg_widget.addItem("5", "Son 5")
        self.seg_widget.addItem("10", "Son 10")
        self.seg_widget.addItem("20", "Son 20")
        self.seg_widget.setCurrentItem("10")
        self.seg_widget.currentItemChanged.connect(self._on_n_changed)
        header.addStretch()
        header.addWidget(self.seg_widget)
        layout.addLayout(header)
        
        self.stats_layout = QHBoxLayout()
        layout.addLayout(self.stats_layout)
        
        self.problem_label = BodyLabel()
        self.problem_label.setWordWrap(True)
        layout.addWidget(self.problem_label)
        
        self._runs = []
        
    def set_runs(self, runs: list):
        self._runs = runs
        self._update()
        
    def _on_n_changed(self, *args):
        self._update()
        
    def _update(self):
        try:
            n = int(self.seg_widget.currentItem().routeKey())
        except:
            n = 10
            
        stats = compute_trends(self._runs, n)
        
        # Clear stats layout
        while self.stats_layout.count():
            c = self.stats_layout.takeAt(0)
            if c.widget(): 
                c.widget().deleteLater()
            elif c.layout():
                # Clear nested layout
                while c.layout().count():
                    item = c.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            
        # Helper: Format duration
        def fmt_dur(ms):
            if ms < 1000:
                return f"{int(ms)}ms"
            elif ms < 60000:
                return f"{ms/1000:.1f}s"
            else:
                mins = int(ms // 60000)
                secs = int((ms % 60000) / 1000)
                return f"{mins}m {secs}s"
        
        # Add summary blocks (exactly 5 KPIs)
        def add_stat(label, val):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(2)
            lbl = BodyLabel(label)
            lbl.setStyleSheet("color: #666;")
            vbox.addWidget(lbl)
            vbox.addWidget(TitleLabel(val))
            self.stats_layout.addWidget(container)
        
        # 1. Ort. Hata
        add_stat("Ort. Hata", f"{stats.avg_errors:.1f}")
        
        # 2. Ort. Süre
        add_stat("Ort. Süre", fmt_dur(stats.avg_duration_ms))
        
        # 3. Medyan Süre
        add_stat("Medyan Süre", fmt_dur(stats.median_duration_ms))
        
        # 4. Hatasız Çalışma Oranı (run-level)
        add_stat("Hatasız Çalışma", f"%{int(round(stats.error_free_rate))}")
        
        # 5. Hatasız Satır Oranı (line-level)
        if stats.line_success_rate >= 0:
            add_stat("Satır Başarısı", f"%{int(round(stats.line_success_rate))}")
        else:
            add_stat("Satır Başarısı", "—")
        
        # Problematic Models
        if stats.problematic_models:
            probs = [f"{m}: %{rate} hata oranı" for m, rate in stats.problematic_models]
            self.problem_label.setText("En Sorunlu Modeller:\n" + "\n".join(probs))
        else:
            self.problem_label.setText("Sorunlu model tespit edilmedi.")

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
        
        # Middle column: Run Details + Analytics (Stage 12)
        middle_layout = QVBoxLayout()
        middle_layout.setSpacing(16)
        
        self.run_details = RunDetailsCard()
        self.run_details.item_clicked.connect(self._on_detail_item_clicked)
        self.run_details.copy_btn.clicked.connect(self._on_copy_report)
        self.run_details.save_md_btn.clicked.connect(self._on_save_report_md)
        self.run_details.save_json_btn.clicked.connect(self._on_save_report_json)
        self.run_details.debug_bundle_btn.clicked.connect(self._on_copy_debug_bundle)
        middle_layout.addWidget(self.run_details)
        
        # Analytics Cards
        self.compare_card = CompareCard()
        middle_layout.addWidget(self.compare_card)
        
        self.trend_card = TrendCard()
        middle_layout.addWidget(self.trend_card)
        
        middle_layout.addStretch() # Ensure cards are top-aligned if meaningful
        
        grid_layout.addLayout(middle_layout, 2)  # Middle gets flex 2
        
        # Right column: Trend
        self.run_trend = TrendListCard("Son Çalıştırmalar")
        self.run_trend.run_selected.connect(self._on_run_selected)
        grid_layout.addWidget(self.run_trend, 1)
        
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
        # Run selection is already connected in _setup_ui via run_trend.run_selected
        pass
    
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
            
            # Note: RunDetails card handles its own button states via set_run
            
            self.goto_first_error_btn.setEnabled(False)
            self.goto_last_error_btn.setEnabled(False)
            self.goto_first_qc_btn.setEnabled(False)
            self.goto_last_qc_btn.setEnabled(False)
        
        # Update categories
        self.error_categories.set_items(stats.get('error_category_totals', []))
        self.qc_categories.set_items(stats.get('qc_code_totals', []))
        
        # Update trend analytics
        self.trend_card.set_runs(runs)
        
        # Update run history list (TrendListCard)
        self.run_trend.set_runs(runs)
        
        # Update compare card (Stage 12)
        if self._selected_run and runs:
            self.compare_card.set_runs(self._selected_run, runs)
        
        # Update run details (Stage 9)
        self.run_details.set_run(self._selected_run, self._format_duration_ms)

        logger.debug(f"Health page refreshed: {len(runs)} runs")
    
    def showEvent(self, event):
        """Refresh when page is shown."""
        super().showEvent(event)
        self.refresh()
    
    def _on_copy_report(self):
        """Copy selected run report to clipboard (Stage 10)."""
        if not self._selected_run:
            return
            
        try:
            from core.batch_report import build_markdown_from_run
            from PySide6.QtGui import QClipboard, QGuiApplication
            
            report = build_markdown_from_run(self._selected_run)
            QGuiApplication.clipboard().setText(report)
            
            InfoBar.success(
                title="Kopyalandı",
                content="Rapor panoya kopyalandı",
                parent=self,
                duration=2000
            )
        except Exception as e:
            logger.error(f"Copy report failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Rapor kopyalanamadı: {e}",
                parent=self
            )

    def _on_save_report_md(self):
        """Save selected run report as Markdown (Stage 10)."""
        if not self._selected_run:
            return
            
        try:
            from core.batch_report import build_markdown_from_run
            
            # Default filename
            ts = self._selected_run.timestamp.replace(':', '-').replace(' ', '_')
            default_name = f"renforge_report_{ts}.md"
            
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Raporu Kaydet (Markdown)",
                default_name,
                "Markdown Files (*.md);;All Files (*.*)"
            )
            
            if path:
                report = build_markdown_from_run(self._selected_run)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                InfoBar.success(
                    title="Kaydedildi",
                    content=f"Rapor kaydedildi:\n{path}",
                    parent=self,
                    duration=3000
                )
        except Exception as e:
            logger.error(f"Save MD failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Kaydetme başarısız: {e}",
                parent=self
            )

    def _on_save_report_json(self):
        """Save selected run report as JSON (Stage 10)."""
        if not self._selected_run:
            return
            
        try:
            from core.batch_report import format_json_from_run
            
            # Default filename
            ts = self._selected_run.timestamp.replace(':', '-').replace(' ', '_')
            default_name = f"renforge_report_{ts}.json"
            
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Raporu Kaydet (JSON)",
                default_name,
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if path:
                report = format_json_from_run(self._selected_run)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                InfoBar.success(
                    title="Kaydedildi",
                    content=f"Rapor kaydedildi:\n{path}",
                    parent=self,
                    duration=3000
                )
        except Exception as e:
            logger.error(f"Save JSON failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Kaydetme başarısız: {e}",
                parent=self
            )
            
    def _on_copy_debug_bundle(self):
        """Copy debug bundle to clipboard (Stage 11)."""
        if not self._selected_run:
            return
            
        try:
            from core.debug_bundle import build_debug_bundle
            from PySide6.QtGui import QClipboard, QGuiApplication
            
            bundle = build_debug_bundle(self._selected_run)
            QGuiApplication.clipboard().setText(bundle)
            
            InfoBar.success(
                title="Kopyalandı",
                content="Debug bundle panoya kopyalandı",
                parent=self,
                duration=2000
            )
        except Exception as e:
            logger.error(f"Copy debug bundle failed: {e}")
            InfoBar.error(
                title="Hata",
                content=f"Debug bundle oluşturulamadı: {e}",
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
    
    def _on_detail_item_clicked(self, row_id: int, mode: str):
        """Handle click on error/QC item in Run Details."""
        self.navigate_to_row_requested.emit(row_id, mode, True)
