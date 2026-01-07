# -*- coding: utf-8 -*-
"""
RenForge Batch Controller
Handles batch translation operations and worker signal handling.
"""

from renforge_logger import get_logger
logger = get_logger("controllers.batch_controller")

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMessageBox

from locales import tr
import renforge_parser as parser
import gui.gui_table_manager as table_manager


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
    def handle_item_updated(self, item_index: int, translated_text: str, updated_item_data_copy: dict):
        """
        Handle batch item update signal from worker.
        
        Args:
            item_index: Index of the item being updated
            translated_text: The translated text
            updated_item_data_copy: Copy of item data from worker
        """
        current_file_data = self.main._get_current_file_data()
        if not current_file_data:
            return
        
        current_items = current_file_data.items
        current_lines = current_file_data.lines
        current_mode = current_file_data.mode
        table_widget = getattr(current_file_data, 'table_widget', None)
        
        if not table_widget or not current_items or not current_lines or not current_mode:
            return
        if not (0 <= item_index < len(current_items)):
            return
        
        # Update item data
        original_item_data = current_items[item_index]
        original_item_data.current_text = translated_text
        original_item_data.is_modified_session = True
        current_file_data.is_modified = True
        
        # Update table display
        table_manager.update_table_item_text(self.main, table_widget, item_index, 4, translated_text)
        table_manager.update_table_row_style(table_widget, item_index, original_item_data)
        
        # Update file lines for 'translate' mode
        update_line_error = False
        if current_mode == 'translate':
            line_index_to_update = getattr(original_item_data, 'line_index', None)
            parsed_data_from_signal = updated_item_data_copy.get('parsed_data')
            
            if line_index_to_update is not None and 0 <= line_index_to_update < len(current_lines):
                if parsed_data_from_signal:
                    new_line = parser.format_line_from_components(updated_item_data_copy, translated_text)
                    if new_line is not None:
                        current_lines[line_index_to_update] = new_line
                    else:
                        update_line_error = True
                        logger.error(f"Failed to format line for file index {line_index_to_update}")
                else:
                    update_line_error = True
                    logger.error(f"Missing 'parsed_data' in data for item {item_index}")
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
        processed = results['processed']
        total = results['total']
        success = results['success']
        errors = results['errors'] + len(self._errors)
        warnings = results['warnings']
        made_changes = results['made_changes']
        canceled = results['canceled']
        
        # Build summary message
        summary_msg = "Batch translation finished.\n\n"
        if canceled:
            summary_msg += "TASK CANCELED BY USER\n\n"
        summary_msg += f"Lines processed: {processed}/{total}\n"
        summary_msg += f"Successful (text updated): {success}\n"
        
        if self._errors:
            errors = len(self._errors)
            summary_msg += f"\nTranslation/Update Errors: {errors}\n"
            summary_msg += "\nError Details (max 10):\n" + "\n".join(self._errors[:10])
            if len(self._errors) > 10:
                summary_msg += "\n..."
        
        if self._warnings:
            warnings = len(self._warnings)
            summary_msg += f"\nWarnings (variables '[...]'): {warnings}\n"
            summary_msg += "\nDetails (max 10):\n" + "\n".join(self._warnings[:10])
            if len(self._warnings) > 10:
                summary_msg += "\n..."
        
        QMessageBox.information(self.main, tr("batch_result_title"), summary_msg)
        
        if made_changes and not canceled:
            self.main._set_current_tab_modified(True)
        
        # Update status bar
        status_message = "Batch translation finished."
        if canceled:
            status_message = "Batch translation canceled."
        elif errors > 0 or warnings > 0:
            status_message += " Completed with errors/warnings."
        
        self.main.statusBar().showMessage(status_message, 5000)
        self.main._update_ui_state()
