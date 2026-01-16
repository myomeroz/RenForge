# -*- coding: utf-8 -*-
"""
RenForge Translation Table Widget

Shared table component with search and filter functionality.
Used across pages (Files, Translate, Review).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout
)

from qfluentwidgets import (
    SearchLineEdit, SegmentedWidget, BodyLabel
)

from renforge_logger import get_logger

logger = get_logger("gui.widgets.translation_table")


class TranslationTableWidget(QWidget):
    """
    Shared translation table component.
    
    Layout:
    - Top: SearchLineEdit + Filter chips
    - Bottom: QTableView (TranslationTableView)
    
    Signals:
    - selection_changed(dict): Emitted when row selection changes
    - filter_changed(str): Emitted when filter selection changes
    """
    
    selection_changed = Signal(dict)
    filter_changed = Signal(str)
    
    # Filter types - Must match TranslationFilterProxyModel
    # Filter types - Must match TranslationFilterProxyModel
    FILTER_ALL = "all"
    FILTER_UNTRANSLATED = "untranslated"
    FILTER_TRANSLATED = "translated" # New
    FILTER_MODIFIED = "modified"
    FILTER_APPROVED = "approved"
    FILTER_ERROR = "error"
    FILTER_FLAGGED = "flagged" # New
    FILTER_PROBLEMS = "problems"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_filter = self.FILTER_ALL
        self._flash_overlay = None # For row highlight
        self._setup_ui()
        
        logger.debug("TranslationTableWidget initialized")
    
    def _setup_ui(self):
        """Setup the table widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Top bar: Search + Filters
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        
        # Search
        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("Ara...")
        self.search_edit.setMinimumWidth(200)
        self.search_edit.setMaximumWidth(320)
        self.search_edit.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_edit)
        
        # Filter chips
        self.filter_segment = SegmentedWidget()
        self.filter_segment.addItem(self.FILTER_ALL, "Tümü")
        self.filter_segment.addItem(self.FILTER_UNTRANSLATED, "Sıra Bekleyen") # ○
        self.filter_segment.addItem(self.FILTER_TRANSLATED, "Çevrilen") # ✓
        self.filter_segment.addItem(self.FILTER_MODIFIED, "Düzenlenen") # ★
        self.filter_segment.addItem(self.FILTER_APPROVED, "Onaylanan") # ✔
        self.filter_segment.addItem(self.FILTER_ERROR, "Hatalı") # ⚠
        self.filter_segment.addItem(self.FILTER_FLAGGED, "İşaretli") # 🚩
        self.filter_segment.addItem(self.FILTER_PROBLEMS, "Sorunlu") # QA
        
        self.filter_segment.setCurrentItem(self.FILTER_ALL)
        self.filter_segment.currentItemChanged.connect(self._on_filter_segment_changed)
        top_bar.addWidget(self.filter_segment)
        
        top_bar.addStretch()
        
        # Row count label
        self.row_count_label = BodyLabel("0 satır")
        top_bar.addWidget(self.row_count_label)
        
        layout.addLayout(top_bar)
        
        # Table view
        self._create_table_view()
        layout.addWidget(self.table_view)
    
    def _create_table_view(self):
        """Create the table view."""
        # Import existing TranslationTableView
        from gui.views.translation_table_view import TranslationTableView
        
        self.table_view = TranslationTableView(self)
        self.table_view.rows_selected.connect(self._on_rows_selected)
    
    def _on_rows_selected(self, row_ids: list):
        """Handle row selection from table view."""
        if not row_ids:
            return
        
        # Helper to get source model data directly using row ID
        # This avoids depending on proxy index mapping which can be complex here
        # But we need the row data to update Inspector
        
        # Note: row_ids are strings now (RowData.id)
        
        model = self.table_view.model()
        # Find the model (could be proxy)
        
        # For the inspector, we need the first selected item's full status
        # We can emit the ID and let the controller/inspector fetch the RowData?
        # Or we can build a dict like before.
        
        # Assuming single selection for detailed inspector, multi for batch actions
        first_id = row_ids[0]
        
        # We need to get RowData object.
        # Check if model assumes string IDs
        
        # Emit the first ID as selected
        # The Inspector panel should ideally request data by ID from the central controller or cache
        # But for now we stick to emitting a dict payload to match previous architecture
        # We need to find the RowData for this ID.
        
        from gui.models.translation_table_model import TranslationTableModel
        
        source_model = None
        if hasattr(model, 'sourceModel'):
             source_model = model.sourceModel()
        elif isinstance(model, TranslationTableModel):
             source_model = model
             
        row_data_payload = {}
        
        if source_model and hasattr(source_model, 'get_row_by_id'):
            # This is O(1) in TranslationTableModel
            row_obj = source_model.get_row_by_id(first_id)
            if row_obj:
                 row_data_payload = {
                    'row_id': row_obj.id,
                    'line_num': str(row_obj.id),  # Inspector expects line_num
                    'type': row_obj.row_type,
                    'item_type': row_obj.row_type,  # Inspector expects item_type
                    'tag': row_obj.tag,
                    'original': row_obj.original_text,
                    'translation': row_obj.editable_text,
                    'status': row_obj.status.value,
                    'is_modified': row_obj.status.value == 'modified',
                    'batch_marker': row_obj.status.value  # approximation
                 }
        
        self.selection_changed.emit(row_data_payload)
    
    def _on_search_changed(self, text: str):
        """Handle search text change."""
        model = self.table_view.model()
        # Check if model is proxy (import locally to avoid cycle if needed, or check method presence)
        if hasattr(model, 'set_search_text'):
            model.set_search_text(text)
            
        logger.debug(f"Search text: {text}")
    
    def _on_filter_segment_changed(self, key: str):
        """Handle filter selection change."""
        self._current_filter = key
        
        model = self.table_view.model()
        if hasattr(model, 'set_status_filter'):
            model.set_status_filter(key)
            
        self.filter_changed.emit(key)
        logger.debug(f"Filter changed: {key}")
    
    def _on_selection_changed(self, row_data: dict):
        """Handle table selection change."""
        self.selection_changed.emit(row_data)
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def set_model(self, model):
        """Set the data model for the table view."""
        self.table_view.setModel(model)
        self._update_row_count()
        
    def select_line(self, line_num: int):
        """
        Select row corresponding to file line number (using ID).
        Handles mapping from source model to proxy model if applicable.
        """
        model = self.table_view.model()
        if not model:
            return
            
        row_id = str(line_num)
        
        # Determine strict or proxy
        source_model = model
        is_proxy = False
        
        if hasattr(model, 'sourceModel'):
             source_model = model.sourceModel()
             is_proxy = True
             
        # Find source index
        if hasattr(source_model, 'get_index_by_id'):
            source_row = source_model.get_index_by_id(row_id)
            if source_row is not None:
                source_idx = source_model.index(source_row, 0)
                
                final_idx = source_idx
                if is_proxy:
                    final_idx = model.mapFromSource(source_idx)
                    
                if final_idx.isValid():
                    self.table_view.selectRow(final_idx.row())
                    self.table_view.scrollTo(final_idx)
                    logger.debug(f"Selected line {line_num} (row {final_idx.row()})")
                else:
                    logger.warning(f"Row {line_num} found but filtered out or invalid")
            else:
                logger.warning(f"Line {line_num} not found in model")

    def select_row_by_index(self, row_index: int):
        """
        Select row by internal 0-based row index (from TableModel).
        Handles mapping if proxy is active.
        """
        model = self.table_view.model()
        if not model:
            return
            
        # Determine strict or proxy
        source_model = model
        is_proxy = False
        
        if hasattr(model, 'sourceModel'):
             source_model = model.sourceModel()
             is_proxy = True
             
        # Create source index (0,0)
        source_idx = source_model.index(row_index, 0)
        
        if not source_idx.isValid():
            logger.warning(f"Row index {row_index} invalid in source model")
            return
            
        final_idx = source_idx
        if is_proxy:
            final_idx = model.mapFromSource(source_idx)
            
        if final_idx.isValid():
            self.table_view.selectRow(final_idx.row())
            self.table_view.scrollTo(final_idx)
            logger.debug(f"Selected row index {row_index} (view row {final_idx.row()})")
            
            # Flash highlight
            self._flash_row(final_idx)
        else:
            logger.warning(f"Row index {row_index} filtered out or hidden")
            
    def _flash_row(self, index):
        """Flash a red highlight on the row."""
        from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        
        # Remove existing overlay
        if self._flash_overlay:
            try:
                self._flash_overlay.deleteLater()
            except RuntimeError:
                pass # Already deleted
            self._flash_overlay = None
            
        # Get rect in viewport
        rect = self.table_view.visualRect(index)
        if not rect.isValid():
            return
            
        # Create overlay
        self._flash_overlay = QFrame(self.table_view.viewport())
        self._flash_overlay.setStyleSheet("background-color: rgba(196, 43, 28, 0.3); border: 1px solid #c42b1c; border-radius: 4px;")
        self._flash_overlay.setGeometry(rect)
        self._flash_overlay.show()
        
        # Fade out animation
        self.fade_eff = QGraphicsOpacityEffect(self._flash_overlay)
        self._flash_overlay.setGraphicsEffect(self.fade_eff)
        
        self.anim = QPropertyAnimation(self.fade_eff, b"opacity")
        self.anim.setDuration(1500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.anim.finished.connect(self._flash_overlay.deleteLater)
        self.anim.start()
    def set_proxy_model(self, proxy_model):
        """Set the proxy model for filtering."""
        self.table_view.setModel(proxy_model)
        self._update_row_count()
    
    def get_selected_row_ids(self) -> list:
        """Get selected row IDs."""
        return self.table_view.get_selected_row_ids()
    
    def get_current_filter(self) -> str:
        """Get current filter type."""
        return self._current_filter
    
    def clear_search(self):
        """Clear search text."""
        self.search_edit.clear()
    
    def clear_filter(self):
        """Reset filter to 'all'."""
        self.filter_segment.setCurrentItem("all")
        self._current_filter = self.FILTER_ALL
    
    def set_filter(self, filter_key: str):
        """
        Programmatically set the filter.
        
        Args:
            filter_key: One of the FILTER_* constants
        """
        if filter_key != self._current_filter:
            self.filter_segment.setCurrentItem(filter_key)
            # The signal handler _on_filter_segment_changed will handle the rest
            
    def scroll_to_top(self):
        """Scroll the table view to the top."""
        if self.table_view:
            self.table_view.scrollToTop()
    
    def update_row_count(self, count: int):
        """Update the row count label."""
        self.row_count_label.setText(f"{count} satır")
    
    def _update_row_count(self):
        """Update row count from model."""
        model = self.table_view.model()
        if model:
            count = model.rowCount()
            self.row_count_label.setText(f"{count} satır")
    
    # =========================================================================
    # LEGACY API DELEGATION - For compatibility with gui_action_handler
    # =========================================================================
    
    def currentIndex(self):
        """Get current index (delegate to table_view)."""
        return self.table_view.currentIndex()
    
    def selectedIndexes(self):
        """Get selected indexes (delegate to table_view)."""
        return self.table_view.selectedIndexes()
    
    def isSortingEnabled(self):
        """Check if sorting is enabled (delegate to table_view)."""
        return self.table_view.isSortingEnabled()
    
    def setSortingEnabled(self, enabled: bool):
        """Set sorting enabled (delegate to table_view)."""
        self.table_view.setSortingEnabled(enabled)
    
    def selectRow(self, row: int):
        """Select a row (delegate to table_view)."""
        self.table_view.selectRow(row)
    
    def rowCount(self) -> int:
        """Get row count from model."""
        model = self.table_view.model()
        return model.rowCount() if model else 0
    
    def item(self, row: int, col: int):
        """Get item at position (stub for legacy compatibility)."""
        # QTableView doesn't have items, return None
        return None
    
    def scrollToItem(self, item, hint=None):
        """Scroll to item (stub for legacy compatibility)."""
        # For QTableView, we would use scrollTo with QModelIndex
        pass
    
    def model(self):
        """Get the model (delegate to table_view)."""
        return self.table_view.model()

