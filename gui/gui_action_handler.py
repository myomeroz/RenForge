import os
import re 
import sys
import time

from renforge_logger import get_logger
logger = get_logger("gui.action_handler")

try:

    from PySide6.QtWidgets import (QMessageBox, QProgressDialog, QDialog,
                                 QAbstractItemView, QApplication)
    from PySide6.QtCore import (Qt, QObject, Signal, QRunnable, QThreadPool, Slot)
except ImportError:
    logger.critical("PySide6 is required for action handling but not found.")
    sys.exit(1)

import renforge_config as config
import parser.core as parser

from gui.renforge_gui_dialog import (AIEditDialog, GoogleTranslateDialog, InsertLineDialog)

import gui.gui_settings_manager as settings_manager
import gui.gui_table_manager as table_manager 
from locales import tr 
from models.parsed_file import ParsedItem
from dataclasses import replace, asdict 

from gui.views.file_table_view import resolve_table_widget


def edit_with_ai(main_window):
    logger.debug("[edit_with_ai] Action triggered. Checking availability via controller...") 

    controller = getattr(main_window, '_app_controller', None)
    if not controller or not getattr(controller, 'translation_controller', None):
        logger.error("Controller not available for checks.")
        main_window.statusBar().showMessage("Controller unavailable", 4000)
        return

    is_avail, error_key = controller.translation_controller.check_ai_availability()
    if not is_avail:
        main_window.statusBar().showMessage(tr(error_key), 5000)
        # Show specific error based on key if needed, or generic
        return
        
    # Also ensure Gemini initialized (which might show UI)
    # The controller check is passive. The original code called ensure_gemini_initialized which is active.
    # We should keep ensure_gemini_initialized call BUT it is in settings_manager which is view layer (or imported).
    # settings_manager is imported in this file. It is fine to use.
    
    if not settings_manager.ensure_gemini_initialized(main_window, force_init=True):
        main_window.statusBar().showMessage(tr("edit_ai_failed_init"), 5000)
        return

    logger.debug("[edit_with_ai] Gemini checks passed. Proceeding to open dialog.") 
    item_index = main_window._get_current_item_index()
    current_file_data = main_window._get_current_file_data()

    if not current_file_data or item_index < 0:
        main_window.statusBar().showMessage(tr("edit_ai_select_item"), 3000)
        return

    current_items = current_file_data.items
    current_mode = current_file_data.mode
    table_widget = resolve_table_widget(main_window, current_file_data.file_path)

    if not current_items or not current_mode or not table_widget or not (0 <= item_index < len(current_items)):
        logger.error("edit_with_ai - Invalid data state.")
        main_window.statusBar().showMessage(tr("edit_ai_data_error"), 4000)
        return

    dialog = AIEditDialog(main_window, item_index, current_mode)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Get the refined text from dialog result
        edited_text = dialog.result_text.toPlainText() if hasattr(dialog, 'result_text') else ''
        edited_item_index = dialog.item_index
        
        if edited_text and not edited_text.startswith("Gemini could not"):
            # Try FluentWindow's model-based update first
            if hasattr(main_window, 'update_row_translation'):
                success = main_window.update_row_translation(edited_item_index, edited_text)
                if success:
                    main_window._set_current_tab_modified(True)
                    main_window.statusBar().showMessage(tr("edit_ai_success", item=edited_item_index + 1), 3000)
                    logger.info(f"[edit_with_ai] Applied AI edit to row {edited_item_index}")
                    return
            
            # Fallback to legacy table_manager for old GUI
            updated_items = main_window._get_current_translatable_items()
            if updated_items and 0 <= edited_item_index < len(updated_items):
                edited_item = updated_items[edited_item_index]
                table_manager.update_table_item_text(main_window, table_widget, edited_item_index, 4, edited_text)
                table_manager.update_table_row_style(table_widget, edited_item_index, edited_item)
                main_window._set_current_tab_modified(True)
                main_window.statusBar().showMessage(tr("edit_ai_success", item=edited_item_index + 1), 3000)
            else:
                logger.error(f"Could not retrieve updated item data after AI edit for index {edited_item_index}")
                main_window.statusBar().showMessage(tr("edit_ai_update_error"), 5000)
        else:
            logger.warning(f"[edit_with_ai] No valid AI edit to apply")

