# -*- coding: utf-8 -*-
"""
RenForge Settings View

Extracted settings-related view logic from RenForgeGUI for cleaner separation.
These functions operate on a main_window instance passed as the first argument.
"""

from PyQt6.QtWidgets import QApplication

from renforge_logger import get_logger
logger = get_logger("gui.views.settings_view")

import renforge_ai as ai
import renforge_config as config


def sync_model_selection(main_window):
    """
    Sync model combo box selection with settings.
    
    Args:
        main_window: The RenForgeGUI instance
    """
    logger.debug("[sync_model_selection] Attempting to sync model selection...")
    current_selection = main_window.model_combo.currentText()
    if current_selection in ["Loading...", "Error loading models"]:
        logger.debug(f"[sync_model_selection] Skipping sync due to placeholder: '{current_selection}'")
        return
    
    default_model = main_window.settings.get("default_selected_model")

    if not default_model:
        logger.debug("[sync_model_selection] No default model set in settings. Skipping sync.")
        if main_window.selected_model != current_selection:
            logger.debug(f"[sync_model_selection] Updating selected_model to combo box value: '{current_selection}'")
            main_window.selected_model = current_selection if current_selection not in ["Loading...", "Error loading models", "Models not found", "None"] else None
        return

    if current_selection == default_model:
        logger.debug(f"[sync_model_selection] Default model '{default_model}' already selected. Sync not needed.")
        if main_window.selected_model != default_model:
            logger.debug(f"[sync_model_selection] Correcting selected_model to '{default_model}'")
            main_window.selected_model = default_model
        return

    model_index = main_window.model_combo.findText(default_model)

    if model_index != -1:
        logger.debug(f"[sync_model_selection] Found default model '{default_model}' at index {model_index}. Setting selection.")
        main_window.model_combo.blockSignals(True)
        main_window.model_combo.setCurrentIndex(model_index)
        main_window.selected_model = default_model
        main_window.model_combo.blockSignals(False)
        main_window._update_ui_state()
    else:
        logger.debug(f"[sync_model_selection] Default model '{default_model}' not found in the current list. Cannot sync. Current selection: '{current_selection}'.")
        if main_window.selected_model != current_selection:
            logger.debug(f"[sync_model_selection] Updating selected_model to combo box value: '{current_selection}'")
            main_window.selected_model = current_selection if current_selection not in ["Loading...", "Error loading models", "Models not found", "None"] else None


def load_languages(main_window):
    """
    Load supported languages from Google Translate API.
    
    Args:
        main_window: The RenForgeGUI instance
    """
    temp_languages = ai.get_google_languages()
    if temp_languages:
        main_window.SUPPORTED_LANGUAGES = temp_languages
        logger.debug(f"Loaded {len(main_window.SUPPORTED_LANGUAGES)} languages. Example: {list(main_window.SUPPORTED_LANGUAGES.items())[:5]}")
    else:
        logger.warning("Could not load supported languages for Google Translate.")
        main_window.SUPPORTED_LANGUAGES = {}


def update_model_list(main_window, force_refresh=False):
    """
    Update the model combo box with available Gemini models.
    
    Args:
        main_window: The RenForgeGUI instance
        force_refresh: If True, force refresh from API
    """
    logger.debug(f"[update_model_list] Called. Force refresh: {force_refresh}")

    previous_valid_selection = None
    if main_window.model_combo.count() > 0 and main_window.model_combo.currentIndex() >= 0:
        current_text = main_window.model_combo.currentText()
        if current_text not in ["Loading...", "Error loading models", "Models not found", "None"]:
            previous_valid_selection = current_text

    target_model_to_select = previous_valid_selection or main_window.selected_model
    if not target_model_to_select:
        target_model_to_select = main_window.settings.get("default_selected_model") or config.DEFAULT_MODEL_NAME

    if not target_model_to_select:
        target_model_to_select = "None"

    logger.debug(f"[update_model_list] Target model for selection: '{target_model_to_select}'")

    try:
        main_window.model_combo.blockSignals(True)
    except Exception as e:
        logger.warning(f"Could not block signals for model_combo: {e}")

    main_window.model_combo.setEnabled(False)
    main_window.model_combo.clear()
    main_window.model_combo.addItem("None")
    main_window.model_combo.addItem("Loading...")
    main_window.model_combo.setCurrentIndex(1)
    QApplication.processEvents()

    available_models = ai.get_available_models(force_refresh=force_refresh)

    main_window.model_combo.clear()
    main_window.model_combo.addItem("None")

    if available_models:
        logger.debug(f"[update_model_list] Populating combo box with {len(available_models)} models.")
        main_window.model_combo.addItems(available_models)

        selected_index = 0
        found_target = False

        if target_model_to_select and target_model_to_select != "None":
            exact_match_index = main_window.model_combo.findText(target_model_to_select)
            if exact_match_index != -1:
                selected_index = exact_match_index
                found_target = True
                logger.debug(f"[update_model_list] Found exact match for target model '{target_model_to_select}' at index {selected_index}.")
            else:
                logger.debug(f"[update_model_list] Exact match for '{target_model_to_select}' not found. Searching by suffix...")
                for i in range(1, main_window.model_combo.count()):
                    model_name_in_combo = main_window.model_combo.itemText(i)
                    if model_name_in_combo.endswith(target_model_to_select):
                        selected_index = i
                        target_model_to_select = model_name_in_combo
                        found_target = True
                        logger.debug(f"[update_model_list] Found model '{model_name_in_combo}' ending with target '{target_model_to_select}' at index {selected_index}.")
                        break

        if not found_target and target_model_to_select != "None":
            logger.debug(f"[update_model_list] Target model '{target_model_to_select}' not found. Checking config default '{config.DEFAULT_MODEL_NAME}'...")
            config_default_target = config.DEFAULT_MODEL_NAME
            config_default_index = main_window.model_combo.findText(config_default_target)
            if config_default_index != -1:
                selected_index = config_default_index
                target_model_to_select = config_default_target
                found_target = True
                logger.debug(f"[update_model_list] Found exact match for config default model '{config_default_target}'.")
            else:
                for i in range(1, main_window.model_combo.count()):
                    model_name_in_combo = main_window.model_combo.itemText(i)
                    if model_name_in_combo.endswith(config_default_target):
                        selected_index = i
                        target_model_to_select = model_name_in_combo
                        found_target = True
                        logger.debug(f"[update_model_list] Found config default model '{model_name_in_combo}' ending with '{config_default_target}'.")
                        break

        if not found_target and main_window.model_combo.count() > 1:
            selected_index = 1
            target_model_to_select = main_window.model_combo.itemText(selected_index)
            logger.debug(f"[update_model_list] Neither target nor config default found. Selecting first available: '{target_model_to_select}'.")

        main_window.model_combo.setCurrentIndex(selected_index)

        current_text_selection = main_window.model_combo.currentText()
        logger.debug(f"[update_model_list] Set combo box index to {selected_index} ('{current_text_selection}').")

        main_window.model_combo.setEnabled(True)
    else:
        logger.debug("[update_model_list] Failed to load models or no models available.")

        if main_window.model_combo.findText("Error loading models") == -1:
            main_window.model_combo.addItem("Error loading models")

        main_window.model_combo.setCurrentIndex(main_window.model_combo.findText("Error loading models"))
        main_window.model_combo.setEnabled(False)
        ai.no_ai = True

    try:
        main_window.model_combo.blockSignals(False)
    except Exception as e:
        logger.warning(f"Could not unblock signals for model_combo: {e}")

    main_window._update_ui_state()
