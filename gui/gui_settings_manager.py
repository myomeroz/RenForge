import os
import sys

from renforge_logger import get_logger
logger = get_logger("gui.settings_manager")

try:

    from PyQt6.QtWidgets import QMessageBox, QDialog
    from PyQt6.QtCore import QTimer 
except ImportError:
    logger.critical("PyQt6 is required for settings management but not found.")
    sys.exit(1)

import renforge_config as config
import renforge_ai as ai 
from renforge_settings import load_settings, save_settings 

from gui.renforge_gui_dialog import ApiKeyDialog, SettingsDialog

def load_initial_settings(main_window):
    main_window.settings = load_settings() 

    main_window.settings.setdefault("mode_selection_method", config.DEFAULT_MODE_SELECTION_METHOD)
    main_window.settings.setdefault("api_key_set", bool(ai.load_api_key())) 

    logger.debug(f"Initial settings loaded: {main_window.settings}")

def check_initial_mode_setting(main_window):
    _perform_initial_mode_check(main_window)

def _perform_initial_mode_check(main_window):
     current_method = main_window.settings.get("mode_selection_method")
     if current_method not in ["auto", "manual"]:
        QMessageBox.information(main_window, "Initial Setup",
                                "Welcome to RenForge!\n\n"
                                "Please choose how the program should determine the editing mode "
                                "for Ren'Py (*.rpy) files. "
                                "This setting can be changed later in Settings -> Main.",
                                QMessageBox.StandardButton.Ok)

        show_settings_dialog(main_window)

def ensure_mode_setting_chosen(main_window):
    main_window.settings = load_settings() 
    current_method = main_window.settings.get("mode_selection_method")

    if current_method not in ["auto", "manual"]:
        QMessageBox.information(main_window, "Mode Setting",
                                "Please select the method for determining file opening mode.",
                                QMessageBox.StandardButton.Ok)
        if show_settings_dialog(main_window): 

             main_window.settings = load_settings() 
             current_method = main_window.settings.get("mode_selection_method")
             return current_method in ["auto", "manual"]
        else:

             return False 
    return True 

def show_settings_dialog(main_window):
    dialog = SettingsDialog(main_window) 
    if dialog.exec() == QDialog.DialogCode.Accepted:

        new_mode_method = dialog.get_selected_mode_method()

        main_window.settings["mode_selection_method"] = new_mode_method
        if not save_settings(main_window.settings): 
            QMessageBox.warning(main_window, "Save Error", "Failed to save settings.")
            return False
        else:
            logger.debug(f"Settings saved. Mode selection method: {new_mode_method}")
            main_window.statusBar().showMessage("Settings saved.", 4000)
            return True
    return False 

def show_api_key_dialog(main_window):
    dialog = ApiKeyDialog(main_window)
    dialog_result = dialog.exec()

    save_status_internal = dialog.get_save_status()

    logger.debug(f"ApiKeyDialog closed. Result: {dialog_result}, Internal Save Status: '{save_status_internal}'")

    if dialog_result == QDialog.DialogCode.Accepted:

        if save_status_internal == "saved":
            logger.info("API key saved/updated (reported by dialog).")

            main_window.settings['api_key_set'] = True

            _reset_gemini_state(main_window, "API key saved/updated.")
            main_window._update_model_list(force_refresh=True)
            ensure_gemini_initialized(main_window)
            return True 
        elif save_status_internal == "removed":
            logger.info("API key removed (reported by dialog).")

            main_window.settings['api_key_set'] = False

            _reset_gemini_state(main_window, "API key removed.")
            ai.no_ai = True
            main_window._update_ui_state()
            return True 
        elif save_status_internal == "unchanged":
            logger.debug("API key dialog closed (Accepted), key state unchanged.")
        elif save_status_internal == "error":
             logger.error("API key dialog closed (Accepted), but reported an error during save/delete.")

        else:
             logger.warning(f"API key dialog closed (Accepted) with unexpected status: {save_status_internal}")

    elif dialog_result == QDialog.DialogCode.Rejected:
         logger.debug("API key dialog was cancelled.")

    return save_status_internal in ["saved", "removed"]

def handle_target_language_changed(main_window):
    new_lang_code = main_window.target_lang_combo.currentData()

    main_window.target_language = new_lang_code

    current_data = main_window._get_current_file_data()
    if current_data:
        if getattr(current_data, 'target_language', None) != new_lang_code:
            current_data.target_language = new_lang_code
            logger.debug(f"Target language for tab '{os.path.basename(main_window.current_file_path)}' set to: {new_lang_code}")

    else:

        pass

def handle_source_language_changed(main_window):
    new_lang_code = main_window.source_lang_combo.currentData()
    main_window.source_language = new_lang_code
    current_data = main_window._get_current_file_data()
    if current_data:
        if getattr(current_data, 'source_language', None) != new_lang_code:
            current_data.source_language = new_lang_code
            logger.debug(f"Source language for tab '{os.path.basename(main_window.current_file_path)}' set to: {new_lang_code}")

