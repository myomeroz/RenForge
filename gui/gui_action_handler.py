import os
import re 
import sys
import time

from renforge_logger import get_logger
logger = get_logger("gui.action_handler")

try:

    from PyQt6.QtWidgets import (QMessageBox, QProgressDialog, QDialog,
                                 QAbstractItemView, QApplication)
    from PyQt6.QtCore import (Qt, QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot)
except ImportError:
    logger.critical("PyQt6 is required for action handling but not found.")
    sys.exit(1)

import renforge_config as config
import renforge_core as core
import renforge_ai as ai
import renforge_parser as parser

from gui.renforge_gui_dialog import (AIEditDialog, GoogleTranslateDialog, InsertLineDialog)

import gui.gui_settings_manager as settings_manager
import gui.gui_table_manager as table_manager 
from locales import tr 
from renforge_models import TabData, ParsedItem
from dataclasses import replace, asdict 

class WorkerSignals(QObject):

    progress = pyqtSignal(int)
    item_updated = pyqtSignal(int, str, object) # Updated to pass ParsedItem object (or dict if converted)
    error_occurred = pyqtSignal(str)
    variables_warning = pyqtSignal(str)
    finished = pyqtSignal(dict)
    request_mark_modified = pyqtSignal()

class BatchTranslateWorker(QRunnable):

    def __init__(self, signals, selected_indices, items_data_copy, lines_copy, source_code, target_code, mode):
        super().__init__()
        self.signals = signals
        self.selected_indices = selected_indices
        self.items_data_copy = items_data_copy 
        self.lines_copy = lines_copy 
        self.source_code = source_code
        self.target_code = target_code
        self.mode = mode
        self._is_canceled = False
        self.translator = None 

    def cancel(self):
        logger.debug("BatchTranslateWorker: Cancel requested")
        self._is_canceled = True

    @pyqtSlot()
    def run(self):
        logger.debug("BatchTranslateWorker: Run started")
        processed_count = 0
        success_count = 0
        error_count = 0
        variable_mismatch_count = 0
        errors_details = []
        variable_warnings_details = []
        made_changes = False

        Translator = ai._lazy_import_translator() 
        if Translator is None:
            errors_details.append(f"- {tr('batch_error_deep_translator_not_found')}")
            results = {
                'processed': processed_count, 'total': len(self.selected_indices),
                'success': success_count, 'errors': error_count + 1, 
                'warnings': variable_mismatch_count, 'errors_details': errors_details,
                'warnings_details': variable_warnings_details, 'made_changes': made_changes
            }
            self.signals.finished.emit(results)
            return

        try:
            self.translator = Translator(source=self.source_code, target=self.target_code)
        except Exception as e:
            errors_details.append(f"- {tr('batch_error_google_translator_init_failed', error=e)}")
            results = {
                'processed': processed_count, 'total': len(self.selected_indices),
                'success': success_count, 'errors': error_count + 1,
                'warnings': variable_mismatch_count, 'errors_details': errors_details,
                'warnings_details': variable_warnings_details, 'made_changes': made_changes
            }
            self.signals.finished.emit(results)
            return

        total_items = len(self.selected_indices)
        for i, item_index in enumerate(self.selected_indices):
            if self._is_canceled:
                logger.debug("BatchTranslateWorker: Canceled during loop")
                errors_details.append(f"- {tr('batch_task_canceled')}")
                break 

            self.signals.progress.emit(i)

            if not (0 <= item_index < len(self.items_data_copy)):
                logger.warning(f"Skipping invalid index {item_index} during batch translate (Worker).")
                err_detail = f"- {tr('batch_skipped_invalid_index', index=item_index+1)}"
                errors_details.append(err_detail)
                error_count += 1
                continue

            item_data: ParsedItem = self.items_data_copy[item_index]
            text_to_translate = ""
            current_text_for_vars = ""
            # text_key_to_update logic removed, we use unified fields
            line_index_to_update = -1

            if self.mode == 'translate':
                text_to_translate = item_data.original_text or ''
                current_text_for_vars = item_data.current_text or ''
                line_index_to_update = item_data.line_index
            elif self.mode == 'direct':
                text_to_translate = item_data.original_text or ''
                current_text_for_vars = item_data.current_text or ''
                line_index_to_update = item_data.line_index

            if not text_to_translate:
                processed_count += 1 
                continue

            if item_data.initial_text is None:
                 item_data.initial_text = current_text_for_vars 

            try:

                if self._is_canceled:
                     logger.debug("BatchTranslateWorker: Canceled before translate call")
                     errors_details.append(f"- {tr('batch_task_canceled')}")
                     break

                translated_text = self.translator.translate(text_to_translate)

                if self._is_canceled:
                    logger.debug("BatchTranslateWorker: Canceled after translate call")
                    errors_details.append(f"- {tr('batch_task_canceled')}")
                    break

                processed_count += 1 

                if translated_text and translated_text != current_text_for_vars:
                    original_vars = set(re.findall(r'(\[.*?\])', current_text_for_vars))
                    translated_vars = set(re.findall(r'(\[.*?\])', translated_text))
                    if original_vars != translated_vars:
                        variable_mismatch_count += 1
                        var_warn_detail = f"- {tr('batch_variable_mismatch', item=item_index+1)}"
                        if line_index_to_update is not None: var_warn_detail += f" ({tr('file_line_label', line=line_index_to_update+1)})"
                        var_warn_detail += f": {original_vars} -> {translated_vars}"
                        variable_warnings_details.append(var_warn_detail)
                        self.signals.variables_warning.emit(var_warn_detail) 

                    item_data.current_text = translated_text
                    item_data.is_modified_session = True
                    made_changes = True

                    vars_source_text = item_data.original_text if self.mode == 'translate' else current_text_for_vars

                    original_vars = set(re.findall(r'(\[.*?\])', vars_source_text))
                    translated_vars = set(re.findall(r'(\[.*?\])', translated_text))
                    if original_vars != translated_vars:
                        variable_mismatch_count += 1
                        var_warn_detail = f"- {tr('batch_variable_mismatch', item=item_index+1)}"
                        if line_index_to_update is not None: var_warn_detail += f" ({tr('file_line_label', line=line_index_to_update+1)})"
                        var_warn_detail += f": {original_vars} -> {translated_vars}"
                        variable_warnings_details.append(var_warn_detail)
                        self.signals.variables_warning.emit(var_warn_detail) 

                    item_data.current_text = translated_text
                    item_data.is_modified_session = True
                    made_changes = True

                    self.signals.item_updated.emit(item_index, translated_text, item_data)
                    logger.debug(f"DEBUG [Worker]: Before emit item_updated for index {item_index}. "
                          f"Parsed data present: {item_data.parsed_data is not None}")
                    success_count += 1

                elif not translated_text:
                    error_count += 1
                    err_detail = f"- {tr('batch_empty_translation', item=item_index+1)}"
                    if line_index_to_update is not None: err_detail += f" ({tr('file_line_label', line=line_index_to_update+1)})"
                    errors_details.append(err_detail)
                    self.signals.error_occurred.emit(err_detail)

                if not self._is_canceled:
                    time.sleep(config.BATCH_TRANSLATE_DELAY)

            except Exception as e:

                 if self._is_canceled:
                      logger.debug("BatchTranslateWorker: Canceled during exception handling")
                      errors_details.append("- Task canceled by user.")
                      break

                 error_count += 1
                 err_detail = f"- {tr('batch_translation_error', item=item_index+1)}"
                 if line_index_to_update is not None: err_detail += f" ({tr('file_line_label', line=line_index_to_update+1)})"
                 err_detail += f": {type(e).__name__}"
                 errors_details.append(err_detail)
                 self.signals.error_occurred.emit(err_detail) 
                 logger.error(f"  Batch translate error detail: {err_detail}. Full error: {e}")

                 time.sleep(config.BATCH_TRANSLATE_DELAY * 2)
                 continue 

        if not self._is_canceled:
            self.signals.progress.emit(total_items)

        if made_changes:
            self.signals.request_mark_modified.emit()

        logger.debug(f"BatchTranslateWorker: Run finished. Processed: {processed_count}, Success: {success_count}, Errors: {error_count}, Warnings: {variable_mismatch_count}")
        results = {
            'processed': processed_count, 'total': total_items,
            'success': success_count, 'errors': error_count,
            'warnings': variable_mismatch_count, 'errors_details': errors_details,
            'warnings_details': variable_warnings_details, 'made_changes': made_changes,
            'canceled': self._is_canceled
        }
        self.signals.finished.emit(results)

