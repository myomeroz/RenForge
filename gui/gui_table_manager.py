import sys
import os
import re 

from renforge_logger import get_logger
logger = get_logger("gui.table_manager")

try:

    from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                                 QAbstractItemView, QMessageBox, QApplication)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QBrush 
except ImportError:
    logger.critical("PySide6 is required for table management but not found.")
    sys.exit(1)

import renforge_config as config
import renforge_core as core 
import parser.core as parser
from models.parsed_file import ParsedFile, ParsedItem
from renforge_enums import ItemType
from locales import tr

def create_table_widget(main_window):

    table = QTableWidget()
    table.setColumnCount(8)  # Added Status column
    table.setHorizontalHeaderLabels(['#', 'Type', 'Tag', 'Original', 'Editable', 'Mod.', 'BP', 'Status']) 
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.verticalHeader().setVisible(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)

    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) 
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) 
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) 
    header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) 
    header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) 
    header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) 
    header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Status column 

    table.itemSelectionChanged.connect(lambda: handle_item_selection_changed(main_window))
    table.currentItemChanged.connect(lambda current, previous: handle_current_item_changed(main_window, current, previous))
    table.itemChanged.connect(lambda item: handle_item_changed(main_window, item))

    return table

def populate_table(table_widget: QTableWidget, items_list: list, mode: str):

    table_widget.clearContents()
    table_widget.setRowCount(len(items_list))

    for i, item in enumerate(items_list):
        # item is ParsedItem
        line_idx = item.line_index # Unified line index
        line_num_str = str(line_idx + 1) if line_idx is not None else "-"
        item_type = item.type
        variable_name = item.variable_name 

        display_tag = ""
        if item_type == ItemType.VARIABLE:
            display_tag = variable_name or '?' 
            item_type_display = "var" 
        elif item_type == 'dialogue':
            if mode == 'translate':
                display_tag = item.character_trans or item.character_tag or ''
            else: 
                display_tag = item.character_tag or ''
            item_type_display = item_type 
        else: 
            display_tag = item.character_tag or ''
            item_type_display = item_type 

        original_text = item.original_text or ''
        edited_text = item.current_text or ''

        modified_status = "*" if item.is_modified_session else ""
        breakpoint_status = "B" if item.has_breakpoint else ""

        breakpoint_status = "B" if item.has_breakpoint else ""

        item_line = QTableWidgetItem(line_num_str)
        item_line.setData(Qt.ItemDataRole.UserRole, i) # Store source index for stability
        item_type_cell = QTableWidgetItem(item_type_display) 
        item_tag_cell = QTableWidgetItem(display_tag)        
        item_original = QTableWidgetItem(original_text)
        item_edited = QTableWidgetItem(edited_text)
        item_modified = QTableWidgetItem(modified_status)
        item_breakpoint = QTableWidgetItem(breakpoint_status)
        
        # Batch marker column
        batch_marker = getattr(item, 'batch_marker', None) or ""
        batch_tooltip = getattr(item, 'batch_tooltip', None) or ""
        if batch_marker == "AI_FAIL":
            marker_display = "🔴"
        elif batch_marker == "AI_WARN":
            marker_display = "⚠️"
        elif batch_marker == "OK":
            marker_display = "✅"
        else:
            marker_display = ""
        item_status = QTableWidgetItem(marker_display)
        if batch_tooltip:
            item_status.setToolTip(batch_tooltip)

        flags_uneditable = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        flags_editable = flags_uneditable | Qt.ItemFlag.ItemIsEditable
        item_line.setFlags(flags_uneditable)
        item_type_cell.setFlags(flags_uneditable)
        item_tag_cell.setFlags(flags_uneditable)
        item_original.setFlags(flags_uneditable)
        item_edited.setFlags(flags_editable)
        item_modified.setFlags(flags_uneditable)
        item_breakpoint.setFlags(flags_uneditable)
        item_status.setFlags(flags_uneditable)

        item_modified.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_breakpoint.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        tooltip = f"Index: {i}, Line: {line_num_str}, Type: {item_type}" 
        if display_tag: tooltip += f", Name: {display_tag}" 
        item_line.setToolTip(tooltip)
        item_type_cell.setToolTip(tooltip)
        item_tag_cell.setToolTip(tooltip)
        item_original.setToolTip(f"{tooltip}\nOriginal: {original_text}")
        item_edited.setToolTip(f"{tooltip}\nEdited: {edited_text}")
        item_modified.setToolTip("*: Modified in this session")
        item_breakpoint.setToolTip(f"B: Marker set ({config.BREAKPOINT_MARKER})")

        table_widget.setItem(i, 0, item_line)
        table_widget.setItem(i, 1, item_type_cell) 
        table_widget.setItem(i, 2, item_tag_cell)  
        table_widget.setItem(i, 3, item_original)
        table_widget.setItem(i, 4, item_edited)
        table_widget.setItem(i, 5, item_modified)
        table_widget.setItem(i, 6, item_breakpoint)
        table_widget.setItem(i, 7, item_status)  # New Status column

        update_table_row_style(table_widget, i, item) 

    table_widget.setColumnHidden(3, mode == "direct") 
    header_item = table_widget.horizontalHeaderItem(4) 
    if header_item:
        header_item.setText("Translation" if mode == "translate" else "Text")

