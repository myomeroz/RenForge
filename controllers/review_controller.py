# -*- coding: utf-8 -*-
"""
RenForge Review Controller (v2)

Manages the logic for the Review Page:
- O(1) statistics via model.stats_updated signal
- Keyboard-driven QA workflow (approve, revert, flag, next issue)
- Selection movement after approve

v2 Changes:
- Removed O(N) scan from refresh_stats
- Connected to model.stats_updated signal
- Added revert_to_saved, toggle_flag, next_problem methods
- Added approve_and_next with selection movement
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Slot, QTimer, Qt
from PySide6.QtGui import QShortcut, QKeySequence

from renforge_logger import get_logger
from gui.models.row_data import RowStatus, RowData

logger = get_logger("controllers.review")


class ReviewController(QObject):
    """
    Controller for Review Page.
    
    Key Responsibilities:
    - Display global stats from model (O(1) via signal)
    - Handle approval/revert/flag actions using row_id (not index)
    - Keyboard shortcuts for QA workflow
    - Selection movement after approve (next row in proxy)
    """
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.review_page = main_window.review_page
        
        # Track current model for signal management
        self._current_model = None
        
        self._connect_signals()
        self._setup_shortcuts()
        
        logger.debug("ReviewController v2 initialized")
    
    # =========================================================================
    # SIGNAL CONNECTIONS
    # =========================================================================
    
    def _connect_signals(self):
        """Connect to ReviewPage and MainWindow signals."""
        # ReviewPage action signals
        self.review_page.approve_requested.connect(self._on_approve)
        self.review_page.undo_requested.connect(self._on_revert_to_saved)
        self.review_page.next_issue_requested.connect(self._on_next_issue)
        
        # File change signal
        self.main_window.active_file_changed.connect(self._on_file_changed)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for Review page."""
        # Enter = Approve & Next
        shortcut_approve_next = QShortcut(
            QKeySequence(Qt.Key.Key_Return), self.review_page
        )
        shortcut_approve_next.activated.connect(self.approve_and_next)
        
        # Ctrl+Enter = Approve only (stay)
        shortcut_approve = QShortcut(
            QKeySequence("Ctrl+Return"), self.review_page
        )
        shortcut_approve.activated.connect(self.approve_current)
        
        # Ctrl+Z = Revert to saved
        shortcut_revert = QShortcut(
            QKeySequence("Ctrl+Z"), self.review_page
        )
        shortcut_revert.activated.connect(self._on_revert_to_saved)
        
        # F = Toggle flag
        shortcut_flag = QShortcut(
            QKeySequence(Qt.Key.Key_F), self.review_page
        )
        shortcut_flag.activated.connect(self.toggle_flag)
        
        # F8 = Next problem
        shortcut_next_problem = QShortcut(
            QKeySequence(Qt.Key.Key_F8), self.review_page
        )
        shortcut_next_problem.activated.connect(self._on_next_issue)
    
    # =========================================================================
    # MODEL ACCESS
    # =========================================================================
    
    def _get_current_model(self):
        """Get current TranslationTableModel from main window."""
        return getattr(self.main_window, '_current_table_model', None)
    
    def _get_proxy_model(self):
        """Get current proxy model from review page table."""
        table = self.review_page.table_widget
        if table and hasattr(table, 'model'):
            model = table.model()
            # If it's a proxy, return it; otherwise None
            if hasattr(model, 'sourceModel'):
                return model
        return None
    
    def _connect_to_model(self, model):
        """Connect to model's stats_updated signal."""
        # Disconnect from old model
        if self._current_model is not None:
            try:
                self._current_model.stats_updated.disconnect(self._on_stats_updated)
            except:
                pass
        
        # Connect to new model
        self._current_model = model
        if model is not None:
            model.stats_updated.connect(self._on_stats_updated)
            # Initial stats update
            self._on_stats_updated(model.get_global_stats())
    
    # =========================================================================
    # STATS (O(1) via signal)
    # =========================================================================
    
    @Slot(dict)
    def _on_stats_updated(self, stats: dict):
        """
        Handle stats update from model. O(1) - no scanning.
        
        stats = {
            "total": N,
            "untranslated": X,
            "translated": Y,
            "modified": Z,
            "approved": A,
            "error": E,
            "flagged": F,
        }
        """
        # Calculate problem count
        problems = (
            stats.get("untranslated", 0) +
            stats.get("error", 0) +
            stats.get("modified", 0) +
            stats.get("flagged", 0)
        )
        
        # Update Review page UI
        self.review_page.update_stats(
            approved=stats.get("approved", 0),
            issues=problems
        )
        
        # Update global counters if review page supports it
        if hasattr(self.review_page, 'update_global_counters'):
            self.review_page.update_global_counters(stats)
        
        # Check for empty state
        proxy = self._get_proxy_model()
        if proxy is not None and proxy.rowCount() == 0:
            self.review_page.show_empty_state(
                "No issues ✅",
                "All rows are approved or translated without errors."
            )
    
    # =========================================================================
    # APPROVAL ACTIONS
    # =========================================================================
    
    def approve_and_next(self):
        """Approve selected rows and move to next row in proxy view."""
        table = self.review_page.table_widget
        if not table:
            return
        
        selected_ids = table.get_selected_row_ids()
        if not selected_ids:
            logger.debug("No rows selected for approval")
            return
        
        model = self._get_current_model()
        if not model:
            return
        
        # Remember current proxy row before approve
        current_proxy_row = table.currentIndex().row()
        
        # Approve all selected
        for row_id in selected_ids:
            model.update_row_by_id(row_id, {
                "status": RowStatus.APPROVED,
                "approved_at": datetime.now()
            })
        
        logger.info(f"Approved {len(selected_ids)} rows")
        
        # After filter invalidation, select next row
        QTimer.singleShot(10, lambda: self._select_next_after_approve(current_proxy_row))
    
    def approve_current(self):
        """Approve selected rows, stay at current position."""
        table = self.review_page.table_widget
        if not table:
            return
        
        selected_ids = table.get_selected_row_ids()
        if not selected_ids:
            return
        
        model = self._get_current_model()
        if not model:
            return
        
        for row_id in selected_ids:
            model.update_row_by_id(row_id, {
                "status": RowStatus.APPROVED,
                "approved_at": datetime.now()
            })
        
        logger.info(f"Approved {len(selected_ids)} rows (stay)")
    
    def _select_next_after_approve(self, previous_proxy_row: int):
        """Select next visible row after approved row(s) disappear."""
        proxy = self._get_proxy_model()
        table = self.review_page.table_widget
        
        if proxy is None or table is None:
            return
        
        new_row_count = proxy.rowCount()
        
        if new_row_count == 0:
            # All problems resolved!
            table.clearSelection()
            self.review_page.show_empty_state(
                "No issues ✅",
                "All rows are approved or translated without errors."
            )
            return
        
        # Select row at same position (or last row if we were at end)
        next_row = min(previous_proxy_row, new_row_count - 1)
        next_index = proxy.index(next_row, 0)
        table.setCurrentIndex(next_index)
        table.selectRow(next_row)
    
    @Slot()
    def _on_approve(self):
        """Handle approve button click."""
        self.approve_current()
    
    # =========================================================================
    # REVERT ACTIONS
    # =========================================================================
    
    @Slot()
    def _on_revert_to_saved(self):
        """Revert selected rows to last saved state."""
        table = self.review_page.table_widget
        if not table:
            return
        
        selected_ids = table.get_selected_row_ids()
        if not selected_ids:
            return
        
        model = self._get_current_model()
        if not model:
            return
        
        for row_id in selected_ids:
            idx = model.get_index_by_id(row_id)
            if idx is not None:
                row = model._rows[idx]
                old_status = row.status
                old_flagged = row.is_flagged
                
                # Use RowData's revert method
                row.revert_to_saved()
                
                # Update counters
                model._update_stats_delta(old_status, row.status, old_flagged, row.is_flagged)
                
                # Emit dataChanged
                from gui.models.translation_table_model import TableColumn
                top_left = model.index(idx, 0)
                bottom_right = model.index(idx, TableColumn.COUNT - 1)
                model.dataChanged.emit(top_left, bottom_right)
        
        logger.info(f"Reverted {len(selected_ids)} rows to saved state")
    
    # =========================================================================
    # FLAG ACTIONS
    # =========================================================================
    
    def toggle_flag(self):
        """Toggle flag on selected rows."""
        table = self.review_page.table_widget
        if not table:
            return
        
        selected_ids = table.get_selected_row_ids()
        if not selected_ids:
            return
        
        model = self._get_current_model()
        if not model:
            return
        
        for row_id in selected_ids:
            idx = model.get_index_by_id(row_id)
            if idx is not None:
                row = model._rows[idx]
                model.update_row_by_id(row_id, {
                    "is_flagged": not row.is_flagged
                })
        
        logger.info(f"Toggled flag on {len(selected_ids)} rows")
    
    # =========================================================================
    # NAVIGATION
    # =========================================================================
    
    @Slot()
    def _on_next_issue(self):
        """Navigate to next problem row."""
        proxy = self._get_proxy_model()
        table = self.review_page.table_widget
        
        if proxy is None or table is None:
            return
        
        if proxy.rowCount() == 0:
            return
        
        # Get current row
        current_idx = table.currentIndex()
        current_row = current_idx.row() if current_idx.isValid() else -1
        
        # Move to next row (wrap around)
        next_row = (current_row + 1) % proxy.rowCount()
        next_index = proxy.index(next_row, 0)
        table.setCurrentIndex(next_index)
        table.selectRow(next_row)
    
    # =========================================================================
    # FILE CHANGE HANDLING
    # =========================================================================
    
    @Slot(str)
    def _on_file_changed(self, file_path: str):
        """Handle file switch - connect to new model."""
        model = self._get_current_model()
        self._connect_to_model(model)
        
        # Check if we should show empty state
        if model is None:
            self.review_page.update_stats(0, 0)
