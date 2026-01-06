import os
import sys

try:

    from PyQt6.QtWidgets import QMessageBox, QDialog
    from PyQt6.QtCore import QTimer 
except ImportError:
    print("CRITICAL ERROR: PyQt6 is required for settings management but not found.")
    sys.exit(1)

import renforge_config as config
import renforge_ai as ai 
from renforge_settings import load_settings, save_settings 

from gui.renforge_gui_dialog import ApiKeyDialog, SettingsDialog

def load_initial_settings(main_window):
    main_window.settings = load_settings() 

    main_window.settings.setdefault("mode_selection_method", config.DEFAULT_MODE_SELECTION_METHOD)
    main_window.settings.setdefault("api_key_set", bool(ai.load_api_key())) 

    print(f"Initial settings loaded: {main_window.settings}")

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
            print(f"Settings saved. Mode selection method: {new_mode_method}")
            main_window.statusBar().showMessage("Settings saved.", 4000)
            return True
    return False 

def show_api_key_dialog(main_window):
    dialog = ApiKeyDialog(main_window)
    dialog_result = dialog.exec()

    save_status_internal = dialog.get_save_status()

    print(f"ApiKeyDialog closed. Result: {dialog_result}, Internal Save Status: '{save_status_internal}'")

    if dialog_result == QDialog.DialogCode.Accepted:

        if save_status_internal == "saved":
            print("API key saved/updated (reported by dialog).")

            main_window.settings['api_key_set'] = True

            _reset_gemini_state(main_window, "API key saved/updated.")
            main_window._update_model_list(force_refresh=True)
            ensure_gemini_initialized(main_window)
            return True 
        elif save_status_internal == "removed":
            print("API key removed (reported by dialog).")

            main_window.settings['api_key_set'] = False

            _reset_gemini_state(main_window, "API key removed.")
            ai.no_ai = True
            main_window._update_ui_state()
            return True 
        elif save_status_internal == "unchanged":
            print("API key dialog closed (Accepted), key state unchanged.")
        elif save_status_internal == "error":
             print("API key dialog closed (Accepted), but reported an error during save/delete.")

        else:
             print(f"API key dialog closed (Accepted) with unexpected status: {save_status_internal}")

    elif dialog_result == QDialog.DialogCode.Rejected:
         print("API key dialog was cancelled.")

    return save_status_internal in ["saved", "removed"]

def handle_target_language_changed(main_window):
    new_lang_code = main_window.target_lang_combo.currentData()

    main_window.target_language = new_lang_code

    current_data = main_window._get_current_file_data()
    if current_data:
        if current_data.get('target_language') != new_lang_code:
            current_data['target_language'] = new_lang_code
            print(f"Target language for tab '{os.path.basename(main_window.current_file_path)}' set to: {new_lang_code}")

    else:

        pass

def handle_source_language_changed(main_window):
    new_lang_code = main_window.source_lang_combo.currentData()
    main_window.source_language = new_lang_code
    current_data = main_window._get_current_file_data()
    if current_data:
        if current_data.get('source_language') != new_lang_code:
            current_data['source_language'] = new_lang_code
            print(f"Source language for tab '{os.path.basename(main_window.current_file_path)}' set to: {new_lang_code}")

def handle_model_changed(main_window):
    new_model_text = main_window.model_combo.currentText()

    new_model = new_model_text if new_model_text != "None" else None 

    print(f"--- [handle_model_changed] Model changed signal. New text: '{new_model_text}', Value to store: '{new_model}' ---")

    if main_window.selected_model != new_model:
        main_window.selected_model = new_model
        print(f"  Updated main_window.selected_model to: {new_model}")

        if new_model:
            _reset_gemini_state(main_window, f"Model changed to {new_model}.")

        else:

            ai.no_ai = True
            ai.gemini_model = None
            main_window._update_ui_state()
            print("  AI marked as unavailable due to 'None' selection.")

    current_data = main_window._get_current_file_data()
    if current_data:
        if current_data.get('selected_model') != new_model:
            current_data['selected_model'] = new_model
            print(f"  Updated selected_model for tab '{os.path.basename(main_window.current_file_path)}' to: {new_model}")
    else:
         print("  No active tab data to update.")

def _reset_gemini_state(main_window, reason=""):

    if ai.gemini_model is not None:
        print(f"Resetting Gemini state. Reason: {reason}")
        ai.gemini_model = None 
        ai.no_ai = True 

        ai._available_models_cache = None
        print("Cleared Gemini model instance and marked AI as unavailable (will re-initialize on next use).")
        main_window._update_ui_state() 
    else:

        ai.no_ai = not bool(ai.load_api_key()) 
        main_window._update_ui_state()

def ensure_gemini_initialized(main_window, force_init=False):
    needs_init = ai.no_ai or ai.gemini_model is None
    print(f"--- [ensure_gemini_initialized] Called. Needs init (no_ai or model is None): {needs_init}, Force: {force_init} ---")

    initialization_performed = False
    initialization_succeeded = False

    if needs_init or force_init:
        print("--- [ensure_gemini_initialized] Checking internet before initialization attempt... ---")
        if not ai.is_internet_available(): 
             print("--- [ensure_gemini_initialized] Internet check failed. Skipping initialization. ---")
             ai.no_ai = True 
             ai.gemini_model = None 
             main_window.statusBar().showMessage("AI unavailable: no internet connection.", 5000)
             initialization_performed = True 
             initialization_succeeded = False
        else:

             print("--- [ensure_gemini_initialized] Internet check OK. Attempting initialization via _initialize_gemini... ---")
             initialization_succeeded = _initialize_gemini(main_window)
             initialization_performed = True
             print(f"--- [ensure_gemini_initialized] Initialization attempt result: {initialization_succeeded} ---")
    else:

         print("--- [ensure_gemini_initialized] AI already initialized. Skipping initialization call. ---")
         initialization_succeeded = True 

    if initialization_performed:
         print("--- [ensure_gemini_initialized] Updating model list after initialization attempt. ---")
         main_window._update_model_list() 

    QTimer.singleShot(50, main_window._sync_model_selection)

    main_window._update_ui_state()

    final_ai_available = not ai.no_ai
    print(f"--- [ensure_gemini_initialized] Finished. Final AI available status: {final_ai_available} ---")
    return final_ai_available

def _initialize_gemini(main_window):
    model_name = main_window.selected_model 
    api_key = ai.load_api_key()

    if not api_key:
        print("Gemini initialization check: API key missing.")
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
         print(f"Gemini initialization check: No model selected (value: {model_name}).")

         ai.no_ai = True 
         main_window._update_ui_state()
         main_window.statusBar().showMessage("AI unavailable: model not selected.", 5000)
         return False 

    try:
        print(f"Initializing Gemini with model: {model_name}")
        config_success = ai.configure_gemini(model_name) 

        if not config_success:

            main_window.statusBar().showMessage(f"Gemini initialization error ({model_name}). Check key/console.", 6000)

            print(f"--- _initialize_gemini returning False because configure_gemini failed for model {model_name} ---")
            return False 
        else:

            main_window.statusBar().showMessage(f"Gemini ({model_name}) initialized.", 3000)
            print(f"--- _initialize_gemini returning True for model {model_name} ---")

            return True 

    except Exception as e:

        print(f"CRITICAL ERROR during Gemini initialization: {e}")
        QMessageBox.critical(main_window, "Critical AI Error",
                           f"Unexpected error during Gemini initialization:\n{e}")
        ai.no_ai = True
        main_window._update_ui_state()
        main_window.statusBar().showMessage("Critical Gemini initialization error.", 5000)
        return False 