def handle_item_selection_changed(main_window):

    sender_table = main_window.sender() 
    current_table = main_window._get_current_table()

    if sender_table != current_table:

        return

    selected_rows = sorted(list(set(index.row() for index in current_table.selectedIndexes())))
    current_stored_index = main_window._get_current_item_index()

    new_index_to_set = -1
    if selected_rows:
        last_selected = selected_rows[-1]
        new_index_to_set = last_selected

    elif not current_table.currentIndex().isValid():
        new_index_to_set = -1

    if new_index_to_set != current_stored_index:
         main_window._set_current_item_index(new_index_to_set) 

    main_window._update_ui_state()

def handle_current_item_changed(main_window, current, previous):

    sender_table = main_window.sender()
    current_table = main_window._get_current_table()

    if sender_table != current_table:

        return

    new_row_index = current.row() if current else -1
    current_stored_index = main_window._get_current_item_index()

    if new_row_index != current_stored_index:
         main_window._set_current_item_index(new_row_index) 
         main_window._update_ui_state() 

def handle_item_changed(main_window, item: QTableWidgetItem):

    sender_table = main_window.sender()
    current_table = main_window._get_current_table()

    if main_window._block_item_changed_signal or sender_table != current_table:
        return

    row = item.row()
    col = item.column()
    editable_col_index = 4 

    if col != editable_col_index:
        return

    current_file_data = main_window._get_current_file_data()
    if not current_file_data:
        logger.error("handle_item_changed - No current file data found!")
        return

    current_items = current_file_data.items
    current_mode = current_file_data.mode
    current_file_lines = current_file_data.lines 

    if not current_items or not current_mode or not (0 <= row < len(current_items)):
        logger.warning(f"Invalid state or index in handle_item_changed (row: {row})")
        return

    item_data = current_items[row]
    new_text = item.text()

    # text_key logic removed
    current_text_in_data = item_data.current_text

    if item_data.initial_text is None:
         item_data.initial_text = current_text_in_data

    if new_text != current_text_in_data:
        
        # Stage 10: Manual Edit Logging
        from core.change_log import get_change_log, ChangeRecord, ChangeSource
        import time
        rec = ChangeRecord(
            timestamp=time.time(),
            file_path=current_file_data.file_path,
            item_index=row, # Note: using row as item_index (assuming strict mapping? populate_table uses i. OK.)
            display_row=item_data.line_index + 1 if item_data.line_index is not None else row + 1,
            before_text=current_text_in_data or "",
            after_text=new_text,
            source=ChangeSource.MANUAL
        )
        get_change_log().add_record(rec)

        item_data.current_text = new_text
        item_data.is_modified_session = True

        update_line = False
        if current_mode == "translate":
            line_idx = item_data.line_index

            parsed_data_for_formatting = item_data.parsed_data
            if line_idx is not None and parsed_data_for_formatting is not None and current_file_lines and 0 <= line_idx < len(current_file_lines):

                new_line = parser.format_line_from_components(item_data, new_text)
                if new_line is not None:
                    current_file_lines[line_idx] = new_line
                    update_line = True

                else:
                    main_window.statusBar().showMessage(f"Error formatting line {line_idx+1} during manual input!", 5000)

            else:
                 logger.warning(f"Could not update line for item {row} in translate mode (missing index or parsed_data).")

        update_table_row_style(sender_table, row, item_data)

        main_window._set_current_tab_modified(True) 

def find_text_in_item(item_data: dict, search_text: str, mode: str, use_regex: bool = False, case_sensitive: bool = False) -> bool:

    if not search_text:
        return False
    # text_key logic removed
    text_to_search_in = item_data.current_text or ''

    if use_regex:
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            match = re.search(search_text, text_to_search_in, flags)
            return match is not None
        except re.error:

            return False
    else:

        if not case_sensitive:
            search_text = search_text.lower()
            text_to_search_in = text_to_search_in.lower()
        return search_text in text_to_search_in

