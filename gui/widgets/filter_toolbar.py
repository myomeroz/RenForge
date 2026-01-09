# -*- coding: utf-8 -*-
"""
RenForge Filter Toolbar

Toolbar widget for filtering table rows by batch markers.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal

from renforge_logger import get_logger
from locales import tr

logger = get_logger("gui.widgets.filter_toolbar")


class FilterToolbar(QWidget):
    """
    Toolbar for filtering table rows by batch marker status.
    
    Filter options:
    - All: Show all rows
    - AI_FAIL: Show only rows with AI_FAIL marker
    - AI_WARN: Show only rows with AI_WARN marker
    - Changed: Show only rows with modified text
    """
    
    filter_changed = pyqtSignal(str)  # Emits filter type when changed
    
    FILTER_ALL = "all"
    FILTER_AI_FAIL = "ai_fail"
    FILTER_AI_WARN = "ai_warn"
    FILTER_CHANGED = "changed"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        
        # Label
        label = QLabel("Filter:")
        layout.addWidget(label)
        
        # Filter combo
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Rows", self.FILTER_ALL)
        self.filter_combo.addItem("🔴 AI_FAIL", self.FILTER_AI_FAIL)
        self.filter_combo.addItem("⚠️ AI_WARN", self.FILTER_AI_WARN)
        self.filter_combo.addItem("✏️ Changed", self.FILTER_CHANGED)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_combo)
        
        # Clear button
        self.clear_btn = QPushButton("Clear Filter")
        self.clear_btn.clicked.connect(self._clear_filter)
        self.clear_btn.setEnabled(False)
        layout.addWidget(self.clear_btn)
        
        # Info label
        self.info_label = QLabel("")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
    
    def _on_filter_changed(self, index: int):
        """Handle filter selection change."""
        filter_type = self.filter_combo.currentData()
        self.clear_btn.setEnabled(filter_type != self.FILTER_ALL)
        self.filter_changed.emit(filter_type)
        logger.debug(f"[FilterToolbar] Filter changed to: {filter_type}")
    
    def _clear_filter(self):
        """Clear filter (set to All)."""
        self.filter_combo.setCurrentIndex(0)
    
    def set_info(self, text: str):
        """Set info label text (e.g., "Showing 5/200 rows")."""
        self.info_label.setText(text)
    
    def get_current_filter(self) -> str:
        """Get the current filter type."""
        return self.filter_combo.currentData()
    
    def reset(self):
        """Reset to default state."""
        self.filter_combo.setCurrentIndex(0)
        self.info_label.setText("")
