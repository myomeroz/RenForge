# -*- coding: utf-8 -*-
"""
RenForge Translation Table View

Custom QTableWidget for displaying translation items with:
- Signal-based interaction (no business logic)
- Styling integration
- Cell editing support
"""

from typing import Optional, List
from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                             QAbstractItemView, QWidget)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont

from renforge_logger import get_logger
from locales import tr

logger = get_logger("views.table")


class TranslationTableView(QTableWidget):
    """
    Custom table widget for displaying translation/editing items.
    
    This is a pure View component - it only displays data and emits signals.
    All business logic should be handled by controllers.
    
    Signals:
        item_selected(int): Emitted when user selects a row (passes row index)
        item_double_clicked(int): Emitted on double-click (passes row index)
        cell_edited(int, int, str): Emitted when cell content is edited (row, col, new_text)
        selection_changed(list): Emitted when selection changes (passes list of row indices)
    """
    
    # Custom signals
    item_selected = pyqtSignal(int)  # row index
    item_double_clicked = pyqtSignal(int)  # row index
    cell_edited = pyqtSignal(int, int, str)  # row, column, new text
    selection_changed_custom = pyqtSignal(list)  # list of selected row indices
    
    # Column indices (for 'translate' mode)
    COL_INDEX = 0
    COL_CHAR = 1
    COL_ORIGINAL = 2
    COL_ARROW = 3
    COL_TRANSLATION = 4
    COL_TYPE = 5
    
    def __init__(self, parent: Optional[QWidget] = None, mode: str = "translate"):
        """
        Initialize the table view.
        
        Args:
            parent: Parent widget
            mode: 'translate' or 'direct' - determines column layout
        """
        super().__init__(parent)
        self._mode = mode
        self._setup_table()
        self._connect_signals()
        
        logger.debug(f"TranslationTableView created (mode={mode})")
    
    def _setup_table(self):
        """Configure table appearance and behavior."""
        if self._mode == "translate":
            self.setColumnCount(6)
            self.setHorizontalHeaderLabels([
                "#", 
                tr("col_char"),
                tr("col_original"),
                "→",
                tr("col_translation"),
                tr("col_type")
            ])
        else:  # direct mode
            self.setColumnCount(5)
            self.setHorizontalHeaderLabels([
                "#",
                tr("col_char"),
                tr("col_text"),
                "",  # Reserved
                tr("col_type")
            ])
        
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Editing
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        
        # Headers
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        
        # Column sizing
        self._configure_column_widths()
        
        # Visual
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
    
    def _configure_column_widths(self):
        """Set up column width behavior."""
        header = self.horizontalHeader()
        
        if self._mode == "translate":
            header.setSectionResizeMode(self.COL_INDEX, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(self.COL_CHAR, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(self.COL_ORIGINAL, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(self.COL_ARROW, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(self.COL_TRANSLATION, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(self.COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
            
            self.setColumnWidth(self.COL_INDEX, 50)
            self.setColumnWidth(self.COL_ARROW, 30)
        else:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            
            self.setColumnWidth(0, 50)
    
    def _connect_signals(self):
        """Connect internal signals to custom signals."""
        self.cellClicked.connect(self._on_cell_clicked)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.cellChanged.connect(self._on_cell_changed)
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _on_cell_clicked(self, row: int, column: int):
        """Handle cell click."""
        self.item_selected.emit(row)
    
    def _on_cell_double_clicked(self, row: int, column: int):
        """Handle double click."""
        self.item_double_clicked.emit(row)
    
    def _on_cell_changed(self, row: int, column: int):
        """Handle cell content change."""
        item = self.item(row, column)
        if item:
            self.cell_edited.emit(row, column, item.text())
    
    def _on_selection_changed(self):
        """Handle selection change."""
        selected_rows = self.get_selected_rows()
        self.selection_changed_custom.emit(selected_rows)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def get_selected_rows(self) -> List[int]:
        """Get list of selected row indices."""
        return list(set(item.row() for item in self.selectedItems()))
    
    def get_selected_row(self) -> int:
        """Get the first selected row, or -1 if none."""
        rows = self.get_selected_rows()
        return rows[0] if rows else -1
    
    def select_row(self, row: int):
        """Select a specific row."""
        if 0 <= row < self.rowCount():
            self.selectRow(row)
            self.scrollToItem(self.item(row, 0))
    
    def set_cell_text(self, row: int, column: int, text: str):
        """Set text in a cell without triggering cellChanged signal."""
        self.blockSignals(True)
        item = self.item(row, column)
        if item:
            item.setText(text)
        else:
            self.setItem(row, column, QTableWidgetItem(text))
        self.blockSignals(False)
    
    def set_row_background(self, row: int, color: QColor):
        """Set background color for entire row."""
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(color)
    
    def set_row_font(self, row: int, font: QFont):
        """Set font for entire row."""
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setFont(font)
    
    def clear_contents_only(self):
        """Clear contents but keep column configuration."""
        self.setRowCount(0)
    
    def add_row(self, data: List[str], editable_columns: Optional[List[int]] = None) -> int:
        """
        Add a new row with data.
        
        Args:
            data: List of cell values
            editable_columns: List of column indices that should be editable
            
        Returns:
            Index of the new row
        """
        row = self.rowCount()
        self.insertRow(row)
        
        for col, text in enumerate(data):
            item = QTableWidgetItem(str(text) if text is not None else "")
            
            # Set editability
            if editable_columns and col in editable_columns:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            self.setItem(row, col, item)
        
        return row
    
    @property
    def mode(self) -> str:
        """Get the current mode."""
        return self._mode
    
    def __repr__(self) -> str:
        return f"TranslationTableView(mode={self._mode}, rows={self.rowCount()})"