def update_table_row_style(table_widget: QTableWidget, row_index: int, item_data: dict):

    if not table_widget:
        return 
        
    # Support for TranslationTableView (Fluent UI)
    if hasattr(table_widget, 'model') and callable(table_widget.model) and not hasattr(table_widget, 'setItem'):
        model = table_widget.model()
        # Handle proxy model
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
            
        if hasattr(model, 'update_single_row'):
            # Update visual flags in model
            # Note: The model's data() method handles colors based on these flags
            patch = {
                "is_modified": getattr(item_data, 'is_modified_session', False),
                "has_breakpoint": getattr(item_data, 'has_breakpoint', False)
            }
            model.update_single_row(row_index, patch)
        return

    # Legacy QTableWidget logic
    if not (0 <= row_index < table_widget.rowCount()):
        return

    has_breakpoint = item_data.has_breakpoint
    is_modified = item_data.is_modified_session

    mod_item = table_widget.item(row_index, 5) 
    if mod_item: mod_item.setText("*" if is_modified else "")
    bp_item = table_widget.item(row_index, 6) 
    if bp_item: bp_item.setText("B" if has_breakpoint else "")

    default_fg = QColor(config.STYLE_DEFAULTS.get("text_color", "#f0f0f0"))
    modified_fg = QColor(config.STYLE_DEFAULTS.get("modified_text_color", "#ADD8E6")) 
    breakpoint_bg_color = QColor(config.STYLE_DEFAULTS.get("breakpoint_bg_color", "#5e5e3c")) 
    default_bg_even = QColor(config.STYLE_DEFAULTS.get("bg_even_color", "#2b2b2b"))
    default_bg_odd = QColor(config.STYLE_DEFAULTS.get("bg_odd_color", "#3c3f41"))

    bg_color = breakpoint_bg_color if has_breakpoint else (default_bg_even if row_index % 2 == 0 else default_bg_odd)
    bg_brush = QBrush(bg_color)

    for col in range(table_widget.columnCount()):
        table_item = table_widget.item(row_index, col)
        if not table_item: continue

        table_item.setBackground(bg_brush)

        current_fg = modified_fg if is_modified else default_fg
        table_item.setForeground(current_fg)

def update_all_row_styles(table_widget: QTableWidget, items_list: list):

    if not table_widget or not items_list:
        return
    for i, item in enumerate(items_list):
         # Adapter support integrated in update_table_row_style
         # Check bounds for QTableWidget (TranslationTableView doesn't have rowCount method directly exposed usually, but via model)
         if hasattr(table_widget, 'rowCount'):
            if i < table_widget.rowCount(): 
                update_table_row_style(table_widget, i, item)
         elif hasattr(table_widget, 'model') and table_widget.model() and i < table_widget.model().rowCount():
             update_table_row_style(table_widget, i, item)

def update_table_item_text(main_window, table_widget: QTableWidget, item_index: int, column_index: int, new_text: str):

    if not table_widget:
        return
        
    # Support for TranslationTableView (Fluent UI)
    if hasattr(table_widget, 'model') and callable(table_widget.model) and not hasattr(table_widget, 'setItem'):
        model = table_widget.model()
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
            
        if hasattr(model, 'update_single_row'):
            # Only support Translation column (index 4) update via this generic method for now
            if column_index == 4:
                model.update_single_row(item_index, {"translation": new_text})
        return

    # Legacy QTableWidget logic
    if not (0 <= item_index < table_widget.rowCount()):
        return

    table_item = table_widget.item(item_index, column_index)
    if table_item:
        was_blocked = main_window._block_item_changed_signal
        main_window._block_item_changed_signal = True
        try:
            table_item.setText(new_text)
        finally:
            main_window._block_item_changed_signal = was_blocked