def edit_with_ai(main_window):
    logger.debug("[edit_with_ai] Action triggered. Ensuring Gemini is initialized...") 

    if not settings_manager.ensure_gemini_initialized(main_window, force_init=True):

        logger.warning("[edit_with_ai] ensure_gemini_initialized returned False. Aborting.") 

        main_window.statusBar().showMessage(tr("edit_ai_failed_init"), 5000)
        return

    if ai.no_ai or ai.gemini_model is None:
        logger.warning(f"[edit_with_ai] Check failed AFTER ensure_gemini_initialized. "
              f"ai.no_ai={ai.no_ai}, ai.gemini_model is None={ai.gemini_model is None}") 
        main_window.statusBar().showMessage(tr("edit_ai_gemini_unavailable"), 5000)
        QMessageBox.warning(main_window, tr("edit_ai_gemini_error_title"),
                            tr("edit_ai_gemini_error_msg"))
        return

    logger.debug("[edit_with_ai] Gemini checks passed. Proceeding to open dialog.") 
    item_index = main_window._get_current_item_index()
    current_file_data = main_window._get_current_file_data()

    if not current_file_data or item_index < 0:
        main_window.statusBar().showMessage(tr("edit_ai_select_item"), 3000)
        return

    current_items = current_file_data.items
    current_mode = current_file_data.mode
    table_widget = getattr(current_file_data, 'table_widget', None)

    if not current_items or not current_mode or not table_widget or not (0 <= item_index < len(current_items)):
        logger.error("edit_with_ai - Invalid data state.")
        main_window.statusBar().showMessage(tr("edit_ai_data_error"), 4000)
        return

    dialog = AIEditDialog(main_window, item_index, current_mode)
    if dialog.exec() == QDialog.DialogCode.Accepted:

        updated_items = main_window._get_current_translatable_items() 
        edited_item_index = dialog.item_index 

        if updated_items and 0 <= edited_item_index < len(updated_items):
            edited_item = updated_items[edited_item_index]
            # text_key logic removed
            edited_text = edited_item.current_text or ''

            table_manager.update_table_item_text(main_window, table_widget, edited_item_index, 4, edited_text)

            table_manager.update_table_row_style(table_widget, edited_item_index, edited_item)

            main_window._set_current_tab_modified(True)
            main_window.statusBar().showMessage(tr("edit_ai_success", item=edited_item_index + 1), 3000)
        else:
            logger.error(f"Could not retrieve updated item data after AI edit for index {edited_item_index}")
            main_window.statusBar().showMessage(tr("edit_ai_update_error"), 5000)

