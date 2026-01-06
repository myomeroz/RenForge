import sys
import os
import re 

try:

    from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                                 QAbstractItemView, QMessageBox, QApplication)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QBrush 
except ImportError:
    print("CRITICAL ERROR: PyQt6 is required for table management but not found.")
    sys.exit(1)

import renforge_config as config
import renforge_core as core 
import renforge_parser as parser

def create_table_widget(main_window):

    table = QTableWidget()
    table.setColumnCount(7) 
    table.setHorizontalHeaderLabels(['#', 'Type', 'Tag', 'Original', 'Editable', 'Mod.', 'Marker']) 
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

    table.itemSelectionChanged.connect(lambda: handle_item_selection_changed(main_window))
    table.currentItemChanged.connect(lambda current, previous: handle_current_item_changed(main_window, current, previous))
    table.itemChanged.connect(lambda item: handle_item_changed(main_window, item))

    return table

def populate_table(table_widget: QTableWidget, items_list: list, mode: str):

    table_widget.clearContents()
    table_widget.setRowCount(len(items_list))

    for i, item in enumerate(items_list):

        line_idx = item.get('translated_line_index') if mode == 'translate' else item.get('line_index')
        line_num_str = str(line_idx + 1) if line_idx is not None else "-"
        item_type = item.get('type', '?')
        variable_name = item.get('variable_name') 

        display_tag = ""
        if item_type == parser.CONTEXT_VARIABLE:
            display_tag = variable_name or '?' 
            item_type_display = "var" 
        elif item_type == 'dialogue':
            if mode == 'translate':
                display_tag = item.get('character_trans', item.get('character_tag', ''))
            else: 
                display_tag = item.get('character_tag', '')
            item_type_display = item_type 
        else: 
            display_tag = item.get('character_tag', '') 
            item_type_display = item_type 

        original_text = item.get('original_text', '')
        edited_text = item.get('translated_text', '') if mode == 'translate' else item.get('current_text', '')

        modified_status = "*" if item.get('is_modified_session', False) else ""
        breakpoint_status = "B" if item.get('has_breakpoint', False) else ""

        item_line = QTableWidgetItem(line_num_str)
        item_type_cell = QTableWidgetItem(item_type_display) 
        item_tag_cell = QTableWidgetItem(display_tag)        
        item_original = QTableWidgetItem(original_text)
        item_edited = QTableWidgetItem(edited_text)
        item_modified = QTableWidgetItem(modified_status)
        item_breakpoint = QTableWidgetItem(breakpoint_status)

        flags_uneditable = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        flags_editable = flags_uneditable | Qt.ItemFlag.ItemIsEditable
        item_line.setFlags(flags_uneditable)
        item_type_cell.setFlags(flags_uneditable)
        item_tag_cell.setFlags(flags_uneditable)
        item_original.setFlags(flags_uneditable)
        item_edited.setFlags(flags_editable)
        item_modified.setFlags(flags_uneditable)
        item_breakpoint.setFlags(flags_uneditable)

        item_modified.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_breakpoint.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

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
        print("Error: handle_item_changed - No current file data found!")
        return

    current_items = current_file_data.get('items')
    current_mode = current_file_data.get('mode')
    current_file_lines = current_file_data.get('lines') 

    if not current_items or not current_mode or not (0 <= row < len(current_items)):
        print(f"Warning: Invalid state or index in handle_item_changed (row: {row})")
        return

    item_data = current_items[row]
    new_text = item.text()

    text_key = 'translated_text' if current_mode == "translate" else 'current_text'
    current_text_in_data = item_data.get(text_key, '')

    if 'initial_text' not in item_data:
         item_data['initial_text'] = current_text_in_data

    if new_text != current_text_in_data:

        item_data[text_key] = new_text
        item_data['is_modified_session'] = True

        update_line = False
        if current_mode == "translate":
            line_idx = item_data.get('translated_line_index')

            parsed_data_for_formatting = item_data.get('parsed_data')
            if line_idx is not None and parsed_data_for_formatting is not None and current_file_lines and 0 <= line_idx < len(current_file_lines):

                new_line = parser.format_line_from_components(item_data, new_text)
                if new_line is not None:
                    current_file_lines[line_idx] = new_line
                    update_line = True

                else:
                    main_window.statusBar().showMessage(f"Error formatting line {line_idx+1} during manual input!", 5000)

            else:
                 print(f"Warning: Could not update line for item {row} in translate mode (missing index or parsed_data).")

        update_table_row_style(sender_table, row, item_data)

        main_window._set_current_tab_modified(True) 

def find_text_in_item(item_data: dict, search_text: str, mode: str, use_regex: bool = False, case_sensitive: bool = False) -> bool:

    if not search_text:
        return False
    text_key = 'translated_text' if mode == "translate" else 'current_text'
    text_to_search_in = item_data.get(text_key, '')

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

    if not table_widget or not (0 <= row_index < table_widget.rowCount()):
        return 

    has_breakpoint = item_data.get('has_breakpoint', False)
    is_modified = item_data.get('is_modified_session', False)

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
         if i < table_widget.rowCount(): 
              update_table_row_style(table_widget, i, item)