def revert_single_item_logic(main_window, item_index: int) -> bool:

    current_file_data = main_window._get_current_file_data()
    if not current_file_data: return False

    current_items = current_file_data.items
    current_file_lines = current_file_data.lines
    current_mode = current_file_data.mode
    table_widget = main_window._get_current_table() 
    
    # ... logic continues ... (unchanged)
    
    if not current_items or not current_mode or not table_widget or not (0 <= item_index < len(current_items)):
        logger.error(f"revert_single_item_logic - Invalid data for index {item_index}")
        return False 
        
    # Skipping unchanged logic block...
    # Re-implenting full function because regex replacement requires full block match typically,
    # OR we can just edit the update calls within it.
    # But for replace_file_content I provided start/end range covering multiple functions.
    # Let me stick to replacing functions related to Update.
    
    item = current_items[item_index]

    if not item.is_modified_session:
        return False

    initial_text = item.initial_text
    if initial_text is None:

         initial_text = item.original_text or ''
         logger.warning(f"No 'initial_text' found for item {item_index}, reverting to 'original_text'.")

    # text_key logic removed
    current_text = item.current_text or ''

    reverted = False
    if current_text != initial_text:

        item.current_text = initial_text

        if current_mode == "translate":
            line_idx = item.line_index

            parsed_data_for_formatting = item.parsed_data
            if line_idx is not None and parsed_data_for_formatting is not None and current_file_lines and 0 <= line_idx < len(current_file_lines):

                new_line = parser.format_line_from_components(item, initial_text)
                if new_line is not None:
                    current_file_lines[line_idx] = new_line
                    reverted = True

                else:
                    main_window.statusBar().showMessage(f"Error formatting line {line_idx+1} on revert", 5000)

                    item.current_text = current_text
                    return False 
            else:

                reverted = True
                logger.warning(f"Could not update line {line_idx} on revert for item {item_index}.")
        else: 
            reverted = True

    if reverted:

        item.is_modified_session = False

        update_table_item_text(main_window, table_widget, item_index, 4, initial_text)

        update_table_row_style(table_widget, item_index, item)
        return True

    return False 

# ... (omitted revert functions) ...

def update_row_batch_marker(table_widget: QTableWidget, row_index: int, 
                            marker: str = None, tooltip: str = None):
    """
    Update the batch marker status column for a specific row.
    """
    if not table_widget:
        return
        
    # Support for TranslationTableView (Fluent UI)
    if hasattr(table_widget, 'model') and callable(table_widget.model) and not hasattr(table_widget, 'setItem'):
        model = table_widget.model()
        if hasattr(model, 'sourceModel'):
            model = model.sourceModel()
            
        if hasattr(model, 'update_single_row'):
            patch = {
                "batch_marker": marker,
                "batch_tooltip": tooltip
            }
            model.update_single_row(row_index, patch)
        return
        
    # Legacy QTableWidget logic
    if not (0 <= row_index < table_widget.rowCount()):
        return
    
    # Determine display emoji
    if marker == "AI_FAIL":
        marker_display = "🔴"
    elif marker == "AI_WARN":
        marker_display = "⚠️"
    elif marker == "OK":
        marker_display = "✅"
    else:
        marker_display = ""
    
    status_item = table_widget.item(row_index, 7)  # Status column
    if status_item:
        status_item.setText(marker_display)
        if tooltip:
            status_item.setToolTip(tooltip)
        else:
            status_item.setToolTip("")


def filter_table_rows(table_widget: QTableWidget, items_list: list, filter_type: str) -> int:
    """
    Filter table rows based on batch marker or modification status.
    
    Args:
        table_widget: The QTableWidget to filter
        items_list: List of ParsedItem objects
        filter_type: "all", "ai_fail", "ai_warn", or "changed"
        
    Returns:
        Number of visible rows after filtering
    """
    if not table_widget or not items_list:
        return 0
    
    visible_count = 0
    
    for i, item in enumerate(items_list):
        if i >= table_widget.rowCount():
            break
        
        should_show = True
        
        if filter_type == "ai_fail":
            batch_marker = getattr(item, 'batch_marker', None)
            should_show = (batch_marker == "AI_FAIL")
        elif filter_type == "ai_warn":
            batch_marker = getattr(item, 'batch_marker', None)
            should_show = (batch_marker == "AI_WARN")
        elif filter_type == "changed":
            should_show = item.is_modified_session
        elif filter_type == "empty":
             # Empty or Untranslated
             current_txt = item.current_text or ""
             original_txt = item.original_text or ""
             should_show = (not current_txt.strip()) or (current_txt == original_txt)
        # else filter_type == "all" -> show all
        
        table_widget.setRowHidden(i, not should_show)
        if should_show:
            visible_count += 1
    
    return visible_count


def clear_filter(table_widget: QTableWidget) -> int:
    """
    Clear filter and show all rows.
    
    Args:
        table_widget: The QTableWidget
        
    Returns:
        Total number of rows
    """
    if not table_widget:
        return 0
    
    row_count = table_widget.rowCount()
    for i in range(row_count):
        table_widget.setRowHidden(i, False)
    
    return row_count