def translate_with_google(main_window):
    logger.debug("[translate_with_google] Action triggered. Checking prerequisites...") 

    if not ai.is_internet_available():
        logger.warning("[translate_with_google] Network check failed.") 
        main_window.statusBar().showMessage(tr("google_trans_unavailable_net"), 4000)
        QMessageBox.warning(main_window, tr("error_no_network_title"), tr("error_no_network_msg_google"))
        return

    Translator = ai._lazy_import_translator()
    if Translator is None:
        logger.warning("[translate_with_google] deep-translator library check failed.") 
        main_window.statusBar().showMessage(tr("google_trans_unavailable_lib"), 4000)
        QMessageBox.critical(main_window, tr("error_library_not_found_title"),
                             tr("error_library_not_found_msg"))
        return

    logger.debug("[translate_with_google] Prerequisites met. Proceeding...") 
    item_index = main_window._get_current_item_index()
    current_file_data = main_window._get_current_file_data()

    if not current_file_data or item_index < 0:
        main_window.statusBar().showMessage(tr("google_trans_select_item"), 3000)
        return

    current_items = current_file_data.items
    current_mode = current_file_data.mode
    table_widget = getattr(current_file_data, 'table_widget', None)

    if not current_items or not current_mode or not table_widget or not (0 <= item_index < len(current_items)):
        logger.error("translate_with_google - Invalid data state.")
        main_window.statusBar().showMessage(tr("google_trans_data_error"), 4000)
        return

    dialog = GoogleTranslateDialog(main_window, item_index, current_mode)
    if dialog.exec() == QDialog.DialogCode.Accepted:

        updated_items = main_window._get_current_translatable_items()
        translated_item_index = dialog.item_index

        if updated_items and 0 <= translated_item_index < len(updated_items):
            translated_item = updated_items[translated_item_index]
            # text_key logic removed
            translated_text = translated_item.current_text or ''

            table_manager.update_table_item_text(main_window, table_widget, translated_item_index, 4, translated_text)
            table_manager.update_table_row_style(table_widget, translated_item_index, translated_item)

            main_window._set_current_tab_modified(True)
            main_window.statusBar().showMessage(tr("google_trans_success", item=translated_item_index + 1), 3000)
        else:
            logger.error(f"Could not retrieve updated item data after Google Translate for index {translated_item_index}")
            main_window.statusBar().showMessage(tr("google_trans_update_error"), 5000)