def translate_with_google(main_window):
    logger.debug("[translate_with_google] Action triggered. Checking prerequisites via controller...") 

    controller = getattr(main_window, '_app_controller', None)
    if not controller or not getattr(controller, 'translation_controller', None):
        logger.error("Controller not available for checks.")
        main_window.statusBar().showMessage("Controller unavailable", 4000)
        return

    is_avail, error_key = controller.translation_controller.check_google_availability()
    if not is_avail:
        logger.warning(f"[translate_with_google] Availability check failed: {error_key}") 
        main_window.statusBar().showMessage(tr(error_key), 4000)
        QMessageBox.warning(main_window, tr("error"), tr(error_key)) # Map key to msg ideally
        return

    logger.debug("[translate_with_google] Prerequisites met. Proceeding...") 
    item_index = main_window._get_current_item_index()
    current_file_data = main_window._get_current_file_data()

    if not current_file_data or item_index < 0:
        main_window.statusBar().showMessage(tr("google_trans_select_item"), 3000)
        return

    current_items = current_file_data.items
    current_mode = current_file_data.mode
    table_widget = resolve_table_widget(main_window, current_file_data.file_path)

    if not current_items or not current_mode or not table_widget or not (0 <= item_index < len(current_items)):
        logger.error("translate_with_google - Invalid data state.")
        main_window.statusBar().showMessage(tr("google_trans_data_error"), 4000)
        return

    dialog = GoogleTranslateDialog(main_window, item_index, current_mode)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Get the translated text from dialog result
        translated_text = dialog.result_text.toPlainText() if hasattr(dialog, 'result_text') else ''
        translated_item_index = dialog.item_index
        
        if translated_text and not translated_text.startswith("Failed"):
            # Try FluentWindow's model-based update first
            if hasattr(main_window, 'update_row_translation'):
                success = main_window.update_row_translation(translated_item_index, translated_text)
                if success:
                    main_window._set_current_tab_modified(True)
                    main_window.statusBar().showMessage(tr("google_trans_success", item=translated_item_index + 1), 3000)
                    logger.info(f"[translate_with_google] Applied translation to row {translated_item_index}")
                    return
            
            # Fallback to legacy table_manager for old GUI
            updated_items = main_window._get_current_translatable_items()
            if updated_items and 0 <= translated_item_index < len(updated_items):
                translated_item = updated_items[translated_item_index]
                table_manager.update_table_item_text(main_window, table_widget, translated_item_index, 4, translated_text)
                table_manager.update_table_row_style(table_widget, translated_item_index, translated_item)
                main_window._set_current_tab_modified(True)
                main_window.statusBar().showMessage(tr("google_trans_success", item=translated_item_index + 1), 3000)
            else:
                logger.error(f"Could not retrieve updated item data after Google Translate for index {translated_item_index}")
                main_window.statusBar().showMessage(tr("google_trans_update_error"), 5000)
        else:
            logger.warning(f"[translate_with_google] No valid translation to apply")

