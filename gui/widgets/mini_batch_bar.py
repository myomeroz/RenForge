# -*- coding: utf-8 -*-
"""
RenForge Mini Batch Bar

Compact progress bar widget for the Translate page.
Shows batch translation progress inline without requiring Inspector panel.
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy

from qfluentwidgets import (
    BodyLabel, StrongBodyLabel, PushButton, ProgressBar, 
    CardWidget, FluentIcon as FIF
)

from renforge_logger import get_logger

logger = get_logger("gui.widgets.mini_batch_bar")


class MiniBatchBar(CardWidget):
    """
    Compact single-row batch progress bar.
    
    Consumes the same status dict as InspectorPanel.show_batch_status().
    
    UI Layout:
    [Status: Running | 64/11501 (0.6%)] [===ProgressBar===] [✅ 64 ❌ 0 ⚠️ 0] [İptal] [Detay] [Log] [Temizle]
    
    Signals:
        detail_clicked: Request to open Inspector Toplu tab
        log_clicked: Request to open Inspector Log tab
        cancel_clicked: Request to cancel batch
        clear_clicked: Request to hide this bar (UI only)
    """
    
    # Signals
    detail_clicked = Signal()
    log_clicked = Signal()
    cancel_clicked = Signal()
    clear_clicked = Signal()
    
    # Status stage constants (matching BatchController._build_status)
    STAGE_IDLE = "idle"
    STAGE_STARTING = "starting"
    STAGE_RUNNING = "running"
    STAGE_CANCELLING = "cancelling"
    STAGE_CANCELED = "canceled"
    STAGE_COMPLETED = "completed"
    STAGE_FAILED = "failed"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Throttling state
        self._pending_status = None
        self._throttle_timer = QTimer(self)
        self._throttle_timer.setSingleShot(True)
        self._throttle_timer.timeout.connect(self._flush_pending_status)
        self._throttle_interval_ms = 100  # Max 10 updates/second
        
        # Last known progress (monotonic check)
        self._last_done = 0
        self._last_total = 0
        
        self._setup_ui()
        self.setVisible(False)  # Default hidden
        
        logger.debug("MiniBatchBar initialized")
    
    def _setup_ui(self):
        """Setup the compact single-row UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # === Left: Status + Progress Text ===
        self.status_label = StrongBodyLabel("Toplu İşlem")
        self.status_label.setMinimumWidth(180)
        layout.addWidget(self.status_label)
        
        self.progress_text = BodyLabel("0 / 0 (%0)")
        self.progress_text.setMinimumWidth(120)
        layout.addWidget(self.progress_text)
        
        # === Middle: Progress Bar ===
        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimumWidth(150)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar, 1)  # Stretch factor
        
        # === Right: Counters ===
        self.success_label = BodyLabel("✅ 0")
        self.success_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(self.success_label)
        
        self.error_label = BodyLabel("❌ 0")
        self.error_label.setStyleSheet("color: #f44336;")
        layout.addWidget(self.error_label)
        
        self.warning_label = BodyLabel("⚠️ 0")
        self.warning_label.setStyleSheet("color: #ff9800;")
        layout.addWidget(self.warning_label)
        
        layout.addSpacing(8)
        
        # === Right: Action Buttons ===
        self.cancel_btn = PushButton("İptal")
        self.cancel_btn.setIcon(FIF.CLOSE)
        self.cancel_btn.setFixedWidth(80)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self.cancel_btn)
        
        self.detail_btn = PushButton("Detay")
        self.detail_btn.setIcon(FIF.INFO)
        self.detail_btn.setFixedWidth(90)
        self.detail_btn.clicked.connect(self.detail_clicked.emit)
        layout.addWidget(self.detail_btn)
        
        self.log_btn = PushButton("Log")
        self.log_btn.setIcon(FIF.DOCUMENT)
        self.log_btn.setFixedWidth(80)
        self.log_btn.clicked.connect(self.log_clicked.emit)
        layout.addWidget(self.log_btn)
        
        self.clear_btn = PushButton("Temizle")
        self.clear_btn.setIcon(FIF.DELETE)
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setVisible(False)  # Only visible when finished
        layout.addWidget(self.clear_btn)
    
    def show_batch_status(self, status: dict):
        """
        Update the bar with batch status.
        
        Uses throttling to prevent UI overload, but terminal states 
        (completed/canceled/failed) are flushed immediately.
        
        Args:
            status: dict with keys from BatchController._build_status()
                - done/processed, total, ok/success, failed/errors, warnings
                - stage, running/is_running, canceled, cancelling
        """
        stage = status.get('stage', '')
        
        # Terminal states bypass throttling
        terminal_stages = {self.STAGE_COMPLETED, self.STAGE_CANCELED, self.STAGE_FAILED}
        if stage in terminal_stages:
            self._apply_status(status)
            self._pending_status = None
            self._throttle_timer.stop()
            return
        
        # Non-terminal: throttle updates
        self._pending_status = status
        if not self._throttle_timer.isActive():
            self._throttle_timer.start(self._throttle_interval_ms)
    
    def _flush_pending_status(self):
        """Apply pending status after throttle delay."""
        if self._pending_status:
            self._apply_status(self._pending_status)
            self._pending_status = None
    
    def _apply_status(self, status: dict):
        """Actually apply status to UI widgets."""
        # Extract values with fallbacks
        done = status.get('done', status.get('processed', 0))
        total = status.get('total', 0)
        ok = status.get('ok', status.get('success', 0))
        fail = status.get('failed', status.get('errors', 0))
        warn = status.get('warnings', 0)
        stage = status.get('stage', '')
        is_running = status.get('is_running', status.get('running', False))
        is_cancelling = status.get('cancelling', False)
        is_canceled = status.get('canceled', False)
        
        # === Visibility ===
        # Show bar when there's activity or finished state with data
        should_show = is_running or is_cancelling or done > 0 or stage in {
            self.STAGE_STARTING, self.STAGE_RUNNING, self.STAGE_CANCELLING,
            self.STAGE_COMPLETED, self.STAGE_CANCELED, self.STAGE_FAILED
        }
        if should_show and not self.isVisible():
            self.setVisible(True)
            logger.debug("MiniBatchBar shown")
        
        # === Progress (monotonic) ===
        # Only update if progress increased OR we're starting fresh
        if total > 0:
            if done >= self._last_done or total != self._last_total:
                percent = int((done / total) * 100)
                self.progress_bar.setValue(percent)
                self.progress_text.setText(f"{done} / {total} (%{percent})")
                self._last_done = done
                self._last_total = total
        else:
            self.progress_bar.setValue(0)
            self.progress_text.setText("0 / 0")
        
        # === Counters ===
        self.success_label.setText(f"✅ {ok}")
        self.error_label.setText(f"❌ {fail}")
        self.warning_label.setText(f"⚠️ {warn}")
        
        # === Status Label ===
        if stage == self.STAGE_CANCELLING or is_cancelling:
            self.status_label.setText("İptal ediliyor...")
        elif stage == self.STAGE_CANCELED or is_canceled:
            self.status_label.setText("İptal edildi")
        elif stage == self.STAGE_COMPLETED:
            if fail > 0:
                self.status_label.setText(f"Tamamlandı ({fail} hata)")
            else:
                self.status_label.setText("Tamamlandı ✓")
        elif stage == self.STAGE_FAILED:
            self.status_label.setText("Hata ile sonlandı")
        elif stage == self.STAGE_STARTING:
            self.status_label.setText("Başlatılıyor...")
        elif stage == self.STAGE_RUNNING or is_running:
            self.status_label.setText("Çalışıyor...")
        else:
            self.status_label.setText("Toplu İşlem")
        
        # === Button States ===
        # Cancel: enabled only when running AND not already cancelling
        self.cancel_btn.setEnabled(is_running and not is_cancelling)
        if is_cancelling:
            self.cancel_btn.setText("İptal...")
        else:
            self.cancel_btn.setText("İptal")
        
        # Clear: visible only when finished (not running)
        finished = not is_running and (
            stage in {self.STAGE_COMPLETED, self.STAGE_CANCELED, self.STAGE_FAILED}
            or done > 0
        )
        self.clear_btn.setVisible(finished)
        
        logger.debug(f"MiniBatchBar updated: {done}/{total}, stage={stage}, running={is_running}")
    
    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        # Immediately update UI to show cancelling state
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("İptal...")
        self.status_label.setText("İptal ediliyor...")
        
        # Emit signal for controller
        self.cancel_clicked.emit()
        logger.info("MiniBatchBar: Cancel requested")
    
    def _on_clear_clicked(self):
        """Handle clear button click - UI only hide."""
        self.setVisible(False)
        self._reset_ui_state()
        self.clear_clicked.emit()
        logger.debug("MiniBatchBar: Cleared (hidden)")
    
    def _reset_ui_state(self):
        """Reset UI to initial state."""
        self._last_done = 0
        self._last_total = 0
        self.progress_bar.setValue(0)
        self.progress_text.setText("0 / 0")
        self.status_label.setText("Toplu İşlem")
        self.success_label.setText("✅ 0")
        self.error_label.setText("❌ 0")
        self.warning_label.setText("⚠️ 0")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("İptal")
        self.clear_btn.setVisible(False)
