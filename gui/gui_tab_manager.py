import os
import gc 

try:

    from PyQt6.QtWidgets import QApplication, QMessageBox, QTableWidget
    from PyQt6.QtCore import Qt
except ImportError:
    print("CRITICAL ERROR: PyQt6 is required for tab management but not found.")
    import sys
    sys.exit(1)

import renforge_config as config

def add_new_tab(main_window, file_path, table_widget: QTableWidget, tab_name):
    tab_index = main_window.tab_widget.addTab(table_widget, tab_name)
    main_window.tab_widget.setTabToolTip(tab_index, file_path) 

    main_window.tab_data[tab_index] = file_path

    main_window.tab_widget.setCurrentIndex(tab_index)
    print(f"Tab added: Index={tab_index}, Path={file_path}, Name={tab_name}")
    print(f"  Updated tab_data: {main_window.tab_data}")

def handle_tab_changed(main_window, index):
    if index == -1: 
        print("Debug: handle_tab_changed - No tabs remaining.")
        main_window.current_file_path = None

        main_window._update_ui_state()
        main_window._display_current_item_status() 
        return

    file_path = main_window.tab_data.get(index)
    widget = main_window.tab_widget.widget(index)
    widget_path = widget.property("filePath") if widget else None

    if file_path is None and widget_path:
        print(f"Info: handle_tab_changed - Path for index {index} not in tab_data, using widget property: {widget_path}")
        file_path = widget_path
        main_window.tab_data[index] = file_path 
    elif file_path and widget_path and file_path != widget_path:
        print(f"Warning: handle_tab_changed - Path mismatch! Index: {index}, tab_data: '{file_path}', widget: '{widget_path}'. Trusting widget path.")
        file_path = widget_path
        main_window.tab_data[index] = file_path 
    elif file_path is None and widget_path is None:
        print(f"ERROR: handle_tab_changed - Cannot determine file path for tab index {index}. Critical state!")
        QMessageBox.critical(main_window, "Tab Error", f"Critical error: Could not determine file for tab {index}.")

        main_window.current_file_path = None
        main_window._update_ui_state()
        main_window._display_current_item_status()
        return

    file_data = main_window.file_data.get(file_path)
    if not file_data:
        print(f"ERROR: handle_tab_changed - Data for path '{file_path}' (Index: {index}) not found in file_data!")

        QMessageBox.critical(main_window, "Tab Data Error", f"Critical error: Data inconsistency detected for tab '{os.path.basename(file_path)}'.\nPlease try closing and reloading the file.")
        main_window.current_file_path = None

        main_window._update_ui_state()
        main_window._display_current_item_status()
        return

    main_window.current_file_path = file_path

    main_window._update_language_model_display()

    main_window._update_ui_state()
    main_window._display_current_item_status()

    table_widget = file_data.get('table_widget')
    if table_widget:
        table_widget.setFocus()

        if table_widget.rowCount() > 0 and not table_widget.selectedItems():
             current_item_idx = main_window._get_current_item_index() 
             if current_item_idx >= 0 and current_item_idx < table_widget.rowCount():
                  table_widget.selectRow(current_item_idx)

             else:

                  table_widget.selectRow(0)
                  main_window._set_current_item_index(0) 

def find_tab_by_path(main_window, file_path):
    for index, path in main_window.tab_data.items():
        if path == file_path:
            return index
    return None 

def close_tab(main_window, index):
    print(f"Debug: close_tab initiated for index {index}")
    if not (0 <= index < main_window.tab_widget.count()):
        print(f"Debug: Invalid index {index} passed to close_tab.")
        return

    file_path = main_window.tab_data.get(index)
    widget_to_remove = main_window.tab_widget.widget(index) 

    if not file_path:
        print(f"Warning: No file path found in tab_data for index {index}. Closing tab anyway.")

    elif file_path in main_window.file_data:
        file_data = main_window.file_data[file_path]
        if file_data.get('is_modified', False):
            base_name = os.path.basename(file_data.get('output_path', file_path))
            msg_box = QMessageBox(main_window)
            msg_box.setWindowTitle("Save Changes?")
            msg_box.setText(f"File '{base_name}' has unsaved changes.")
            msg_box.setInformativeText("Save changes before closing the tab?")
            msg_box.setIcon(QMessageBox.Icon.Question)
            save_button = msg_box.addButton("Save", QMessageBox.ButtonRole.YesRole)
            discard_button = msg_box.addButton("Discard", QMessageBox.ButtonRole.NoRole)
            cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(save_button)

            msg_box.exec()
            clicked_button = msg_box.clickedButton()

            if clicked_button == save_button:

                import gui.gui_file_manager as file_manager

                if main_window.tab_widget.currentIndex() != index:
                     main_window.tab_widget.setCurrentIndex(index)
                     QApplication.processEvents() 

                if not file_manager.save_changes(main_window):
                    main_window.statusBar().showMessage("Save failed. Tab closing cancelled.", 5000)
                    return 
            elif clicked_button == cancel_button:
                main_window.statusBar().showMessage("Tab closing cancelled.", 3000)
                return 

    print(f"Closing tab: Index={index}, Path={file_path}")

    if file_path and file_path in main_window.file_data:
        print(f"  Removing data for {file_path} from file_data...")
        try:

            data_entry = main_window.file_data[file_path]
            data_entry.get('items', []).clear()
            data_entry.get('lines', []).clear()
            data_entry.get('breakpoints', set()).clear()

            data_entry['table_widget'] = None
        except Exception as e:
            print(f"  Warning: Error during pre-removal cleanup: {e}")
        del main_window.file_data[file_path]
        print(f"  Data for {file_path} removed.")

    print(f"  Removing tab {index} from QTabWidget...")

    main_window.tab_widget.removeTab(index)
    print(f"  Tab {index} removed.")

    print("  Rebuilding tab_data...")
    rebuild_tab_data(main_window)
    print(f"  Rebuilt tab_data: {main_window.tab_data}")

    print("  Running garbage collector...")
    collected = gc.collect()
    print(f"  GC collected {collected} objects.")

def close_current_tab(main_window):
    current_index = main_window.tab_widget.currentIndex()
    if current_index != -1:
        close_tab(main_window, current_index)
    else:
        main_window.statusBar().showMessage("No active tab to close.", 3000)

def rebuild_tab_data(main_window):
    new_tab_data = {}
    for i in range(main_window.tab_widget.count()):
        widget = main_window.tab_widget.widget(i)
        if widget:
            path = widget.property("filePath")
            if path:
                new_tab_data[i] = path
            else:
                print(f"ERROR (rebuild_tab_data): Widget at index {i} has no 'filePath' property!")
        else:
             print(f"ERROR (rebuild_tab_data): Could not get widget at index {i}!")
    main_window.tab_data = new_tab_data

def handle_tab_moved(main_window, from_index, to_index):
    print(f"Debug: Tab moved from {from_index} to {to_index}. Rebuilding tab_data...")
    rebuild_tab_data(main_window)
    print(f"Debug: Rebuilt tab_data after move: {main_window.tab_data}")

    current_index_after_move = main_window.tab_widget.currentIndex()
    if current_index_after_move != -1:
        new_path_at_current_index = main_window.tab_data.get(current_index_after_move)
        if new_path_at_current_index != main_window.current_file_path:
             print(f"Debug: Updating current_file_path after tab move to '{new_path_at_current_index}'")
             main_window.current_file_path = new_path_at_current_index