def batch_translate_google(main_window):
    
    controller = getattr(main_window, '_app_controller', None)
    if not controller or not getattr(controller, 'translation_controller', None):
        main_window.statusBar().showMessage("Controller unavailable", 4000)
        return
        
    is_avail, error_key = controller.translation_controller.check_google_availability()
    if not is_avail:
        main_window.statusBar().showMessage(tr(error_key), 4000)
        QMessageBox.warning(main_window, tr("error"), tr(error_key))
        return

    current_table = main_window._get_current_table()
    current_file_data = main_window._get_current_file_data()

    if not current_table or not current_file_data:
        main_window.statusBar().showMessage(tr("batch_no_active_tab"), 3000)
        return

    # FIX: Use get_selected_row_ids for proper proxy-aware index mapping
    if hasattr(current_table, "get_selected_row_ids"):
        selected_rows_indices = current_table.get_selected_row_ids()
    else:
        selected_rows_indices = sorted(list(set(index.row() for index in current_table.selectedIndexes())))
    
    if not selected_rows_indices:
        main_window.statusBar().showMessage(tr("batch_no_selected_rows"), 3000)
        return

    current_items = current_file_data.items
    current_mode = current_file_data.mode
    current_file_lines = current_file_data.lines

    if not current_items or not current_mode or not current_file_lines:
        logger.error("batch_translate_google - Invalid data state.")
        main_window.statusBar().showMessage(tr("batch_data_error"), 4000)
        return

    # Use helper methods on main_window for reliable language code/name retrieval
    source_code = main_window.get_current_source_code() if hasattr(main_window, 'get_current_source_code') else "en"
    target_code = main_window.get_current_target_code() if hasattr(main_window, 'get_current_target_code') else "tr"
    source_name = main_window.get_current_source_language() if hasattr(main_window, 'get_current_source_language') else "English"
    target_name = main_window.get_current_target_language() if hasattr(main_window, 'get_current_target_language') else "Turkish"

    if not target_code:
        QMessageBox.warning(main_window, tr("batch_lang_required_title"), tr("batch_target_lang_required_msg"))
        return
    if not source_code:
        QMessageBox.warning(main_window, tr("batch_lang_required_title"), tr("batch_source_lang_required_msg"))
        return

    confirm_msg = tr("batch_confirm_msg", count=len(selected_rows_indices), source=source_name, source_code=source_code, target=target_name, target_code=target_code)
    reply = QMessageBox.question(main_window, tr("batch_google_title"), confirm_msg,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        main_window.statusBar().showMessage(tr("batch_canceled"), 3000)
        # Butonları sıfırla (güvenlik için)
        if hasattr(main_window, 'translate_page') and main_window.translate_page:
            main_window.translate_page.set_batch_running(False)
        return
    
    # Kullanıcı EVET dedi - şimdi butonları disable et
    if hasattr(main_window, 'translate_page') and main_window.translate_page:
        main_window.translate_page.set_batch_running(True)
        logger.debug("[batch_translate_google] User confirmed, buttons disabled")


    # NOTE: Do NOT auto-switch Inspector to Toplu tab - let user control their view
    # Progress updates will go to batch_controller -> inspector.show_batch_status

    # Convert row IDs to integer indices for undo capture
    # selected_rows_indices may be UUIDs from get_selected_row_ids()
    row_indices_for_undo = []
    if hasattr(main_window, '_current_table_model') and main_window._current_table_model:
        model = main_window._current_table_model
        for row_id in selected_rows_indices:
            idx = model.get_index_by_id(str(row_id))
            if idx is not None:
                row_indices_for_undo.append(idx)
    else:
        # Fallback: treat as integers if no model
        row_indices_for_undo = [int(x) if isinstance(x, int) else 0 for x in selected_rows_indices]

    # Capture undo snapshot before starting batch
    if row_indices_for_undo:
        main_window.batch_controller.capture_undo_snapshot(
            current_file_data.file_path, 
            row_indices_for_undo, 
            current_file_data.items,
            batch_type="google"
        )

    # Start via controller - use converted integer indices
    try:
        worker, signals = controller.translation_controller.start_batch_google_translation(
            current_file_data,
            row_indices_for_undo,  # Use converted integer indices, not UUIDs
            source_code,
            target_code
        )
    except Exception as e:
        logger.error(f"Failed to start batch Google translation: {e}")
        main_window.statusBar().showMessage("Batch start failed", 5000)
        # Re-enable buttons on failure
        if hasattr(main_window, 'translate_page') and main_window.translate_page:
            main_window.translate_page.set_batch_running(False)
        return

    # Signal handlers - progress now goes to batch_controller which updates Inspector
    # signals.progress emits (current, total) - connect to batch_controller for Inspector updates
    def on_progress(current, total):
        """Forward progress to batch_controller for Inspector panel update."""
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            main_window.batch_controller._total_processed = current
            main_window.batch_controller._total_items = total
            main_window.batch_controller._emit_status()
    
    signals.progress.connect(on_progress)
    signals.item_updated.connect(main_window._handle_batch_item_updated)
    signals.error.connect(main_window._handle_batch_translate_error)
    signals.finished.connect(main_window._handle_batch_translate_finished)
    
    # Cancel button in Inspector is already wired via app_bootstrap to batch_controller.cancel
    # Worker cancel is called by batch_controller.cancel which calls worker.cancel if set
    main_window.batch_controller.start_batch(len(row_indices_for_undo))  # Set running=True, enable cancel
    main_window.batch_controller.set_active_worker(worker)

    main_window._clear_batch_results()

    main_window.statusBar().showMessage(tr("batch_starting"), 0) 
    
    # Disable sorting to prevent freeze on updates
    was_sorting = current_table.isSortingEnabled()
    current_table.setSortingEnabled(False)
    
    # Restore sorting on finish
    def restore_sorting():
        current_table.setSortingEnabled(was_sorting)
        
    signals.finished.connect(restore_sorting) 

def batch_translate_ai(main_window):
    logger.debug("[batch_translate_ai] Action triggered.")
    
    # 1. Check prerequisites via Controller
    controller = getattr(main_window, '_app_controller', None)
    if not controller or not getattr(controller, 'translation_controller', None):
        logger.error("Controller unavailable.")
        main_window.statusBar().showMessage("Controller unavailable", 4000)
        return

    # 2. Ensure Gemini Initialized (Active check via settings manager)
    # MUST be done BEFORE check_ai_availability because availability depends on initialization
    if not settings_manager.ensure_gemini_initialized(main_window, force_init=False):
        main_window.statusBar().showMessage(tr("batch_ai_failed_init"), 5000)
        # Show explicit error to avoid "no reaction"
        QMessageBox.warning(main_window, tr("error"), tr("batch_ai_failed_init"))
        return

    # 3. Check Prerequisites (Internet, Model etc.) via Controller
    # Now that we tried to init, this check will be accurate
    is_avail, error_msg_key = controller.translation_controller.check_ai_availability()
    if not is_avail:
        # If error key is network, show network error
        if error_msg_key == "batch_ai_unavailable_net":
            main_window.statusBar().showMessage(tr("batch_ai_unavailable_net"), 4000)
            QMessageBox.warning(main_window, tr("error_no_network_title"), tr("error_no_network_msg_batch_ai"))
        elif error_msg_key == "edit_ai_gemini_unavailable":
             main_window.statusBar().showMessage(tr("batch_ai_gemini_unavailable"), 5000)
             QMessageBox.warning(main_window, tr("edit_ai_gemini_error_title"), tr("edit_ai_gemini_error_msg"))
        else:
             main_window.statusBar().showMessage(tr(error_msg_key or "error"), 5000)
        return
    
    # 3. Get UI Data
    current_table = main_window._get_current_table()
    current_file_data = main_window._get_current_file_data()
    
    if not current_table or not current_file_data:
        main_window.statusBar().showMessage(tr("batch_no_active_tab"), 3000)
        return
    
    # FIX: Use get_selected_row_ids for proper proxy-aware index mapping
    selected_rows_indices = []
    
    if hasattr(current_table, "get_selected_row_ids"):
        # IDs are strings (UUIDs) from RowData
        row_ids = current_table.get_selected_row_ids()
        
        # Convert IDs to integer indices using model
        model = current_table.model()
        if hasattr(model, 'sourceModel'):
             model = model.sourceModel()
             
        # Check if model has ID mapping (TranslationTableModel)
        if hasattr(model, '_id_to_index'):
            for rid in row_ids:
                if rid in model._id_to_index:
                    selected_rows_indices.append(model._id_to_index[rid])
        else:
            # Fallback for legacy tables or if model structure differs
            logger.warning("Model missing _id_to_index mapping, assuming indices or falling back")
            # If IDs are ints (legacy), use them directly
            if row_ids and isinstance(row_ids[0], int):
                 selected_rows_indices = row_ids
                 
    else:
        selected_rows_indices = sorted(list(set(index.row() for index in current_table.selectedIndexes())))
    
    # Ensure indices are valid and sorted
    selected_rows_indices = sorted(list(set(selected_rows_indices)))
    
    if not selected_rows_indices:
        main_window.statusBar().showMessage(tr("batch_no_selected_rows"), 3000)
        return
    
    selected_model = main_window.model_combo.currentText() if main_window.model_combo.count() > 0 else None
    if not selected_model or selected_model == "Loading models...":
        QMessageBox.warning(main_window, tr("batch_lang_required_title"), tr("error_no_model"))
        return
    
    target_name = main_window.target_lang_combo.currentText()
    source_name = main_window.source_lang_combo.currentText()
    # Use language NAMES for Gemini (e.g., "German"), not codes (e.g., "de")
    # Gemini understands natural language names better
    source_lang_for_gemini = source_name.strip()
    target_lang_for_gemini = target_name.strip()
    
    # DEBUG: Log the exact languages being used
    logger.info(f"[batch_translate_ai] UI Selection -> Source: {source_name}, Target: {target_name}")
    logger.info(f"[batch_translate_ai] Passing to Gemini -> source_lang={source_lang_for_gemini}, target_lang={target_lang_for_gemini}")

    confirm_msg = tr("batch_ai_confirm_msg", count=len(selected_rows_indices), model=selected_model, target=target_name)
    reply = QMessageBox.question(main_window, tr("batch_ai_title"), confirm_msg,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        main_window.statusBar().showMessage(tr("batch_canceled"), 3000)
        # Butonları sıfırla (güvenlik için)
        if hasattr(main_window, 'translate_page') and main_window.translate_page:
            main_window.translate_page.set_batch_running(False)
        return
    
    # Kullanıcı EVET dedi - şimdi butonları disable et
    if hasattr(main_window, 'translate_page') and main_window.translate_page:
        main_window.translate_page.set_batch_running(True)
        logger.debug("[batch_translate_ai] User confirmed, buttons disabled")
    
    
    # NOTE: Do NOT auto-switch Inspector to Toplu tab - let user control their view
    # Progress updates will go to batch_controller -> inspector.show_batch_status
    
    # Capture undo snapshot before starting batch
    main_window.batch_controller.capture_undo_snapshot(
        current_file_data.file_path, 
        selected_rows_indices, 
        current_file_data.items,
        batch_type="ai"
    )
    
    # 5. Start Task via Controller - Use NAMES, not codes!
    try:
        worker, signals = controller.translation_controller.start_batch_ai_translation(
            current_file_data, 
            selected_rows_indices, 
            selected_model,
            source_lang=source_lang_for_gemini,
            target_lang=target_lang_for_gemini
        )
    except Exception as e:
        logger.error(f"Failed to start batch AI translation: {e}")
        main_window.statusBar().showMessage(tr("error_batch_start_failed"), 5000)
        # Re-enable buttons on failure
        if hasattr(main_window, 'translate_page') and main_window.translate_page:
            main_window.translate_page.set_batch_running(False)
        return

    # 6. Wire Signals - progress now goes to batch_controller which updates Inspector
    def on_progress(current, total):
        """Forward progress to batch_controller for Inspector panel update."""
        if hasattr(main_window, 'batch_controller') and main_window.batch_controller:
            main_window.batch_controller._total_processed = current
            main_window.batch_controller._total_items = total
            main_window.batch_controller._emit_status()
    
    signals.progress.connect(on_progress)
    signals.item_updated.connect(main_window._handle_batch_item_updated)
    signals.error.connect(main_window._handle_batch_translate_error)
    signals.finished.connect(main_window._handle_batch_translate_finished)
    
    # Cancel button in Inspector is already wired via app_bootstrap to batch_controller.cancel
    # Worker cancel is called by batch_controller.cancel which calls worker.cancel if set
    main_window.batch_controller.start_batch(len(selected_rows_indices))  # Set running=True, enable cancel
    main_window.batch_controller.set_active_worker(worker)
    
    main_window.statusBar().showMessage(tr("batch_starting"), 0)
    
    # Disable sorting to prevent freeze on updates
    was_sorting = current_table.isSortingEnabled()
    current_table.setSortingEnabled(False)
    
    # Restore sorting on finish
    def restore_sorting():
        current_table.setSortingEnabled(was_sorting)
        
    signals.finished.connect(restore_sorting)

def navigate_prev(main_window):
    current_table = main_window._get_current_table()
    current_idx = main_window._get_current_item_index()
    if current_table and current_idx > 0:
        new_index = current_idx - 1
        current_table.selectRow(new_index)
        current_table.scrollToItem(current_table.item(new_index, 0), QAbstractItemView.ScrollHint.PositionAtCenter)

def navigate_next(main_window):
    current_table = main_window._get_current_table()
    current_items = main_window._get_current_translatable_items()
    current_idx = main_window._get_current_item_index()
    if current_table and current_items and 0 <= current_idx < len(current_items) - 1:
        new_index = current_idx + 1
        current_table.selectRow(new_index)
        current_table.scrollToItem(current_table.item(new_index, 0), QAbstractItemView.ScrollHint.PositionAtCenter)

def toggle_breakpoint(main_window):
    item_index = main_window._get_current_item_index()
    current_file_data = main_window._get_current_file_data()

    if not current_file_data or item_index < 0:
        main_window.statusBar().showMessage(tr("marker_select_line"), 3000)
        return

    current_items = current_file_data.items
    current_breakpoints = current_file_data.breakpoints
    current_mode = current_file_data.mode
    table_widget = getattr(current_file_data, 'table_widget', None)

    if not all([current_items, current_breakpoints is not None, current_mode, table_widget]) or not (0 <= item_index < len(current_items)):
         logger.error("toggle_breakpoint - Invalid data state.")
         main_window.statusBar().showMessage(tr("marker_data_error"), 4000)
         return

    item = current_items[item_index]

    line_idx = item.line_index

    if line_idx is None:
        main_window.statusBar().showMessage(tr("marker_line_idx_error", item=item_index + 1), 4000)
        return

    if line_idx in current_breakpoints:
        current_breakpoints.remove(line_idx)
        item.has_breakpoint = False
        status_msg = tr("marker_removed", line=line_idx + 1)
    else:
        current_breakpoints.add(line_idx)
        item.has_breakpoint = True
        status_msg = tr("marker_set", line=line_idx + 1)

    table_manager.update_table_row_style(table_widget, item_index, item)

    current_file_data.breakpoint_modified = True
    main_window._set_current_tab_modified(True)
    main_window.statusBar().showMessage(status_msg, 3000)

def go_to_next_breakpoint(main_window):
    current_file_data = main_window._get_current_file_data()
    if not current_file_data: return

    current_items = current_file_data.items
    current_breakpoints = current_file_data.breakpoints
    table_widget = getattr(current_file_data, 'table_widget', None)

    if not current_items or not current_breakpoints or not table_widget:
        main_window.statusBar().showMessage(tr("marker_nav_no_markers"), 3000)
        return

    start_index = main_window._get_current_item_index()
    num_items = len(current_items)
    found_item_index = -1

    for i in range(start_index + 1, num_items):
        if current_items[i].has_breakpoint:
            found_item_index = i
            break
    else: 
        for i in range(start_index + 1):
            if current_items[i].has_breakpoint:
                found_item_index = i
                main_window.statusBar().showMessage(tr("marker_nav_first"), 2000)
                break

    if found_item_index != -1:
        table_widget.selectRow(found_item_index)
        table_widget.scrollToItem(table_widget.item(found_item_index, 0), QAbstractItemView.ScrollHint.PositionAtCenter)
    else:

        main_window.statusBar().showMessage(tr("marker_nav_not_found"), 3000)

def clear_all_breakpoints(main_window):
    current_file_data = main_window._get_current_file_data()
    if not current_file_data: return

    current_items = current_file_data.items
    current_breakpoints = current_file_data.breakpoints
    table_widget = getattr(current_file_data, 'table_widget', None)

    if not current_items or current_breakpoints is None or not table_widget:
         main_window.statusBar().showMessage(tr("marker_clear_no_data"), 3000)
         return

    if not current_breakpoints:
        main_window.statusBar().showMessage(tr("marker_clear_none_set"), 3000)
        return

    file_name = os.path.basename(current_file_data.output_path or main_window.current_file_path or "?")
    reply = QMessageBox.question(main_window, tr("confirmation"),
                                 tr("marker_clear_confirm_msg", count=len(current_breakpoints), file=file_name),
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)

    if reply == QMessageBox.StandardButton.Yes:
        breakpoints_were_present = len(current_breakpoints) > 0
        current_breakpoints.clear()

        for i, item in enumerate(current_items):
            if item.has_breakpoint:
                item.has_breakpoint = False
                if i < table_widget.rowCount(): 
                     table_manager.update_table_row_style(table_widget, i, item)

        if breakpoints_were_present:
            current_file_data.breakpoint_modified = True
            main_window._set_current_tab_modified(True)
            main_window.statusBar().showMessage(tr("marker_clear_success"), 3000)

def insert_line(main_window):
    current_file_data = main_window._get_current_file_data()
    if not current_file_data or current_file_data.get('mode') != "direct":
        main_window.statusBar().showMessage(tr("insert_line_mode_error"), 3000)
        return

    current_items = current_file_data.items
    current_table = getattr(current_file_data, 'table_widget', None)
    current_file_lines = current_file_data.lines
    current_breakpoints = current_file_data.breakpoints

    if not all([current_items is not None, current_table, current_file_lines is not None, current_breakpoints is not None]):
        main_window.statusBar().showMessage(tr("insert_line_data_error"), 3000)
        return

    insert_after_item_index = main_window._get_current_item_index()

    dialog = InsertLineDialog(main_window)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        raw_new_line = dialog.get_line_text()
        if not raw_new_line:
            main_window.statusBar().showMessage(tr("insert_line_canceled"), 3000)
            return

        parsed_info = parser.parse_line(raw_new_line)
        if not parsed_info or parsed_info['type'] not in config.DIRECT_MODE_EDITABLE_TYPES:
            QMessageBox.warning(main_window, tr("parsing_error"),
                              tr("insert_line_parse_error_msg", line=raw_new_line, types=', '.join(config.DIRECT_MODE_EDITABLE_TYPES)))
            return

        new_line_file_index = 0
        new_item_list_index = 0
        if insert_after_item_index == -1: 
             pass 
        elif 0 <= insert_after_item_index < len(current_items):
             line_index_of_selected = current_items[insert_after_item_index]['line_index']
             new_line_file_index = line_index_of_selected + 1
             new_item_list_index = insert_after_item_index + 1
        else: 
             new_line_file_index = len(current_file_lines)
             new_item_list_index = len(current_items)

        formatted_line = parser.format_line_from_components(parsed_info, parsed_info['text'])
        if formatted_line is None:
             QMessageBox.critical(main_window, tr("error"), tr("insert_line_format_error"))
             return

        current_file_lines.insert(new_line_file_index, formatted_line)

        new_item = ParsedItem(
            line_index=new_line_file_index, 
            original_text=parsed_info['text'], 
            current_text=parsed_info['text'],
            initial_text=parsed_info['text'], 
            is_modified_session=True, 
            type=parsed_info['type'],
            character_tag=parsed_info.get('character_tag'),
            parsed_data=parsed_info,
            has_breakpoint=False
        )
        # Note: variable_name and character_trans are None by default, which is correct for direct mode new lines.

        current_items.insert(new_item_list_index, new_item)

        for i in range(new_item_list_index + 1, len(current_items)):
            current_items[i].line_index += 1

        new_breakpoints = set()
        bp_indices_changed = False
        for bp_idx in current_breakpoints:
            if bp_idx >= new_line_file_index:
                new_breakpoints.add(bp_idx + 1)
                bp_indices_changed = True
            else:
                new_breakpoints.add(bp_idx)
        current_file_data.breakpoints = new_breakpoints
        if bp_indices_changed:
             current_file_data.breakpoint_modified = True

        was_blocked = main_window._block_item_changed_signal
        main_window._block_item_changed_signal = True
        try:

            table_manager.populate_table(current_table, current_items, "direct")
        finally:
            main_window._block_item_changed_signal = was_blocked

        if 0 <= new_item_list_index < current_table.rowCount():
            current_table.selectRow(new_item_list_index)
            current_table.scrollToItem(current_table.item(new_item_list_index, 0), QAbstractItemView.ScrollHint.PositionAtCenter)
            main_window._set_current_item_index(new_item_list_index) 
        else:
             main_window._set_current_item_index(-1) 

        main_window._set_current_tab_modified(True)
        main_window.statusBar().showMessage(tr("insert_line_success"), 3000)

def delete_line(main_window):
    current_file_data = main_window._get_current_file_data()
    if not current_file_data or current_file_data.get('mode') != "direct":
        main_window.statusBar().showMessage(tr("delete_line_mode_error"), 3000)
        return

    delete_item_index = main_window._get_current_item_index()
    current_items = current_file_data.items
    current_table = getattr(current_file_data, 'table_widget', None)
    current_file_lines = current_file_data.lines
    current_breakpoints = current_file_data.breakpoints

    if not all([current_items, current_table, current_file_lines is not None, current_breakpoints is not None]) or not (0 <= delete_item_index < len(current_items)):
        main_window.statusBar().showMessage(tr("delete_line_select_error"), 3000)
        return

    item_to_delete = current_items[delete_item_index]
    line_index_to_delete = item_to_delete.line_index

    file_name = os.path.basename(current_file_data.output_path or main_window.current_file_path or "?")
    text_preview = (item_to_delete.current_text or '')[:50] + ("..." if len(item_to_delete.current_text or '') > 50 else "")
    reply = QMessageBox.question(main_window, tr("delete_line_confirm_title"),
                                 tr("delete_line_confirm_msg", line=line_index_to_delete + 1, file=file_name, text=text_preview),
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)

    if reply == QMessageBox.StandardButton.Yes:
        try:

            breakpoint_removed = item_to_delete.has_breakpoint

            if 0 <= line_index_to_delete < len(current_file_lines):
                del current_file_lines[line_index_to_delete]
            else:
                raise IndexError(f"Invalid line index {line_index_to_delete} for deletion. Data corrupted?")

            del current_items[delete_item_index]

            for i in range(delete_item_index, len(current_items)):
                current_items[i].line_index -= 1

            new_breakpoints = set()
            bp_indices_changed = False
            for bp_idx in current_breakpoints:
                if bp_idx == line_index_to_delete:
                    bp_indices_changed = True 
                    continue
                elif bp_idx > line_index_to_delete:
                    new_breakpoints.add(bp_idx - 1)
                    bp_indices_changed = True
                else:
                    new_breakpoints.add(bp_idx)
            current_file_data.breakpoints = new_breakpoints
            if bp_indices_changed:
                 current_file_data.breakpoint_modified = True

            was_blocked = main_window._block_item_changed_signal
            main_window._block_item_changed_signal = True
            try:
                table_manager.populate_table(current_table, current_items, "direct")
            finally:
                main_window._block_item_changed_signal = was_blocked

            new_index_to_select = -1
            if current_items:
                new_index_to_select = max(0, min(delete_item_index, len(current_items) - 1))

            if new_index_to_select >= 0:
                current_table.selectRow(new_index_to_select)
                current_table.scrollToItem(current_table.item(new_index_to_select, 0), QAbstractItemView.ScrollHint.PositionAtCenter)
                main_window._set_current_item_index(new_index_to_select)
            else: 
                main_window._set_current_item_index(-1)

            main_window._set_current_tab_modified(True)
            status_msg = tr("delete_line_success")
            if breakpoint_removed : status_msg += f" ({tr('marker_removed_short')})"
            main_window.statusBar().showMessage(status_msg + ".", 3000)

        except IndexError as e:
            QMessageBox.critical(main_window, tr("delete_line_error_title"), tr("delete_line_index_error", error=e))
        except Exception as e:
            QMessageBox.critical(main_window, tr("delete_line_error_title"), tr("delete_line_unexpected_error", error=e))

    else: 
        main_window.statusBar().showMessage(tr("delete_line_canceled"), 3000)

def handle_find_prev(main_window):
    """Delegate to SearchManager."""
    if not getattr(main_window, 'search_manager', None): return

    current_table = main_window._get_current_table()
    if not current_table: return

    search_text = main_window.search_input.text() if main_window.search_input else ""
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 
    
    main_window.search_manager.find_prev(current_table, search_text, use_regex)

def handle_find_next(main_window):
    """Delegate to SearchManager."""
    if not getattr(main_window, 'search_manager', None):
        logger.error("SearchManager not initialized.")
        return

    current_table = main_window._get_current_table()
    if not current_table:
        main_window.statusBar().showMessage(tr("search_enter_text_error"), 3000)
        return

    search_text = main_window.search_input.text() if main_window.search_input else ""
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 
    
    main_window.search_manager.find_next(current_table, search_text, use_regex)

def handle_replace(main_window):
    """Delegate to SearchManager."""
    if not getattr(main_window, 'search_manager', None): return

    current_table = main_window._get_current_table()
    if not current_table: return

    search_text = main_window.search_input.text() if main_window.search_input else ""
    replace_text = main_window.replace_input.text() if main_window.replace_input else ""
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 
    safe_mode = main_window.search_safe_mode_chk.isChecked() if main_window.search_safe_mode_chk else True
    
    main_window.search_manager.replace_current(current_table, search_text, replace_text, use_regex, safe_mode)

def handle_replace_all(main_window):
    """Delegate to SearchManager."""
    if not getattr(main_window, 'search_manager', None): return

    current_table = main_window._get_current_table()
    if not current_table: return

    search_text = main_window.search_input.text() if main_window.search_input else ""
    replace_text = main_window.replace_input.text() if main_window.replace_input else ""
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 
    
    scope = main_window.search_scope_combo.currentData() if main_window.search_scope_combo else "visible"
    safe_mode = main_window.search_safe_mode_chk.isChecked() if main_window.search_safe_mode_chk else True
    
    main_window.search_manager.replace_all(current_table, search_text, replace_text, use_regex, scope, safe_mode)