def update_table_item_text(main_window, table_widget: QTableWidget, item_index: int, column_index: int, new_text: str):

    if not table_widget or not (0 <= item_index < table_widget.rowCount()):
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

    current_items = current_file_data.get('items')
    current_file_lines = current_file_data.get('lines')
    current_mode = current_file_data.get('mode')
    table_widget = current_file_data.get('table_widget') 

    if not current_items or not current_mode or not table_widget or not (0 <= item_index < len(current_items)):
        print(f"Error: revert_single_item_logic - Invalid data for index {item_index}")
        return False 

    item = current_items[item_index]

    if not item.get('is_modified_session', False):
        return False

    initial_text = item.get('initial_text')
    if initial_text is None:

         initial_text = item.get('original_text', '')
         print(f"Warning: No 'initial_text' found for item {item_index}, reverting to 'original_text'.")

    text_key = 'translated_text' if current_mode == "translate" else 'current_text'
    current_text = item.get(text_key, '')

    reverted = False
    if current_text != initial_text:

        item[text_key] = initial_text

        if current_mode == "translate":
            line_idx = item.get('translated_line_index')

            parsed_data_for_formatting = item.get('parsed_data')
            if line_idx is not None and parsed_data_for_formatting is not None and current_file_lines and 0 <= line_idx < len(current_file_lines):

                new_line = parser.format_line_from_components(item, initial_text)
                if new_line is not None:
                    current_file_lines[line_idx] = new_line
                    reverted = True

                else:
                    main_window.statusBar().showMessage(f"Error formatting line {line_idx+1} on revert", 5000)

                    item[text_key] = current_text
                    return False 
            else:

                reverted = True
                print(f"Warning: Could not update line {line_idx} on revert for item {item_index}.")
        else: 
            reverted = True

    if reverted:

        item['is_modified_session'] = False

        update_table_item_text(main_window, table_widget, item_index, 4, initial_text)

        update_table_row_style(table_widget, item_index, item)
        return True

    return False 

def revert_single_item_menu(main_window):

    current_idx = main_window._get_current_item_index()
    if current_idx >= 0:
        if revert_single_item_logic(main_window, current_idx):
            main_window.statusBar().showMessage(f"Changes for item {current_idx + 1} reverted.", 3000)

            current_items = main_window._get_current_translatable_items()
            current_data = main_window._get_current_file_data()
            any_text_modified = any(it.get('is_modified_session', False) for it in current_items) if current_items else False
            breakpoint_modified = current_data.get('breakpoint_modified', False) if current_data else False
            main_window._set_current_tab_modified(any_text_modified or breakpoint_modified)
        else:
            main_window.statusBar().showMessage(f"No changes to revert for item {current_idx + 1}.", 3000)
    else:
        main_window.statusBar().showMessage("Select an item to revert changes.", 3000)

def revert_selected_items(main_window):

    current_table = main_window._get_current_table()
    if not current_table:
        main_window.statusBar().showMessage("No active table to revert.", 3000)
        return

    selected_indices = current_table.selectedIndexes()
    if not selected_indices:
        main_window.statusBar().showMessage("No selected items to revert.", 3000)
        return

    selected_rows = sorted(list(set(index.row() for index in selected_indices)))
    reverted_count = 0

    for row_index in selected_rows:
        if revert_single_item_logic(main_window, row_index):
            reverted_count += 1

    if reverted_count > 0:
        main_window.statusBar().showMessage(f"Changes reverted for {reverted_count} items.", 3000)

        current_items = main_window._get_current_translatable_items()
        current_data = main_window._get_current_file_data()
        any_text_modified = any(it.get('is_modified_session', False) for it in current_items) if current_items else False
        breakpoint_modified = current_data.get('breakpoint_modified', False) if current_data else False
        main_window._set_current_tab_modified(any_text_modified or breakpoint_modified)
    else:
        main_window.statusBar().showMessage("No changes to revert in selected items.", 3000)

def revert_all_items(main_window):

    current_file_data = main_window._get_current_file_data()
    current_table = main_window._get_current_table() 

    if not current_file_data or not current_table:
        main_window.statusBar().showMessage("Нет активной вкладки для отмены.", 3000)
        return

    current_items = current_file_data.get('items')
    if not current_items: return

    modified_indices = [i for i, item in enumerate(current_items) if item.get('is_modified_session', False)]

    if not modified_indices:
        main_window.statusBar().showMessage("No text changes to revert.", 3000)
        return

    file_name = os.path.basename(current_file_data.get('output_path', main_window.current_file_path or "?"))
    reply = QMessageBox.question(main_window, "Confirm Revert",
                                 f"Revert all {len(modified_indices)} text changes in file {file_name}?\n"
                                 "(Marker changes will remain)",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)

    if reply == QMessageBox.StandardButton.Yes:
        reverted_count = 0
        for index in modified_indices:
            if revert_single_item_logic(main_window, index):
                reverted_count += 1

        if reverted_count > 0:
            main_window.statusBar().showMessage(f"All {reverted_count} text changes reverted.", 4000)

            breakpoint_modified = current_file_data.get('breakpoint_modified', False)
            main_window._set_current_tab_modified(breakpoint_modified)
        else:

            main_window.statusBar().showMessage("Failed to revert changes (internal error?).", 5000)