def batch_translate_google(main_window):
    if not ai.is_internet_available(): 
        main_window.statusBar().showMessage(tr("batch_google_unavailable_net"), 4000)
        QMessageBox.warning(main_window, tr("error_no_network_title"), tr("error_no_network_msg_batch"))
        return

    Translator = ai._lazy_import_translator() 
    if Translator is None:
        main_window.statusBar().showMessage(tr("batch_google_unavailable_lib"), 4000)
        QMessageBox.warning(main_window, tr("error_library_not_found_title"),
                            tr("error_library_not_found_msg_shorter"))
        return

    current_table = main_window._get_current_table()
    current_file_data = main_window._get_current_file_data()

    if not current_table or not current_file_data:
        main_window.statusBar().showMessage(tr("batch_no_active_tab"), 3000)
        return

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

    source_code = main_window.source_lang_combo.currentData()
    target_code = main_window.target_lang_combo.currentData()
    source_name = main_window.source_lang_combo.currentText()
    target_name = main_window.target_lang_combo.currentText()

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
        return

    progress = QProgressDialog(tr("batch_progress_msg"), tr("cancel"), 0, len(selected_rows_indices), main_window)
    progress.setWindowTitle(tr("batch_google_title"))
    progress.setWindowModality(Qt.WindowModality.WindowModal)

    progress.setAutoClose(False)
    progress.setAutoReset(False) 

    items_copy = [replace(item) for item in current_items] 
    lines_copy = list(current_file_lines) 

    worker_signals = WorkerSignals()
    worker = BatchTranslateWorker(
        signals=worker_signals,
        selected_indices=selected_rows_indices,
        items_data_copy=items_copy, 
        lines_copy=lines_copy, 
        source_code=source_code,
        target_code=target_code,
        mode=current_mode
    )

    worker_signals.progress.connect(progress.setValue)

    worker_signals.item_updated.connect(main_window._handle_batch_item_updated)

    worker_signals.error_occurred.connect(main_window._handle_batch_translate_error)
    worker_signals.variables_warning.connect(main_window._handle_batch_translate_warning)

    worker_signals.finished.connect(main_window._handle_batch_translate_finished)
    worker_signals.finished.connect(progress.close) 

    worker_signals.request_mark_modified.connect(main_window._mark_tab_modified_from_worker)

    progress.canceled.connect(worker.cancel)

    main_window._clear_batch_results()

    QThreadPool.globalInstance().start(worker)

    main_window.statusBar().showMessage(tr("batch_starting"), 0) 

    items_copy = [replace(item) for item in current_items] 
    lines_copy = list(current_file_lines) 

    worker_signals = WorkerSignals()
    worker = BatchTranslateWorker(
        signals=worker_signals,
        selected_indices=selected_rows_indices,
        items_data_copy=items_copy, 
        lines_copy=lines_copy, 
        source_code=source_code,
        target_code=target_code,
        mode=current_mode
    )

    worker_signals.progress.connect(progress.setValue)

    worker_signals.item_updated.connect(main_window._handle_batch_item_updated)

    worker_signals.error_occurred.connect(main_window._handle_batch_translate_error)
    worker_signals.variables_warning.connect(main_window._handle_batch_translate_warning)

    worker_signals.finished.connect(main_window._handle_batch_translate_finished)
    worker_signals.finished.connect(progress.close) 

    worker_signals.request_mark_modified.connect(main_window._mark_tab_modified_from_worker)

    progress.canceled.connect(worker.cancel)

    main_window._clear_batch_results()

    QThreadPool.globalInstance().start(worker)

    progress.show()
    main_window.statusBar().showMessage(tr("batch_starting"), 0) 

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

