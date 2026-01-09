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
    
    @pyqtSlot(int, str, dict)
    def handle_item_updated(self, item_index: int, translated_text: str, updated_item_data_copy: dict = None):
        """
        Handle batch item update signal from worker.
        
        Args:
            item_index: Index of the item being updated
            translated_text: The translated text
            updated_item_data_copy: Optional data dict, may contain 'file_path'
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
        
        # Resolve table widget on-demand via file_table_view
        table_widget = file_table_view.resolve_table_widget(self.main, current_file_data.file_path)
        
        if not table_widget:
            logger.error(f"Batch update failed: No table widget found for {current_file_data.file_path}")
            return

        if not current_items or not current_lines or not current_mode:
            logger.error("Batch update failed: Missing items/lines/mode in file data")
            return
            
        if not (0 <= item_index < len(current_items)):
            logger.error(f"Batch update failed: Index {item_index} out of bounds (len: {len(current_items)})")
            return
        
        # Update item data
        original_item_data = current_items[item_index]
        original_item_data.current_text = translated_text
        original_item_data.is_modified_session = True
        current_file_data.is_modified = True
        
        # Update table display
        try:
             table_manager.update_table_item_text(self.main, table_widget, item_index, 4, translated_text)
             table_manager.update_table_row_style(table_widget, item_index, original_item_data)
        except Exception as e:
             logger.error(f"Batch update table UI failed: {e}")
        
        # Update file lines for 'translate' mode
        update_line_error = False
        if current_mode == 'translate':
            line_index_to_update = getattr(original_item_data, 'line_index', None)
            
            if line_index_to_update is not None and 0 <= line_index_to_update < len(current_lines):
                # Use original_item_data for reconstruction (it contains parsed_data)
                # Parse logic expects ParsedItem or dict with 'parsed_data'
                try:
                    new_line = parser.format_line_from_components(original_item_data, translated_text)
                    if new_line is not None:
                        current_lines[line_index_to_update] = new_line
                    else:
                        update_line_error = True
                        logger.error(f"Failed to format line for file index {line_index_to_update}")
                except Exception as e:
                    update_line_error = True
                    logger.error(f"Error formatting line: {e}")
            else:
                update_line_error = True
                logger.error(f"Invalid line index {line_index_to_update} for item {item_index}")
            
            if update_line_error:
                err_detail = f"- Error updating file line {line_index_to_update+1} for item {item_index+1}"
                self._errors.append(err_detail)
    
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

