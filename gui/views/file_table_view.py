# -*- coding: utf-8 -*-
"""
RenForge File Table View

Provides deterministic table widget resolution and wrapper functions
for table operations. Delegates to gui_table_manager for actual operations.
"""

from PyQt6.QtWidgets import QTableWidget

from renforge_logger import get_logger
logger = get_logger("gui.views.file_table_view")

import gui.gui_table_manager as table_manager


def resolve_table_widget(main_window, file_path: str) -> QTableWidget | None:
    """
    Resolve table widget on-demand via tab_data mapping.
    
    This is the deterministic lookup method - no caching on models,
    always looks up via the tab_data dictionary.
    
    Args:
        main_window: The RenForgeGUI instance
        file_path: Path of the file to find table for
        
    Returns:
        QTableWidget or None if not found
    """
    for i in range(main_window.tab_widget.count()):
        if main_window.tab_data.get(i) == file_path:
            widget = main_window.tab_widget.widget(i)
            if isinstance(widget, QTableWidget):
                return widget
    return None


def get_selected_indices(table_widget: QTableWidget) -> list:
    """
    Get list of selected row indices from table.
    
    Args:
        table_widget: The QTableWidget to query
        
    Returns:
        Sorted list of unique selected row indices
    """
    if not table_widget:
        return []
    return sorted(list(set(index.row() for index in table_widget.selectedIndexes())))


def update_row_text(main_window, table_widget: QTableWidget, row_index: int, 
                    column_index: int, new_text: str):
    """
    Update text in a specific table cell.
    
    Delegates to table_manager.update_table_item_text.
    
    Args:
        main_window: The RenForgeGUI instance
        table_widget: The QTableWidget to update
        row_index: Row index to update
        column_index: Column index to update
        new_text: New text content
    """
    table_manager.update_table_item_text(main_window, table_widget, row_index, column_index, new_text)


def update_row_style(table_widget: QTableWidget, row_index: int, item_data):
    """
    Update row styling based on item state.
    
    Delegates to table_manager.update_table_row_style.
    
    Args:
        table_widget: The QTableWidget to update
        row_index: Row index to update
        item_data: ParsedItem or dict with item state info
    """
    table_manager.update_table_row_style(table_widget, row_index, item_data)
