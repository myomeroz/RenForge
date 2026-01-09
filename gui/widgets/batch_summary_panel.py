# -*- coding: utf-8 -*-
"""
RenForge Batch Summary Panel

Collapsible dock widget showing last batch operation results.
"""

from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QTextEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from renforge_logger import get_logger
from locales import tr

logger = get_logger("gui.widgets.batch_summary_panel")


class BatchSummaryPanel(QDockWidget):
    """
    Dock widget showing the last batch operation summary.
    
    Displays: status, total, success, failed, fallback, elapsed_time
    Provides: Copy Summary button, Undo Last Batch button
    """
    
    undo_requested = pyqtSignal()  # Emitted when Undo button clicked
    
    def __init__(self, parent=None):
        super().__init__("Last Batch Summary", parent)
        self.setObjectName("BatchSummaryPanel")
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | 
                            Qt.DockWidgetArea.RightDockWidgetArea)
        
        # Main widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Status line
        self.status_label = QLabel("No batch operation yet")
        self.status_label.setFont(QFont("", -1, QFont.Weight.Bold))
        layout.addWidget(self.status_label)
        
        # Stats frame
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(6, 6, 6, 6)
        stats_layout.setSpacing(2)
        
        self.total_label = QLabel("Total: -")
        self.success_label = QLabel("Success: -")
        self.failed_label = QLabel("Failed: -")
        self.fallback_label = QLabel("Fallback: -")
        self.elapsed_label = QLabel("Elapsed: -")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.success_label)
        stats_layout.addWidget(self.failed_label)
        stats_layout.addWidget(self.fallback_label)
        stats_layout.addWidget(self.elapsed_label)
        
        layout.addWidget(stats_frame)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 Copy Summary")
        self.copy_btn.clicked.connect(self._copy_summary)
        self.copy_btn.setEnabled(False)
        btn_layout.addWidget(self.copy_btn)
        
        self.undo_btn = QPushButton("↩️ Undo Last Batch")
        self.undo_btn.clicked.connect(self._request_undo)
        self.undo_btn.setEnabled(False)
        btn_layout.addWidget(self.undo_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        self.setWidget(container)
        
        # Store last results for copy
        self._last_results = None
        self._summary_text = ""
    
    def update_summary(self, results: dict):
        """
        Update the panel with batch results.
        
        Args:
            results: Dict with batch results
        """
        self._last_results = results
        
        canceled = results.get('canceled', False)
        total = results.get('total', 0)
        success = results.get('success', results.get('success_count', 0))
        failed = results.get('failed', len(results.get('errors', [])))
        fallback = results.get('fallback', 0)
        elapsed = results.get('elapsed', results.get('elapsed_time', 0))
        
        # Update status
        if canceled:
            self.status_label.setText("⚠️ CANCELED")
            self.status_label.setStyleSheet("color: #FFA500;")  # Orange
        elif failed > 0:
            self.status_label.setText("⚠️ DONE with errors")
            self.status_label.setStyleSheet("color: #FF6B6B;")  # Red
        else:
            self.status_label.setText("✅ DONE")
            self.status_label.setStyleSheet("color: #4CAF50;")  # Green
        
        # Update stats
        self.total_label.setText(f"Total: {total}")
        self.success_label.setText(f"Success: {success}")
        self.failed_label.setText(f"Failed: {failed}")
        self.fallback_label.setText(f"Fallback: {fallback}")
        
        if isinstance(elapsed, (int, float)):
            self.elapsed_label.setText(f"Elapsed: {elapsed:.1f}s")
        else:
            self.elapsed_label.setText(f"Elapsed: {elapsed}")
        
        # Build summary text
        status_str = "CANCELED" if canceled else "DONE"
        self._summary_text = (
            f"Batch Translation {status_str}\n"
            f"Total: {total}\n"
            f"Success: {success}\n"
            f"Failed: {failed}\n"
            f"Fallback: {fallback}\n"
            f"Elapsed: {elapsed:.1f}s" if isinstance(elapsed, (int, float)) else f"Elapsed: {elapsed}"
        )
        
        self.copy_btn.setEnabled(True)
        
        logger.debug(f"[BatchSummaryPanel] Updated with results: {status_str}")
    
    def set_undo_available(self, available: bool):
        """Enable/disable the Undo button."""
        self.undo_btn.setEnabled(available)
    
    def _copy_summary(self):
        """Copy summary text to clipboard."""
        if self._summary_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._summary_text)
            logger.debug("[BatchSummaryPanel] Summary copied to clipboard")
    
    def _request_undo(self):
        """Emit undo request signal."""
        self.undo_requested.emit()
    
    def clear(self):
        """Clear the panel."""
        self.status_label.setText("No batch operation yet")
        self.status_label.setStyleSheet("")
        self.total_label.setText("Total: -")
        self.success_label.setText("Success: -")
        self.failed_label.setText("Failed: -")
        self.fallback_label.setText("Fallback: -")
        self.elapsed_label.setText("Elapsed: -")
        self.copy_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self._last_results = None
        self._summary_text = ""
