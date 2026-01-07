# -*- coding: utf-8 -*-
"""
RenForge GUI File Manager

DEPRECATED: This module contains legacy file management functions.
File operations are being migrated to controllers.FileController.
This module is kept for backward compatibility during the migration period.

For new code, use:
    from controllers import FileController
    controller.open_file(path, mode)
    controller.save_file()
"""

import os
import sys
import time

from renforge_logger import get_logger
logger = get_logger("gui.file_manager")

try:

    from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
    from PyQt6.QtCore import Qt
except ImportError:

    logger.critical("PyQt6 is required for file operations but not found.")

    sys.exit(1)

try:
    from utils import project_utils 
except ImportError:
    logger.error("utils.project_utils modülü yüklenemedi. Proje hazırlama özellikleri kullanılamayacak.")
    project_utils = None 

import renforge_config as config
import renforge_core as core
import renforge_ai as ai
from renforge_exceptions import SaveError
from locales import tr
from renforge_models import TabData, ParsedItem
from renforge_enums import FileMode, ContextType, ItemType

from gui.renforge_gui_dialog import ModeSelectionDialog
import gui.gui_tab_manager as tab_manager
import gui.gui_table_manager as table_manager
import gui.gui_settings_manager as settings_manager

def open_project_dialog(main_window):
    start_dir = main_window.last_open_project_directory or \
                (os.path.dirname(main_window.current_project_path) if main_window.current_project_path else os.getcwd())

    project_path = QFileDialog.getExistingDirectory(
        main_window,
        "Open Ren'Py Project Folder",
        start_dir
    )

    if project_path:

        game_folder = os.path.join(project_path, 'game')
        if not os.path.isdir(game_folder):
            reply = QMessageBox.question(main_window, "Project Folder?",
                                         f"The folder '{os.path.basename(project_path)}' does not contain a 'game' subfolder.\n"
                                         "Is this definitely a Ren'Py project folder?\n\n"
                                         "Open it in the project panel anyway?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                main_window.statusBar().showMessage(tr("project_opening_cancelled"), 3000)
                return

        logger.debug(f"Project folder selected: {project_path}")
        main_window.last_open_project_directory = project_path 

        prep_results = None
        if project_utils:
            current_settings = main_window.settings

            if current_settings.get("auto_prepare_project", config.DEFAULT_AUTO_PREPARE_PROJECT):
                 main_window.statusBar().showMessage(tr("preparing_project"), 0)
                 QApplication.processEvents()
                 start_time = time.time()
                 try:
                      prep_results = project_utils.prepare_project_files(project_path, current_settings) 
                 except Exception as e:
                      logger.critical(f"Exception during prepare_project_files call: {e}")
                      QMessageBox.critical(main_window, "Project Preparation Error",
                                           f"An unexpected error occurred while preparing project files:\n{e}")
                      prep_results = {"error": str(e)}

                 end_time = time.time()
                 duration = end_time - start_time
                 logger.debug(f"File preparation took {duration:.2f} seconds.")

            if prep_results and "error" not in prep_results and not prep_results.get("preparation_skipped_by_setting"):
                 summary_lines = [f"File preparation finished ({duration:.1f}s):"]
                 has_issues = False
                 if prep_results["rpa_processed"] or prep_results["rpa_skipped"] or prep_results["rpa_errors"]:
                     summary_lines.append(f"  RPA: Unpacked={prep_results['rpa_processed']}, Skipped={prep_results['rpa_skipped']}, Errors={prep_results['rpa_errors']}")
                     if prep_results["rpa_errors"]:
                         has_issues = True
                         if not prep_results["unrpa_available"]:
                              summary_lines.append("    - Error reason: 'unrpa' library not found/unavailable.")
                         elif prep_results["rpa_error_details"]:
                              summary_lines.append("    - RPA Error Details (max 3):")
                              summary_lines.extend([f"      - {detail}" for detail in prep_results["rpa_error_details"][:3]])
                              if len(prep_results["rpa_error_details"]) > 3: summary_lines.append("        ...")

                 if prep_results["rpyc_processed"] or prep_results["rpyc_skipped"] or prep_results["rpyc_errors"]:
                     summary_lines.append(f"  RPYC: Decompiled={prep_results['rpyc_processed']}, Skipped={prep_results['rpyc_skipped']}, Errors={prep_results['rpyc_errors']}")
                     if prep_results["rpyc_errors"]:
                         has_issues = True
                         if not prep_results["unrpyc_available"]:
                              summary_lines.append(f"    - Error reason: script '{project_utils.UNRPYC_SCRIPT_PATH.name}' not found.")
                         elif prep_results["rpyc_error_details"]:
                              summary_lines.append("    - RPYC Error Details (max 3):")
                              summary_lines.extend([f"      - {detail}" for detail in prep_results["rpyc_error_details"][:3]])
                              if len(prep_results["rpyc_error_details"]) > 3: summary_lines.append("        ...")

                 if has_issues:
                     QMessageBox.warning(main_window, "Project Preparation Results", "\n".join(summary_lines))
                     main_window.statusBar().showMessage(tr("project_prep_errors"), 5000)
                 elif prep_results["rpa_processed"] > 0 or prep_results["rpyc_processed"] > 0:

                     QMessageBox.information(main_window, "Project Preparation", "\n".join(summary_lines))
                     main_window.statusBar().showMessage(tr("project_prep_success"), 5000)

            elif prep_results and prep_results.get("preparation_skipped_by_setting"):
                     main_window.statusBar().showMessage(tr("project_prep_skipped"), 4000)
            elif prep_results and "error" in prep_results:
                     main_window.statusBar().showMessage(f"Error during project file preparation: {prep_results['error']}", 6000)

            else:

                main_window.statusBar().showMessage(tr("auto_prep_disabled"), 4000)
                logger.info("Call to project_utils.prepare_project_files skipped due to settings.")

        else:
             logger.warning("Module project_utils not loaded, skipping project file preparation.")

        main_window._populate_project_tree(project_path)
        main_window.statusBar().showMessage(tr("project_opened", name=os.path.basename(project_path)), 5000)
    else:
        main_window.statusBar().showMessage(tr("project_opening_cancelled"), 3000)

def open_file_dialog(main_window):
    start_dir = main_window.last_open_directory if main_window.last_open_directory and os.path.isdir(main_window.last_open_directory) \
                else (os.path.dirname(main_window.current_file_path) if main_window.current_file_path else os.getcwd())

    file_dialog = QFileDialog(main_window, "Open Ren'Py Script(s)", start_dir)
    file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
    file_dialog.setNameFilter("RPY files (*.rpy);;All Files (*)") 

    if file_dialog.exec():
        file_paths = file_dialog.selectedFiles()
        if not file_paths:
            return 

        if file_paths:
            main_window.last_open_directory = os.path.dirname(file_paths[0])

        if not settings_manager.ensure_mode_setting_chosen(main_window):
            main_window.statusBar().showMessage(tr("file_opening_cancelled_mode"), 5000)
            return

        loaded_count = 0
        already_open_files = []

        for file_path in file_paths:

            is_open = False
            for i in range(main_window.tab_widget.count()):
                tab_path = main_window.tab_data.get(i)
                if tab_path == file_path:
                    main_window.tab_widget.setCurrentIndex(i) 
                    is_open = True
                    already_open_files.append(os.path.basename(file_path))
                    break
            if is_open:
                continue 

            final_mode = determine_file_mode(main_window, file_path)
            if final_mode:
                if load_file(main_window, file_path, final_mode):
                    loaded_count += 1

        status_messages = []
        if loaded_count > 0:
            status_messages.append(f"Loaded {loaded_count} file(s).")
        if already_open_files:
             status_messages.append(f"File(s) already open: {', '.join(already_open_files)}.")
        if not status_messages and file_paths: 
             status_messages.append("File loading cancelled.")
        elif not file_paths:
            status_messages.append("No files selected.")

        main_window.statusBar().showMessage(" ".join(status_messages), 5000)

def determine_file_mode(main_window, file_path):
    current_selection_method = main_window.settings.get("mode_selection_method", config.DEFAULT_MODE_SELECTION_METHOD)
    final_mode = None
    detected_mode = "direct" 

    try:
        detected_mode = core.detect_file_mode(file_path)
        logger.debug(f"Auto-detected mode for {os.path.basename(file_path)}: {detected_mode}")
    except Exception as detect_err:
        logger.error(f"Error detecting mode for {file_path}: {detect_err}")
        QMessageBox.warning(main_window, "Mode Detection Error",
                            f"Could not automatically detect mode for file:\n{os.path.basename(file_path)}\n"
                            f"Error: {detect_err}\n\n"
                            "Please select the mode manually.")

    if current_selection_method == "manual":
        mode_dialog = ModeSelectionDialog(main_window, detected_mode, file_path)
        if mode_dialog.exec():
            final_mode = mode_dialog.get_selected_mode()

    else: 
        final_mode = detected_mode 

    if final_mode:
        logger.debug(f"Selected mode for {os.path.basename(file_path)}: {final_mode}")
    else:
        logger.debug(f"Mode selection cancelled for {os.path.basename(file_path)}")

    return final_mode

def load_file(main_window, file_path, selected_mode):
    try:
        base_name = os.path.basename(file_path)
        main_window.statusBar().showMessage(tr("loading_file", name=base_name, mode=selected_mode), 0)
        QApplication.processEvents()

        new_table = table_manager.create_table_widget(main_window)
        new_table.setProperty("filePath", file_path) 

        items, lines, breakpoints, detected_lang_from_file = None, None, None, None
        current_target_lang = main_window.target_lang_combo.currentData()
        current_source_lang = main_window.source_lang_combo.currentData()
        model_name = main_window.model_combo.currentText()

        available_languages_map = main_window.SUPPORTED_LANGUAGES
        lang_name_to_code_map = {name.lower(): code for code, name in available_languages_map.items()}

        if selected_mode == "translate":
            items, lines, breakpoints, detected_lang_from_file = core.load_and_parse_translate_file(file_path)
            if detected_lang_from_file:
                 logger.debug(f"'translate' block language detected as: {detected_lang_from_file}")
                 final_target_lang = detected_lang_from_file
                 detected_code = lang_name_to_code_map.get(detected_lang_from_file.lower())
                 if detected_code:
                     final_target_lang = detected_code 
                     logger.debug(f"Mapped detected language to code: '{detected_code}'")
                 else:
                     # Allow custom language codes defined in Ren'Py
                     final_target_lang = detected_lang_from_file
                     logger.info(f"Using detected custom language code: '{detected_lang_from_file}'")
            else:
                 logger.debug(f"'translate' block language not detected, using current: {current_target_lang}")
                 final_target_lang = current_target_lang
        else: 
            items, lines, breakpoints = core.load_and_parse_direct_file(file_path)
            final_target_lang = current_target_lang 

        if lines is None or items is None or breakpoints is None:
            raise Exception(f"Core parsing function failed for '{base_name}'. See console.")

        # Create TabData object
        tab_data = TabData(
            file_path=file_path,
            mode=FileMode(selected_mode),
            lines=lines,
            items=items,
            breakpoints=breakpoints,
            output_path=file_path,
            target_language=final_target_lang,
            source_language=current_source_lang,
            selected_model=model_name
        )
        # Dynamically attach table_widget (GUI element) to data object
        setattr(tab_data, 'table_widget', new_table)
        # Python dataclasses allow dynamic attribute assignment if not frozen.
        
        tab_data.table_widget = new_table # Dynamic assignment for now, or I update the class.
        
        main_window.file_data[file_path] = tab_data

        table_manager.populate_table(new_table, items, selected_mode)

        tab_manager.add_new_tab(main_window, file_path, new_table, base_name)

        if not items:
            logger.warning(f"No items found in file {base_name} (Mode: {selected_mode})")
            if selected_mode == "translate":
                QMessageBox.warning(main_window, tr("warning_empty_translate_mode_title"), tr("warning_empty_translate_mode_msg"))
            else:
                QMessageBox.warning(main_window, "Empty File", f"No items found in '{base_name}' with mode '{selected_mode}'.")
        
        # Notify new architecture (Phase 5 Sync)
        if hasattr(main_window, 'file_loaded'):
            main_window.file_loaded.emit(file_path)

        item_count = len(items)
        main_window.statusBar().showMessage(tr("file_loaded", name=base_name, count=item_count, mode=selected_mode), 5000)

        return True

    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(main_window, "Load Error", f"Failed to load file:\n{file_path}\n\nError: {e}")
        
        # Original cleanup logic from the old except block
        if file_path in main_window.file_data:
            del main_window.file_data[file_path]

        for i in range(main_window.tab_widget.count()):
             widget = main_window.tab_widget.widget(i)
             if widget and widget.property("filePath") == file_path:
                  logger.debug(f"Attempting to remove potentially failed tab for {file_path}")
                  main_window.tab_widget.removeTab(i)

                  tab_manager.rebuild_tab_data(main_window)
                  break

        main_window._update_ui_state()
        main_window._display_current_item_status()
        return False

def save_changes(main_window):
    current_data = main_window._get_current_file_data()
    if not current_data:
        main_window.statusBar().showMessage(tr("no_active_tab_save"), 3000)
        return False

    # current_data is now TabData object
    file_path_to_save = current_data.output_path
    if not file_path_to_save:

        QMessageBox.warning(main_window, "Save Error", "Could not determine save path. Try 'Save As...'.")
        return save_file_dialog(main_window) 

    current_file_lines = current_data.lines
    current_items_list = current_data.items
    current_breakpoints = current_data.breakpoints
    current_table = getattr(current_data, 'table_widget', None) # Safely get dynamically added attr
    current_mode = current_data.mode

    if current_file_lines is None or current_items_list is None or current_breakpoints is None or current_mode is None:
        QMessageBox.critical(main_window, "Data Error", "Internal error: missing data for saving the file.")
        return False

    success = False
    base_name = os.path.basename(file_path_to_save)
    try:
        main_window.statusBar().showMessage(tr("saving_file", name=base_name), 0)
        QApplication.processEvents()

        if current_mode == "translate":
            core.save_translate_file(file_path_to_save, current_file_lines, current_breakpoints)
        else: 
            core.save_direct_file(file_path_to_save, current_items_list, current_file_lines, current_breakpoints)

        # If we reached here, save was successful (otherwise SaveError would be raised)

        current_data.is_modified = False
        
        # text_key logic
        for item in current_items_list:
            item.is_modified_session = False
            item.initial_text = item.current_text

        if current_table:
                table_manager.update_all_row_styles(current_table, current_items_list) 

        main_window._set_current_tab_modified(False) 

        main_window.statusBar().showMessage(tr("file_saved", path=file_path_to_save), 5000)
        return True

    except SaveError as e:
        logger.error(f"SaveError for {base_name}: {e}")
        main_window.statusBar().showMessage(f"Error saving {base_name}: {e.message}", 10000)
        QMessageBox.critical(main_window, "Save Error",
                            f"Failed to save file:\n{file_path_to_save}\n\nError: {e.message}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error saving {base_name}: {e}")
        main_window.statusBar().showMessage(f"Unexpected error saving {base_name}: {e}", 10000)
        QMessageBox.critical(main_window, "Save Error",
                            f"Failed to save file (Unexpected):\n{file_path_to_save}\n\nError: {e}")
        return False

def save_file_dialog(main_window):
    current_data = main_window._get_current_file_data()
    if not current_data:
        main_window.statusBar().showMessage("No active tab for 'Save As...'.", 3000)
        return False

    start_path = current_data.output_path or main_window.current_file_path or os.getcwd()
    start_dir = os.path.dirname(start_path)
    start_name = os.path.basename(start_path)

    file_path, _ = QFileDialog.getSaveFileName(main_window, "Save File As", os.path.join(start_dir, start_name),
                                                 "Ren'Py Scripts (*.rpy);;All Files (*)")

    if not file_path:
        main_window.statusBar().showMessage("Saving cancelled.", 3000)
        return False

    current_data.output_path = file_path

    return save_changes(main_window)

def save_all_files(main_window):
    current_tab_index = main_window.tab_widget.currentIndex()
    saved_successfully = True
    failed_files = []
    modified_files_found = False

    indices_to_save = []
    for i in range(main_window.tab_widget.count()):
        file_path = main_window.tab_data.get(i)
        if file_path:
             data = main_window.file_data.get(file_path)
             if data and data.is_modified:
                 indices_to_save.append(i)
                 modified_files_found = True

    if not modified_files_found:

         return True 

    main_window.statusBar().showMessage("Saving all modified files...", 0)
    QApplication.processEvents()

    for i in indices_to_save:

        main_window.tab_widget.setCurrentIndex(i) 

        QApplication.processEvents()

        file_path_to_save = main_window.tab_data.get(i)
        if not file_path_to_save: 
            logger.error(f"Could not get file path for tab index {i} during Save All.")
            failed_files.append(f"(Sekme {i} için yol hatası)")
            saved_successfully = False
            continue

        if not save_changes(main_window): 
            saved_successfully = False

            data = main_window.file_data.get(file_path_to_save)
            failed_name = os.path.basename(data.output_path if data else file_path_to_save)
            failed_files.append(failed_name)

    if 0 <= current_tab_index < main_window.tab_widget.count():

        main_window.tab_widget.setCurrentIndex(current_tab_index)
    elif main_window.tab_widget.count() > 0:
        main_window.tab_widget.setCurrentIndex(0) 

    if not saved_successfully:
        QMessageBox.warning(main_window, "Save Error",
                          "Failed to save one or more files:\n- " + "\n- ".join(failed_files))
        main_window.statusBar().showMessage("Saving finished with errors.", 5000)

    elif modified_files_found: 
        main_window.statusBar().showMessage(tr("all_files_saved"), 4000)

    main_window._update_ui_state()
    main_window._display_current_item_status()

    return saved_successfully