"""
RenForge Status Bar Updater
Handles updating the main window status bar.
"""
import os
from locales import tr
from renforge_logger import get_logger
logger = get_logger("gui.status_updater")


def update_status_bar(main_window):
    current_tab_index = main_window.tab_widget.currentIndex()

    if current_tab_index == -1:
        main_window.statusBar().showMessage(tr("status_no_open_files"))
        return

    current_file_data = main_window._get_current_file_data()

    if not current_file_data:
        main_window.statusBar().showMessage(tr("active_tab_data_error"))
        logger.error("update_status_bar: Could not get file data for current tab.")
        return

    status_parts = []

    if main_window.current_project_path:
        project_name = os.path.basename(main_window.current_project_path)
        status_parts.append(tr("status_project", name=project_name))

    file_path = main_window.current_file_path 
    output_path = current_file_data.output_path or file_path
    base_name = os.path.basename(output_path) if output_path else "<???>"
    file_status = tr("status_file", name=base_name)
    if current_file_data.is_modified:
        file_status += "*"
    status_parts.append(file_status)

    current_mode = current_file_data.mode or '?'
    if current_mode == "direct":
        mode_text = tr("status_mode_direct")
    elif current_mode == "translate":
        mode_text = tr("status_mode_translate")
    else:
        mode_text = tr("status_mode_unknown")
    status_parts.append(tr("status_mode", mode=mode_text))

    current_items = current_file_data.items
    item_count = len(current_items) if current_items is not None else 0
    status_parts.append(tr("status_items", count=item_count))

    current_idx = getattr(current_file_data, 'item_index', -1)
    if current_items and 0 <= current_idx < item_count:
        item = current_items[current_idx]
        status_parts.append(tr("status_selected", current=current_idx + 1, total=item_count))

        # ParsedItem uses line_index for direct mode, and has translated_line_index for translate mode
        if current_mode == "translate":
            line_num = getattr(item, 'line_index', None)  # translated line index
        else:
            line_num = getattr(item, 'line_index', None)
        if line_num is not None:
            status_parts.append(tr("status_line", num=line_num + 1))

        char_tag = getattr(item, 'character_trans', None) or getattr(item, 'character_tag', None) or ""
        if char_tag:
            status_parts.append(tr("status_character", tag=char_tag))

        item_type = getattr(item, 'type', '?')
        # Convert enum to string if needed
        if hasattr(item_type, 'value'):
            item_type = item_type.value
        status_parts.append(tr("status_type", type=item_type))

        status_flags = []
        if getattr(item, 'has_breakpoint', False):
            status_flags.append(tr("status_marker"))
        if getattr(item, 'is_modified_session', False):
            status_flags.append(tr("status_modified"))
        if status_flags:
            status_parts.append(f"[{'|'.join(status_flags)}]")

    elif item_count > 0:
        status_parts.append(tr("status_no_selection"))

    status_message = " | ".join(status_parts)
    main_window.statusBar().showMessage(status_message)