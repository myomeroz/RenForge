# -*- coding: utf-8 -*-
"""
RenForge Batch Controller
Handles batch translation operations and worker signal handling.
"""

from renforge_logger import get_logger
logger = get_logger("controllers.batch_controller")

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox, QTableWidget

from locales import tr
import parser.core as parser
import gui.gui_table_manager as table_manager
from gui.views import batch_status_view, file_table_view
from models.batch_undo import get_undo_manager


class BatchController(QObject):
    """
    Controls batch translation operations:
    - Tracking batch results (errors, warnings, counts)
    - Handling worker signals for item updates
    - Displaying batch completion summaries
    """
    
    def __init__(self, main_window):
        """
        Initialize BatchController with reference to the main window.
        
        Args:
            main_window: The RenForgeGUI instance
        """
        super().__init__()
        self.main = main_window
        
        # Batch operation tracking
        self._errors = []
        self._warnings = []
        self._total_processed = 0
        self._success_count = 0
    
    def clear_results(self):
        """Clear all batch result tracking data."""
        self._errors = []
        self._warnings = []
        self._total_processed = 0
        self._success_count = 0
    
    @property
    def errors(self):
        return self._errors
    
    @property
    def warnings(self):
        return self._warnings
    
    def capture_undo_snapshot(self, file_path: str, row_indices: list, items: list, 
                              batch_type: str = "ai"):
        """
        Capture undo snapshot before batch operation starts.
        
        Args:
            file_path: Path of the file being processed
            row_indices: List of row indices that will be affected
            items: List of ParsedItem objects (full file items)
            batch_type: "ai" or "google"
        """
        undo_mgr = get_undo_manager()
        undo_mgr.capture(file_path, row_indices, items, batch_type)
        logger.debug(f"[BatchController] Captured undo snapshot for {len(row_indices)} rows")
    
    @pyqtSlot(int, str, dict)
    def handle_item_updated(self, item_index: int, translated_text: str, updated_item_data_copy: dict = None):
        """
        Handle batch item update signal from worker.
        
        Args:
            item_index: Index of the item being updated (-1 for batch mode)
            translated_text: The translated text (empty for batch mode)
            updated_item_data_copy: Optional data dict, may contain 'file_path' and 'batch_items'
        """
        updated_item_data_copy = updated_item_data_copy or {}
        file_path = updated_item_data_copy.get('file_path')
        
        current_file_data = None
        if file_path and file_path in self.main.file_data:
             current_file_data = self.main.file_data[file_path]
        else:
             current_file_data = self.main._get_current_file_data()
        
        if not current_file_data:
            logger.error(f"Batch update failed: Could not find file data for {file_path or 'current'}")
            return
        
        current_items = current_file_data.items
        current_lines = current_file_data.lines
        current_mode = current_file_data.mode
        
        # Resolve table widget ONCE
        table_widget = file_table_view.resolve_table_widget(self.main, current_file_data.file_path)
        
        if not table_widget:
            logger.error(f"Batch update failed: No table widget found for {current_file_data.file_path}")
            return

        if not current_items or not current_lines or not current_mode:
            logger.error("Batch update failed: Missing items/lines/mode in file data")
            return
        
        # Check for batch mode (item_index = -1 with batch_items in data)
        batch_items = updated_item_data_copy.get('batch_items', [])
        
        if item_index == -1 and batch_items:
            # BATCH MODE: Process entire chunk at once
            self._process_batch_chunk(
                batch_items, current_file_data, current_items, 
                current_lines, current_mode, table_widget
            )
        elif item_index >= 0:
            # SINGLE ITEM MODE (legacy/Google translate)
            self._process_single_item(
                item_index, translated_text, current_file_data,
                current_items, current_lines, current_mode, table_widget
            )
    
    def _process_batch_chunk(self, batch_items, current_file_data, current_items, 
                              current_lines, current_mode, table_widget):
        """Process a batch of translations efficiently."""
        from core.change_log import get_change_log, ChangeRecord, ChangeSource
        import time
        
        # Disable table updates while processing
        table_widget.setUpdatesEnabled(False)
        
        try:
            for batch_item in batch_items:
                idx = batch_item.get('index')
                text = batch_item.get('text')
                
                if idx is None or text is None:
                    continue
                    
                if not (0 <= idx < len(current_items)):
                    logger.warning(f"Batch chunk: Index {idx} out of bounds")
                    continue
                
                item_data = current_items[idx]
                before_text = item_data.current_text or ""
                
                # Update item
                item_data.current_text = text
                item_data.is_modified_session = True
                
                # Record change (lightweight)
                record = ChangeRecord(
                    timestamp=time.time(),
                    file_path=current_file_data.file_path,
                    item_index=idx,
                    display_row=item_data.line_index + 1 if item_data.line_index is not None else idx + 1,
                    before_text=before_text,
                    after_text=text,
                    source=ChangeSource.BATCH,
                    batch_id="batch"
                )
                get_change_log().add_record(record)
                
                # Update table cell directly (no style update)
                try:
                    table_manager.update_table_item_text(self.main, table_widget, idx, 4, text)
                except Exception as e:
                    logger.debug(f"Batch table update error for idx {idx}: {e}")
                
                # Update file lines for 'translate' mode
                if current_mode == 'translate':
                    line_idx = getattr(item_data, 'line_index', None)
                    if line_idx is not None and 0 <= line_idx < len(current_lines):
                        try:
                            new_line = parser.format_line_from_components(item_data, text)
                            if new_line is not None:
                                current_lines[line_idx] = new_line
                        except Exception as e:
                            logger.debug(f"Batch line format error for idx {idx}: {e}")
            
            # Mark file as modified once
            current_file_data.is_modified = True
            
        finally:
            # Re-enable table updates
            table_widget.setUpdatesEnabled(True)
    
    def _process_single_item(self, item_index, translated_text, current_file_data,
                              current_items, current_lines, current_mode, table_widget):
        """Process a single translation item (legacy mode)."""
        from core.change_log import get_change_log, ChangeRecord, ChangeSource
        import time
        
        if not (0 <= item_index < len(current_items)):
            logger.error(f"Batch update failed: Index {item_index} out of bounds (len: {len(current_items)})")
            return
        
        original_item_data = current_items[item_index]
        before_text = original_item_data.current_text or ""
        
        original_item_data.current_text = translated_text
        original_item_data.is_modified_session = True
        current_file_data.is_modified = True
        
        record = ChangeRecord(
            timestamp=time.time(),
            file_path=current_file_data.file_path,
            item_index=item_index,
            display_row=original_item_data.line_index + 1 if original_item_data.line_index is not None else item_index + 1,
            before_text=before_text,
            after_text=translated_text,
            source=ChangeSource.BATCH,
            batch_id="batch"
        )
        get_change_log().add_record(record)
        
        try:
            table_manager.update_table_item_text(self.main, table_widget, item_index, 4, translated_text)
            table_manager.update_table_row_style(table_widget, item_index, original_item_data)
        except Exception as e:
            logger.error(f"Batch update table UI failed: {e}")
        
        if current_mode == 'translate':
            line_index_to_update = getattr(original_item_data, 'line_index', None)
            
            if line_index_to_update is not None and 0 <= line_index_to_update < len(current_lines):
                try:
                    new_line = parser.format_line_from_components(original_item_data, translated_text)
                    if new_line is not None:
                        current_lines[line_index_to_update] = new_line
                    else:
                        self._errors.append(f"- Error updating file line {line_index_to_update+1} for item {item_index+1}")
                except Exception as e:
                    self._errors.append(f"- Error formatting line: {e}")
    
    @pyqtSlot(str)
    def handle_error(self, details: str):
        """
        Handle batch translation error signal.
        
        Args:
            details: Error details string
        """
        self._errors.append(details)
    
    @pyqtSlot(str)
    def handle_warning(self, details: str):
        """
        Handle batch translation warning signal.
        
        Args:
            details: Warning details string
        """
        self._warnings.append(details)
    
    @pyqtSlot()
    def mark_tab_modified(self):
        """Mark the current tab as modified from worker thread."""
        self.main._set_current_tab_modified(True)
    
    @pyqtSlot(dict)
    def handle_finished(self, results: dict):
        """
        Handle batch translation finished signal.
        
        Args:
            results: Dict with keys: processed, total, success, errors, warnings, made_changes, canceled
        """
        # Merge local errors/warnings with results
        result_errors = results.get('errors', [])
        if not isinstance(result_errors, list):
            result_errors = []
        all_errors = list(self._errors) + result_errors
        
        result_warnings = results.get('warnings', [])
        if not isinstance(result_warnings, list):
            result_warnings = []
        all_warnings = list(self._warnings) + result_warnings
        
        # Prepare merged results for formatting
        merged_results = dict(results)
        merged_results['errors'] = all_errors
        merged_results['warnings'] = all_warnings
        
        # CRITICAL: Refresh table UI with updated model data
        # This is done ONCE after all translations complete (not during)
        current_file_data = self.main._get_current_file_data()
        current_table = self.main._get_current_table()
        
        if current_file_data and current_table:
            # Block signals to avoid triggering item_changed during refresh
            was_blocked = self.main._block_item_changed_signal
            self.main._block_item_changed_signal = True
            
            try:
                # Update file lines for all modified items (translate mode)
                if current_file_data.mode == 'translate':
                    current_lines = current_file_data.lines
                    for item in current_file_data.items:
                        if item.is_modified_session:
                            line_idx = getattr(item, 'line_index', None)
                            if line_idx is not None and 0 <= line_idx < len(current_lines):
                                try:
                                    new_line = parser.format_line_from_components(item, item.current_text)
                                    if new_line is not None:
                                        current_lines[line_idx] = new_line
                                except Exception as e:
                                    logger.debug(f"Line format error at {line_idx}: {e}")
                
                # YENİ: Model-View API ile senkronizasyon
                # Eski populate_table KULLANILMIYOR - o UI'ı bloke ederdi!
                from gui.views.translation_table_view import TranslationTableView
                
                if isinstance(current_table, TranslationTableView):
                    # Yeni TranslationTableView: Model güncelle
                    file_table_view.sync_parsed_file_to_view(current_table, current_file_data)
                    logger.info("[BatchController] Table synced via Model-View API")
                else:
                    # Eski QTableWidget fallback (geriye dönük uyumluluk)
                    table_manager.populate_table(
                        current_table, 
                        current_file_data.items, 
                        current_file_data.mode
                    )
                    logger.info("[BatchController] Table refreshed via legacy populate_table")
                
            finally:
                self.main._block_item_changed_signal = was_blocked
            
            # Mark file as modified
            current_file_data.is_modified = True
        
        # Use batch_status_view for formatting
        summary_msg = batch_status_view.format_batch_summary(merged_results)
        status_message = batch_status_view.get_status_message(merged_results)
        
        # Display summary
        QMessageBox.information(self.main, tr("batch_result_title"), summary_msg)
        
        # Mark tab modified if changes were made
        success = results.get('success', results.get('success_count', 0))
        made_changes = results.get('made_changes', success > 0)
        canceled = results.get('canceled', False)
        
        if made_changes and not canceled:
            self.main._set_current_tab_modified(True)
        
        # Update status bar
        self.main.statusBar().showMessage(status_message, 5000)
        self.main._update_ui_state()