def handle_model_changed(main_window):
    new_model_text = main_window.model_combo.currentText()

    new_model = new_model_text if new_model_text != "None" else None 

    logger.debug(f"[handle_model_changed] Model changed signal. New text: '{new_model_text}', Value to store: '{new_model}'")

    if main_window.selected_model != new_model:
        main_window.selected_model = new_model
        logger.debug(f"Updated main_window.selected_model to: {new_model}")

        if new_model:
            _reset_gemini_state(main_window, f"Model changed to {new_model}.")

        else:

            ai.no_ai = True
            ai.gemini_model = None
            main_window._update_ui_state()
            logger.debug("AI marked as unavailable due to 'None' selection.")

    current_data = main_window._get_current_file_data()
    if current_data:
        # ParsedFile is an object, not a dict. Check attribute existence or use getattr.
        if getattr(current_data, 'selected_model', None) != new_model:
            current_data.selected_model = new_model
            logger.debug(f"Updated selected_model for tab '{os.path.basename(main_window.current_file_path)}' to: {new_model}")
    else:
         logger.debug("No active tab data to update.")

def _reset_gemini_state(main_window, reason=""):

    if ai.gemini_model is not None:
        logger.debug(f"Resetting Gemini state. Reason: {reason}")
        ai.gemini_model = None 
        ai.no_ai = True 

        ai._available_models_cache = None
        logger.debug("Cleared Gemini model instance and marked AI as unavailable.")
        main_window._update_ui_state() 
    else:

        ai.no_ai = not bool(ai.load_api_key()) 
        main_window._update_ui_state()

def ensure_gemini_initialized(main_window, force_init=False):
    needs_init = ai.no_ai or ai.gemini_model is None
    logger.debug(f"[ensure_gemini_initialized] Called. Needs init: {needs_init}, Force: {force_init}")

    initialization_performed = False
    initialization_succeeded = False

    if needs_init or force_init:
        logger.debug("[ensure_gemini_initialized] Checking internet before initialization...")
        if not ai.is_internet_available(): 
             logger.warning("[ensure_gemini_initialized] Internet check failed. Skipping initialization.")
             ai.no_ai = True 
             ai.gemini_model = None 
             main_window.statusBar().showMessage("AI unavailable: no internet connection.", 5000)
             initialization_performed = True 
             initialization_succeeded = False
        else:

             logger.debug("[ensure_gemini_initialized] Internet OK. Attempting initialization...")
             initialization_succeeded = _initialize_gemini(main_window)
             initialization_performed = True
             logger.debug(f"[ensure_gemini_initialized] Initialization result: {initialization_succeeded}")
    else:

         logger.debug("[ensure_gemini_initialized] AI already initialized. Skipping.")
         initialization_succeeded = True 

    if initialization_performed:
         logger.debug("[ensure_gemini_initialized] Updating model list after initialization.")
         main_window._update_model_list() 

    QTimer.singleShot(50, main_window._sync_model_selection)

    main_window._update_ui_state()

    final_ai_available = not ai.no_ai
    logger.debug(f"[ensure_gemini_initialized] Finished. AI available: {final_ai_available}")
    return final_ai_available

def _initialize_gemini(main_window):
    model_name = main_window.selected_model 
    api_key = ai.load_api_key()

    if not api_key:
        logger.warning("Gemini initialization check: API key missing.")
        main_window.settings['api_key_set'] = False 

        QMessageBox.warning(main_window, "API Key Missing",
                             "A Google Gemini API key is required to use AI features.\n"
                             "Please add the key via the Settings -> API Key menu.",
                             QMessageBox.StandardButton.Ok)

        if not api_key: 
             ai.no_ai = True
             main_window._update_ui_state()
             main_window.statusBar().showMessage("AI unavailable: API key not found.", 5000)
             return False 

    if not model_name:
         logger.warning(f"Gemini initialization check: No model selected (value: {model_name}).")

         ai.no_ai = True 
         main_window._update_ui_state()
         main_window.statusBar().showMessage("AI unavailable: model not selected.", 5000)
         return False 

    try:
        logger.info(f"Initializing Gemini with model: {model_name}")
        config_success = ai.configure_gemini(model_name) 

        if not config_success:

            main_window.statusBar().showMessage(f"Gemini initialization error ({model_name}). Check key/console.", 6000)

            logger.error(f"_initialize_gemini returning False because configure_gemini failed for model {model_name}")
            return False 
        else:

            main_window.statusBar().showMessage(f"Gemini ({model_name}) initialized.", 3000)
            logger.info(f"_initialize_gemini returning True for model {model_name}")

            return True 

    except Exception as e:

        logger.critical(f"CRITICAL ERROR during Gemini initialization: {e}")
        QMessageBox.critical(main_window, "Critical AI Error",
                           f"Unexpected error during Gemini initialization:\n{e}")
        ai.no_ai = True
        main_window._update_ui_state()
        main_window.statusBar().showMessage("Critical Gemini initialization error.", 5000)
        return False 