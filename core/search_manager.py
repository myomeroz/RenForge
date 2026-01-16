
import re
from typing import Optional, Tuple, List, Dict, Any
from PySide6.QtWidgets import QTableView, QMessageBox
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide6.QtWidgets import QTableView, QMessageBox, QApplication
from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, QObject
from renforge_logger import get_logger
from core.text_utils import mask_renpy_tokens, unmask_renpy_tokens
import locales

logger = get_logger("core.search_manager")

class SearchManager:
    def __init__(self, main_window):
        self.main_window = main_window
        
    def find_next(self, table: QTableView, search_text: str, use_regex: bool) -> bool:
        return self._find_impl(table, search_text, use_regex, forward=True)

    def find_prev(self, table: QTableView, search_text: str, use_regex: bool) -> bool:
        return self._find_impl(table, search_text, use_regex, forward=False)

    def _find_impl(self, table: QTableView, search_text: str, use_regex: bool, forward: bool) -> bool:
        if not search_text:
             self._update_status(locales.tr("search_enter_text_error"))
             return False
            
        model = table.model()
        if not model: return False
            
        row_count = model.rowCount()
        current_idx = table.currentIndex()
        
        start_row = current_idx.row() + (1 if forward else -1)
        if start_row < 0: start_row = row_count - 1
        if start_row >= row_count: start_row = 0
        
        # Search loop
        # Forward: start -> end, then 0 -> start
        # Backward: start -> 0, then end -> start
        
        ranges = []
        if forward:
            ranges.append((start_row, row_count, 1))
            ranges.append((0, start_row, 1))
        else:
            ranges.append((start_row, -1, -1))
            ranges.append((row_count - 1, start_row, -1))
            
        found_idx = None
        for start, end, step in ranges:
            found_idx = self._search_in_range(table, search_text, use_regex, start, end, step)
            if found_idx:
                if start != ranges[0][0]: # Wrapped
                     self.main_window.statusBar().showMessage(locales.tr("find_wrapped"), 2000)
                break
                
        if found_idx:
            table.selectRow(found_idx.row())
            table.scrollTo(found_idx, QTableView.ScrollHint.PositionAtCenter)
            self._update_status(locales.tr("search_found", text=search_text, line=found_idx.row()+1))
            return True
        else:
            self._update_status(locales.tr("search_not_found", text=search_text))
            return False

    def _search_in_range(self, table: QTableView, text: str, regex: bool, start: int, end: int, step: int) -> Optional[QModelIndex]:
        model = table.model()
        target_col = 4 # Translation/Editable column
        
        flags = 0 if regex else re.IGNORECASE
        pattern = None
        if regex:
            try:
                pattern = re.compile(text)
            except re.error as e:
                self._update_status(locales.tr("search_regex_error", error=e))
                return None
        
        for r in range(start, end, step):
            idx = model.index(r, target_col)
            cell_text = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "")
            
            match = False
            if regex and pattern:
                if pattern.search(cell_text): match = True
            elif not regex:
                if text.lower() in cell_text.lower(): match = True
                    
            if match:
                return model.index(r, 0) # Return col 0 for row selection
        return None

    def replace_current(self, table: QTableView, search_text: str, replace_text: str, use_regex: bool, safe_mode: bool = True) -> bool:
        idx = table.currentIndex()
        if not idx.isValid():
            self._update_status(locales.tr("replace_enter_text_error"))
            return False
            
        model = table.model()
        target_col = 4
        edit_idx = model.index(idx.row(), target_col)
        
        original_text = str(model.data(edit_idx, Qt.ItemDataRole.DisplayRole) or "")
        
        # Check match
        match_found = False
        if use_regex:
             try:
                 if re.search(search_text, original_text): match_found = True
             except: pass
        else:
             if search_text.lower() in original_text.lower(): match_found = True
             
        if not match_found:
             self._update_status(locales.tr("replace_no_match"))
             self.find_next(table, search_text, use_regex)
             return False

        # Apply Safe Replace
        new_text, error = self._safe_replace(original_text, search_text, replace_text, use_regex, safe_mode)
        
        if error:
            QMessageBox.warning(self.main_window, locales.tr("error"), locales.tr("replace_skip_reason", reason=error))
            return False
            
        if new_text != original_text:
            idx0 = model.index(idx.row(), 0)
            item_list_idx = model.data(idx0, Qt.ItemDataRole.UserRole) # Source index
            
            if item_list_idx is not None:
                 # Capture Undo
                 current_data = self.main_window._get_current_file_data()
                 if current_data:
                     self.main_window.batch_controller.capture_undo_snapshot(
                         current_data.file_path, [item_list_idx], current_data.items, batch_type="replace_single"
                     )
                 
                 from gui import gui_table_manager as tm
                 tm.update_table_item_text(self.main_window, table, item_list_idx, 4, new_text)
                 
                 # Stage 10: Change Log
                 from core.change_log import get_change_log, ChangeRecord, ChangeSource
                 import time
                 
                 rec = ChangeRecord(
                    timestamp=time.time(),
                    file_path=current_data.file_path,
                    item_index=item_list_idx,
                    display_row=idx.row() + 1,
                    before_text=original_text,
                    after_text=new_text,
                    source=ChangeSource.SEARCH_REPLACE
                 )
                 get_change_log().add_record(rec)
                 
                 self._update_status(locales.tr("replace_success", num=idx.row()+1, old=search_text, new=replace_text))
                 self.find_next(table, search_text, use_regex)
                 return True
            else:
                 logger.error("Could not find Item List Index in UserRole")
                 return False
        return False

    def replace_all(self, table: QTableView, search_text: str, replace_text: str, use_regex: bool, scope: str = "visible", safe_mode: bool = True):
        current_data = self.main_window._get_current_file_data()
        if not current_data: return

        # Identify items to process
        items_to_scan = [] # List of (index, item_data)
        
        if scope == "visible":
            model = table.model()
            row_count = model.rowCount()
            for r in range(row_count):
                idx0 = model.index(r, 0)
                item_idx = model.data(idx0, Qt.ItemDataRole.UserRole)
                if item_idx is not None and item_idx < len(current_data.items):
                    items_to_scan.append((item_idx, current_data.items[item_idx]))
        elif scope == "all":
            for i, item in enumerate(current_data.items):
                items_to_scan.append((i, item))
        
        if not items_to_scan:
            self._update_status(locales.tr("replace_all_no_data"))
            return

        # Pre-scan for confirmation count
        matches_found = 0
        modifications = [] # (index, new_text, item)
        errors = []

        self._update_status(locales.tr("search_match_calculating"))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            for item_idx, item in items_to_scan:
                current_text = item.current_text or ""
                match = False
                if use_regex:
                    try: 
                        if re.search(search_text, current_text): match = True
                    except: pass
                else:
                    if search_text.lower() in current_text.lower(): match = True
                
                if match:
                    matches_found += 1
                    new_text, err = self._safe_replace(current_text, search_text, replace_text, use_regex, safe_mode)
                    if err:
                        errors.append((item_idx, err))
                    if err:
                        errors.append((item_idx, err))
                    elif new_text != current_text:
                        modifications.append((item_idx, new_text, current_text))
        finally:
            QApplication.restoreOverrideCursor()

        if matches_found == 0:
            self._update_status(locales.tr("replace_all_none"))
            return

        confirm_msg = f"{locales.tr('replace_all_confirm_msg', search=search_text, replace=replace_text, search_mode='Regex ' if use_regex else '')}\n\n"
        confirm_msg += f"Changes: {len(modifications)}\nScope: {locales.tr('search_scope_' + scope)}\nSkipped: {len(errors)}"
        
        reply = QMessageBox.question(self.main_window, locales.tr("replace_all_title"), confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            self._update_status(locales.tr("replace_all_canceled"))
            return

        # Snapshot Undo
        row_indices = [x[0] for x in modifications]
        if row_indices:
             self.main_window.batch_controller.capture_undo_snapshot(
                 current_data.file_path, row_indices, current_data.items, batch_type="replace_all"
             )

        # Apply Updates
        from gui import gui_table_manager as tm
        
        # Stage 10: Change Logging
        from core.change_log import get_change_log, ChangeRecord, ChangeSource
        import time
        change_log = get_change_log()
        
        applied_count = 0
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for i, (item_idx, new_text, before_text) in enumerate(modifications):
                 if i % 100 == 0: QApplication.processEvents()
                 
                 items_to_update = current_data.items
                 target_item = items_to_update[item_idx]
                 target_item.current_text = new_text
                 target_item.is_modified_session = True
                 if not target_item.initial_text: target_item.initial_text = before_text 
                 
                 # Record Change
                 rec = ChangeRecord(
                    timestamp=time.time(),
                    file_path=current_data.file_path,
                    item_index=item_idx,
                    display_row=(target_item.line_index or 0) + 1,
                    before_text=before_text,
                    after_text=new_text,
                    source=ChangeSource.SEARCH_REPLACE
                 )
                 change_log.add_record(rec)
                 
                 applied_count += 1
            
            # Repopulate specific rows? Or all?
            # Creating a map of changed indices to "Visible Row" is O(N).
            # full refresh is O(N).
            # Just Repopulate.
            tm.populate_table(table, current_data.items, current_data.mode)
            
            # Re-apply filters if active
            if hasattr(self.main_window, 'filter_toolbar') and hasattr(self.main_window, '_handle_filter_changed'):
                current_filter = self.main_window.filter_toolbar.get_current_filter()
                if current_filter != "all":
                    self.main_window._handle_filter_changed(current_filter)
            
            self.main_window._set_current_tab_modified(True)
            self._update_status(locales.tr("replace_all_count", count=applied_count))
            
            if errors:
                QMessageBox.warning(self.main_window, locales.tr("warning"), f"{len(errors)} items skipped due to safety checks.")
        finally:
            QApplication.restoreOverrideCursor()

    def _safe_replace(self, text: str, search: str, replace: str, regex: bool, safe_mode: bool) -> Tuple[str, Optional[str]]:
        masked, token_map = mask_renpy_tokens(text)
        
        new_masked = masked
        try:
            if regex:
                new_masked = re.sub(search, replace, masked)
            else:
                pattern = re.compile(re.escape(search), re.IGNORECASE)
                new_masked = pattern.sub(replace, masked)
        except re.error as e:
            return text, str(e)
            
        # Validation
        if "⟦" in new_masked or "⟧" in new_masked:
             for key in token_map:
                 if key not in new_masked:
                     return text, "Protected token deleted"
        
        result = unmask_renpy_tokens(new_masked, token_map)
        
        if safe_mode:
             # Strict Check: Token sets must match
             # Original tokens
             orig_tokens = set(re.findall(r'\[.*?\]', text))
             # New tokens
             new_tokens = set(re.findall(r'\[.*?\]', result))
             
             if orig_tokens != new_tokens:
                 # Check if we intended to change them?
                 # "If replacement changes the count/order of tokens, skip."
                 return text, f"Token mismatch (Safe Mode). Orig: {len(orig_tokens)}, New: {len(new_tokens)}"

        return result, None

    def _update_status(self, msg: str):
        self.main_window.statusBar().showMessage(msg, 3000)
        if self.main_window.search_info_label:
             self.main_window.search_info_label.setText(msg)