def handle_find_next(main_window):
    current_file_data = main_window._get_current_file_data()
    current_table = main_window._get_current_table()
    search_text = main_window.search_input.text() if main_window.search_input else ""
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 

    if not current_file_data or not current_table or not search_text:
        main_window.statusBar().showMessage(tr("search_enter_text_error"), 3000)
        return

    if use_regex:
        try:
            re.compile(search_text)
        except re.error as e:
            main_window.statusBar().showMessage(tr("search_regex_error", error=e), 5000)
            return

    current_items = current_file_data.get('items')
    current_mode = current_file_data.get('mode')
    start_index = main_window._get_current_item_index()

    if not current_items or not current_mode:
        main_window.statusBar().showMessage(tr("search_no_data"), 3000)
        return

    num_items = len(current_items)
    found_item_index = -1

    for i in range(start_index + 1, num_items):

        if table_manager.find_text_in_item(current_items[i], search_text, current_mode, use_regex=use_regex):
            found_item_index = i
            break
    else: 
        for i in range(start_index + 1):

            if table_manager.find_text_in_item(current_items[i], search_text, current_mode, use_regex=use_regex):
                found_item_index = i
                main_window.statusBar().showMessage(tr("search_restarted", text=search_text), 2000)
                break

    if found_item_index != -1:
        current_table.selectRow(found_item_index)
        current_table.scrollToItem(current_table.item(found_item_index, 0), QAbstractItemView.ScrollHint.PositionAtCenter)

        search_mode_str = "(Regex) " if use_regex else ""
        main_window.statusBar().showMessage(f"{search_mode_str}{tr('search_found', text=search_text, line=found_item_index + 1)}", 3000)
    else:
        search_mode_str = "(Regex) " if use_regex else ""
        main_window.statusBar().showMessage(f"{search_mode_str}{tr('search_not_found', text=search_text)}", 3000)

def handle_replace(main_window):
    current_file_data = main_window._get_current_file_data()
    current_table = main_window._get_current_table()
    search_text = main_window.search_input.text() if main_window.search_input else ""
    replace_text = main_window.replace_input.text() if main_window.replace_input else ""
    item_index = main_window._get_current_item_index() 
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 

    if not current_file_data or not current_table or not search_text or item_index < 0:
        main_window.statusBar().showMessage(tr("replace_enter_text_error"), 3000)
        return

    if use_regex:
        try:
            re.compile(search_text)

        except re.error as e:
            main_window.statusBar().showMessage(f"Search Regex Error: {e}", 5000)
            return

    current_items = current_file_data.get('items')
    current_mode = current_file_data.get('mode')
    current_lines = current_file_data.get('lines') 

    if not current_items or not current_mode or not (0 <= item_index < len(current_items)):
        main_window.statusBar().showMessage(tr("replace_data_error"), 3000)
        return

    item_data = current_items[item_index] 
    text_key = 'translated_text' if current_mode == "translate" else 'current_text'
    original_cell_text = item_data.get(text_key, '')

    match_found = table_manager.find_text_in_item(item_data, search_text, current_mode, use_regex=use_regex)

    if match_found:

        try:

            pattern_to_use = search_text if use_regex else re.escape(search_text)
            new_cell_text, num_subs = re.subn(pattern_to_use, replace_text, original_cell_text, count=1, flags=re.IGNORECASE)

            if num_subs > 0:

                if 'initial_text' not in item_data: 
                    item_data['initial_text'] = original_cell_text
                item_data[text_key] = new_cell_text
                item_data['is_modified_session'] = True

                editable_col_index = 4 
                table_manager.update_table_item_text(main_window, current_table, item_index, editable_col_index, new_cell_text)
                table_manager.update_table_row_style(current_table, item_index, item_data)

                if current_mode == "translate":
                    line_idx = item_data.get('translated_line_index')

                    parsed_data_for_format = item_data.get('parsed_data')
                    if line_idx is not None and parsed_data_for_format is not None and current_lines and 0 <= line_idx < len(current_lines):

                        new_line = parser.format_line_from_components(item_data, new_cell_text)
                        if new_line is not None:
                            current_lines[line_idx] = new_line
                        else:
                            logger.warning(f"Could not format line {line_idx} after replace.")
                            QMessageBox.warning(main_window, tr("replace_format_error_title"),
                                                tr("replace_format_error_msg", line=line_idx+1))

                    else:
                        logger.warning(f"Could not update line {line_idx} after replace (missing index or parsed_data).")

                main_window._set_current_tab_modified(True)
                main_window.statusBar().showMessage(tr("replace_success_finding_next", line=item_index + 1), 2000)

                handle_find_next(main_window)

            else:

                main_window.statusBar().showMessage(tr("replace_failed"), 3000)

        except re.error as e:

             main_window.statusBar().showMessage(tr("replace_regex_error", error=e), 4000)
             logger.error(f"Regex error during replace: {e}")

    else:

        search_mode_str = "(Regex) " if use_regex else "" 
        main_window.statusBar().showMessage(f"{search_mode_str}{tr('replace_no_match')}", 2000)
        handle_find_next(main_window)

def handle_replace_all(main_window):
    current_file_data = main_window._get_current_file_data()
    current_table = main_window._get_current_table()
    search_text = main_window.search_input.text() if main_window.search_input else ""
    replace_text = main_window.replace_input.text() if main_window.replace_input else ""
    use_regex = main_window.regex_checkbox.isChecked() if main_window.regex_checkbox else False 

    if not current_file_data or not current_table or not search_text:
        main_window.statusBar().showMessage(tr("replace_all_enter_text_error"), 3000)
        return

    if use_regex:
        try:
            re.compile(search_text)

        except re.error as e:
            main_window.statusBar().showMessage(f"Search Regex Error: {e}", 5000)
            return

    current_items = current_file_data.get('items')
    current_mode = current_file_data.get('mode')
    current_lines = current_file_data.get('lines') 

    if not current_items or not current_mode:
        main_window.statusBar().showMessage(tr("replace_all_no_data"), 3000)
        return

    total_replace_count = 0 
    items_changed_count = 0 
    errors = []

    search_mode_str = "(Regex) " if use_regex else ""
    reply = QMessageBox.question(main_window, tr("replace_all_title"),
                                 tr("replace_all_confirm_msg", search_mode=search_mode_str, search=search_text, replace=replace_text),
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        main_window.statusBar().showMessage(tr("replace_all_canceled"), 3000)
        return

    main_window.statusBar().showMessage(tr("replace_all_starting"), 0)
    QApplication.processEvents() 

    for i, item_data in enumerate(current_items):
        text_key = 'translated_text' if current_mode == "translate" else 'current_text'
        original_cell_text = item_data.get(text_key, '')
        item_replace_count = 0 

        if not table_manager.find_text_in_item(item_data, search_text, current_mode, use_regex=use_regex):
            continue 

        new_cell_text = original_cell_text
        try:

            pattern_to_use = search_text if use_regex else re.escape(search_text)
            new_cell_text, num_subs = re.subn(pattern_to_use, replace_text, original_cell_text, flags=re.IGNORECASE)
            item_replace_count = num_subs
        except re.error as e:
            errors.append(tr("replace_all_regex_error", line=i+1, error=e)) 
            continue 

        if item_replace_count > 0:
            total_replace_count += item_replace_count
            items_changed_count += 1

            if 'initial_text' not in item_data: 
                item_data['initial_text'] = original_cell_text
            item_data[text_key] = new_cell_text
            item_data['is_modified_session'] = True

            editable_col_index = 4 
            table_manager.update_table_item_text(main_window, current_table, i, editable_col_index, new_cell_text)
            table_manager.update_table_row_style(current_table, i, item_data)

            if current_mode == "translate":
                line_idx = item_data.get('translated_line_index')

                parsed_data_for_format = item_data.get('parsed_data')
                if line_idx is not None and parsed_data_for_format is not None and current_lines and 0 <= line_idx < len(current_lines):

                    new_line = parser.format_line_from_components(item_data, new_cell_text)
                    if new_line is not None:
                        current_lines[line_idx] = new_line
                    else:
                        errors.append(tr("replace_all_format_error", line=i+1, file_line=line_idx+1))
                else:
                    errors.append(tr("replace_all_update_error", line=i+1))

    if items_changed_count > 0: 
        main_window._set_current_tab_modified(True)

    result_message = tr("replace_all_finished", count=total_replace_count, lines=items_changed_count)
    if errors:
        result_message += f" {tr('replace_all_errors', count=len(errors))}."
        QMessageBox.warning(main_window, tr("replace_all_error_title"),
                            tr("replace_all_error_msg_header") + "\n- " + "\n- ".join(errors[:10]) + ("\n..." if len(errors)>10 else ""))

    main_window.statusBar().showMessage(result_message, 5000)