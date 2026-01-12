# -*- coding: utf-8 -*-
"""
RenForge Application Bootstrap (Composition Root)

This module serves as the composition root for the application.
It creates and wires all the main components:
- DI Container registrations
- Controllers and Models
- View (RenForgeGUI)
- Signal connections between View and Controllers
"""

from typing import Tuple

from renforge_logger import get_logger
import renforge_ai as ai
from interfaces.di_container import DIContainer, Lifetime
from interfaces.i_controller import (
    IAppController, IFileController, ITranslationController,
    IBatchController, IProjectController
)
from interfaces.i_view import IMainView
from models.settings_model import SettingsModel
from models.project_model import ProjectModel
from controllers.app_controller import AppController
from controllers.file_controller import FileController
from controllers.translation_controller import TranslationController
from controllers.batch_controller import BatchController
from controllers.project_controller import ProjectController

logger = get_logger("bootstrap")


def bootstrap() -> Tuple[AppController, 'RenForgeGUI']:
    """
    Bootstrap the application by creating and wiring all components.
    
    This is the composition root - the single place where all dependencies
    are resolved and connected.
    
    Returns:
        Tuple of (AppController, RenForgeGUI view instance)
    """
    logger.info("=== RenForge Bootstrap Starting ===")
    
    # Get or create the DI container
    container = DIContainer.instance()
    container.clear()  # Start fresh
    
    # Stage 7: Initialize Plugin System
    from core.plugin_manager import PluginManager
    plugin_manager = PluginManager()
    plugin_manager.initialize()
    logger.info("Plugin System Initialized")
    
    # =========================================================================
    # REGISTER MODELS (Singletons)
    # =========================================================================
    logger.debug("Registering models...")
    
    # SettingsModel is already a singleton, register the instance
    settings = SettingsModel.instance()
    container.register_instance(SettingsModel, settings)
    logger.debug("  - Registered SettingsModel instance")
    
    # ProjectModel
    project = ProjectModel()
    container.register_instance(ProjectModel, project)
    logger.debug("  - Registered ProjectModel instance")
    
    # =========================================================================
    # REGISTER CONTROLLERS
    # =========================================================================
    logger.debug("Registering controllers...")
    
    # FileController with factory (needs project and settings)
    container.register_factory(
        IFileController,
        lambda c: FileController(
            c.resolve(ProjectModel),
            c.resolve(SettingsModel)
        ),
        Lifetime.SINGLETON
    )
    logger.debug("  - Registered IFileController -> FileController factory")
    
    # TranslationController with factory
    container.register_factory(
        ITranslationController,
        lambda c: TranslationController(c.resolve(SettingsModel)),
        Lifetime.SINGLETON
    )
    logger.debug("  - Registered ITranslationController -> TranslationController factory")
    
    # AppController with injected dependencies (no more DI bypass!)
    app_controller = AppController(
        file_controller=container.resolve(IFileController),
        translation_controller=container.resolve(ITranslationController),
        settings=container.resolve(SettingsModel),
        project=container.resolve(ProjectModel)
    )
    container.register_instance(IAppController, app_controller)
    logger.debug("  - Registered IAppController -> AppController with injected deps")
    
    # =========================================================================
    # CREATE VIEW (RenForgeGUI)
    # =========================================================================
    logger.debug("Creating view (RenForgeGUI)...")
    
    # Import here to avoid circular imports
    from gui.renforge_gui import RenForgeGUI
    
    view = RenForgeGUI()
    container.register_instance(IMainView, view)
    logger.debug("  - Created and registered RenForgeGUI as IMainView")
    
    # =========================================================================
    # REGISTER GUI CONTROLLERS (need view reference)
    # =========================================================================
    logger.debug("Registering GUI controllers...")
    
    # BatchController - for batch translation operations
    batch_controller = BatchController(view)
    container.register_instance(IBatchController, batch_controller)
    view.batch_controller = batch_controller  # Assign to view
    logger.debug("  - Registered IBatchController -> BatchController instance")
    
    # ProjectController - for project tree management
    project_controller = ProjectController(view)
    container.register_instance(IProjectController, project_controller)
    view.project_controller = project_controller  # Assign to view
    logger.debug("  - Registered IProjectController -> ProjectController instance")
    
    # =========================================================================
    # WIRE SIGNALS (View -> Controller, Controller -> View)
    # =========================================================================
    logger.debug("Wiring signals...")
    
    _wire_controller_to_view_signals(app_controller, view)
    _wire_view_to_controller_signals(view, app_controller)
    
    # =========================================================================
    # STORE CONTROLLER REFERENCE IN VIEW
    # =========================================================================
    view._app_controller = app_controller
    logger.debug("  - Stored AppController reference in view")
    
    logger.info("=== RenForge Bootstrap Complete ===")
    logger.info(f"  Registrations: {container.get_registrations()}")
    
    return app_controller, view


def _wire_controller_to_view_signals(controller: AppController, view: 'RenForgeGUI'):
    """
    Connect controller signals to view update methods.
    These handle controller -> view data flow.
    """
    logger.debug("  Wiring controller -> view signals...")
    
    # Status updates -> status bar
    controller.status_updated.connect(
        lambda msg: view.statusBar().showMessage(msg, 5000)
    )
    logger.debug("    - status_updated -> statusBar")
    
    # File opened -> trigger table refresh
    controller.file_controller.file_opened.connect(
        lambda parsed_file: _on_file_opened_from_controller(view, parsed_file)
    )
    logger.debug("    - file_opened -> view update")
    
    # File saved -> update tab title
    controller.file_controller.file_saved.connect(
        lambda path: view.statusBar().showMessage(f"Saved: {path}", 3000)
    )
    logger.debug("    - file_saved -> statusBar")
    
    # File error -> error dialog
    controller.file_controller.file_error.connect(
        lambda msg: _show_error_from_controller(view, msg)
    )
    logger.debug("    - file_error -> error dialog")
    
    # Models loaded -> populate combo
    controller.models_loaded.connect(
        lambda models: _on_models_loaded(view, models)
    )
    logger.debug("    - models_loaded -> model_combo")
    
    # Languages loaded -> populate combos
    controller.languages_loaded.connect(
        lambda langs: _on_languages_loaded(view, langs)
    )
    logger.debug("    - languages_loaded -> lang_combos")


def _wire_view_to_controller_signals(view: 'RenForgeGUI', controller: AppController):
    """
    Connect view signals to controller methods.
    These handle view -> controller action flow.
    
    Note: The legacy GUI uses menu actions directly calling gui_file_manager etc.
    We're adding additional signal connections here for the new architecture,
    but keeping the legacy code paths working.
    """
    logger.debug("  Wiring view -> controller signals (adapter layer)...")
    
    # =========================================================================
    # FILE OPERATIONS - These are the ONLY handlers, no double-run
    # =========================================================================
    
    # Save - delegate to legacy file_manager (controller state not synced yet)
    view.save_requested.connect(
        lambda: _handle_save(view)
    )
    logger.debug("    - save_requested -> _handle_save")
    
    # Save All - delegate to legacy file_manager
    view.save_all_requested.connect(
        lambda: _handle_save_all(view)
    )
    logger.debug("    - save_all_requested -> _handle_save_all")
    
    # Close Tab - delegate to legacy tab_manager
    view.close_tab_requested.connect(
        lambda idx: _handle_close_tab(view, idx)
    )
    logger.debug("    - close_tab_requested -> _handle_close_tab")
    
    # Open File - delegate to legacy file_manager
    view.open_file_requested.connect(
        lambda: _handle_open_file(view)
    )
    logger.debug("    - open_file_requested -> _handle_open_file")
    
    # Open Project - delegate to legacy handler
    view.open_project_requested.connect(
        lambda: _handle_open_project(view)
    )
    logger.debug("    - open_project_requested -> _handle_open_project")
    
    # File Loaded signal no longer used by view directly
    logger.debug("    - (file_loaded signal deprecated)")
    
    # =========================================================================
    # TRANSLATION OPERATIONS
    # =========================================================================
    
    # AI Translate - delegate to legacy action_handler
    view.translate_ai_requested.connect(
        lambda: _handle_translate_ai(view)
    )
    logger.debug("    - translate_ai_requested -> _handle_translate_ai")
    
    # Google Translate - delegate to legacy action_handler
    view.translate_google_requested.connect(
        lambda: _handle_translate_google(view)
    )
    logger.debug("    - translate_google_requested -> _handle_translate_google")
    
    # Batch Google Translate - delegate to legacy action_handler
    view.batch_google_requested.connect(
        lambda: _handle_batch_google(view)
    )
    logger.debug("    - batch_google_requested -> _handle_batch_google")
    
    # Batch AI Translate - controller-first with background worker
    view.batch_ai_requested.connect(
        lambda: _handle_batch_ai(view)
    )
    logger.debug("    - batch_ai_requested -> _handle_batch_ai")
    
    # Settings changes - sync to settings model
    view.target_language_changed.connect(
        lambda code: _on_target_language_changed(controller, view, code)
    )
    logger.debug("    - target_language_changed -> settings sync")
    
    view.source_language_changed.connect(
        lambda code: _on_source_language_changed(controller, view, code)
    )
    logger.debug("    - source_language_changed -> settings sync")
    
    view.model_changed.connect(
        lambda model: _on_model_changed(controller, view, model)
    )
    logger.debug("    - model_changed -> settings sync")
    
    # Tab changes - notify controller
    view.tab_changed.connect(
        lambda idx: _on_tab_changed(controller, view, idx)
    )
    logger.debug("    - tab_changed -> controller notification")
    
    logger.debug("    - Legacy action handlers preserved")
    logger.debug("    - Controller available via view._app_controller")


def _on_file_opened_from_controller(view: 'RenForgeGUI', parsed_file):
    """
    Handle file opened signal from controller.
    
    Bu fonksiyon dosya açıldığında UI oluşturur.
    YENİ: Model-View mimarisi kullanılıyor - UI donması yok!
    
    PERFORMANS:
    - Eski: QTableWidget + 11,500 item oluşturma = UI donması
    - Yeni: QTableView + Model = Virtual scrolling, sadece ~30 satır render
    """
    logger.info(f"Controller opened file: {parsed_file.filename}, mode: {parsed_file.mode}")
    
    # Import legacy managers for UI creation
    import gui.gui_tab_manager as tab_manager
    
    # YENİ: Model-View mimarisi kullanıyoruz
    from gui.views import file_table_view
    
    # Check if file is already open
    file_path = str(parsed_file.file_path)
    if file_path in view.file_data:
        # File already open - just switch to its tab
        for idx in range(view.tab_widget.count()):
            if view.tab_data.get(idx) == file_path:
                view.tab_widget.setCurrentIndex(idx)
                logger.debug(f"  File already open, switched to tab {idx}")
                return
    
    # Directly store the ParsedFile
    view.file_data[file_path] = parsed_file
    view.current_file_path = file_path
    
    # =============================================
    # SYNC WITH PROJECT_MODEL (PR-3)
    # =============================================
    try:
        project_model = view._app_controller.project
        project_model.add_file(parsed_file)
        project_model.set_active_file(file_path)
        logger.debug(f"  Synced to project_model: {file_path}")
    except Exception as e:
        logger.warning(f"  Failed to sync to project_model: {e}")
    
    # =============================================
    # YENİ: MODEL-VIEW MİMARİSİ İLE TABLO OLUŞTUR
    # =============================================
    
    # Yeni TranslationTableView oluştur (QTableWidget yerine!)
    table_view = file_table_view.create_table_view(view)
    table_view.setProperty("filePath", file_path)
    
    # Veriyi modele yükle (populate_table yerine!)
    # Bu çağrı artık DONMA YAPMAZ çünkü:
    # 1. Model sadece list referansı tutuyor
    # 2. View sadece görünen satırları render ediyor
    file_table_view.load_data_to_view(table_view, parsed_file)
    
    # Add tab
    import os
    base_name = os.path.basename(file_path)
    tab_manager.add_new_tab(view, file_path, table_view, base_name)
    
    # Update UI state
    view._update_language_model_display()
    view._update_ui_state()
    
    logger.info(f"  File UI created successfully: {parsed_file.filename}")


def _on_target_language_changed(controller: AppController, view: 'RenForgeGUI', code: str):
    """Handle target language change from view."""
    logger.debug(f"Target language changed: {code}")
    view.target_language = code
    # Update current file data if exists
    current_file_data = view._get_current_file_data()
    if current_file_data:
        current_file_data.target_language = code


def _on_source_language_changed(controller: AppController, view: 'RenForgeGUI', code: str):
    """Handle source language change from view."""
    logger.debug(f"Source language changed: {code}")
    view.source_language = code
    # Update current file data if exists
    current_file_data = view._get_current_file_data()
    if current_file_data:
        current_file_data.source_language = code


def _on_model_changed(controller: AppController, view: 'RenForgeGUI', model: str):
    """Handle model change from view."""
    logger.debug(f"Model changed: {model}")
    view.selected_model = model if model != "None" else None
    
    # Sync with AI module
    if view.selected_model:
        success = ai.configure_gemini(view.selected_model)
        if not success:
            logger.warning(f"Failed to configure Gemini model {view.selected_model} on change")
    else:
        ai.gemini_model = None
    
    # Update current file data if exists
    current_file_data = view._get_current_file_data()
    if current_file_data:
        current_file_data.selected_model = model if model != "None" else None


def _on_tab_changed(controller: AppController, view: 'RenForgeGUI', idx: int):
    """Handle tab change from view."""
    logger.debug(f"Tab changed to index: {idx}")
    # Update current file path
    if idx >= 0 and idx in view.tab_data:
        file_path = view.tab_data[idx]
        view.current_file_path = file_path
        
        # SYNC WITH PROJECT_MODEL (PR-3)
        try:
            controller.project.set_active_file(file_path)
            logger.debug(f"  Synced active file to project_model: {file_path}")
        except Exception as e:
            logger.warning(f"  Failed to sync active file: {e}")


def _show_error_from_controller(view: 'RenForgeGUI', message: str):
    """Show error dialog from controller signal."""
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.critical(view, "Error", message)


def _on_models_loaded(view: 'RenForgeGUI', models: list):
    """Handle models loaded from controller."""
    logger.debug(f"Models loaded from controller: {len(models)} models")
    # The view already has _update_model_list, controller provides data
    # For Phase 4, we keep existing flow but log the connection


def _on_languages_loaded(view: 'RenForgeGUI', languages: dict):
    """Handle languages loaded from controller."""
    logger.debug(f"Languages loaded from controller: {len(languages)} languages")
    # Similar to models - view has its own loading, this is for future


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    return DIContainer.instance()


def get_app_controller() -> AppController:
    """Get the AppController from the container."""
    return DIContainer.instance().resolve(IAppController)


# =============================================================================
# FILE OPERATION HANDLERS - Called by signals from view
# =============================================================================

def _handle_save(view: 'RenForgeGUI'):
    """
    Handle save request from view signal.
    Delegates to legacy file_manager for actual save.
    """
    import gui.gui_file_manager as file_manager
    logger.debug("_handle_save called via signal")
    file_manager.save_changes(view)


def _handle_save_all(view: 'RenForgeGUI'):
    """
    Handle save all request from view signal.
    Delegates to legacy file_manager for actual save.
    """
    import gui.gui_file_manager as file_manager
    logger.debug("_handle_save_all called via signal")
    file_manager.save_all_files(view)


def _handle_close_tab(view: 'RenForgeGUI', idx: int):
    """
    Handle close tab request from view signal.
    Delegates to legacy tab_manager for actual close.
    """
    import gui.gui_tab_manager as tab_manager
    logger.debug(f"_handle_close_tab called via signal, idx={idx}")
    
    # Get file path before closing
    file_path = view.tab_data.get(idx)
    
    # Close tab via legacy manager
    tab_manager.close_current_tab(view)
    
    # SYNC WITH PROJECT_MODEL (PR-3)
    if file_path and view._app_controller:
        try:
            view._app_controller.project.close_file(file_path)
            logger.debug(f"  Synced close to project_model: {file_path}")
        except Exception as e:
            logger.warning(f"  Failed to sync close to project_model: {e}")


def _handle_open_file(view: 'RenForgeGUI'):
    """
    Handle open file request from view signal.
    Delegates to legacy file_manager for file dialog.
    """
    import gui.gui_file_manager as file_manager
    logger.debug("_handle_open_file called via signal")
    file_manager.open_file_dialog(view)


def _handle_open_project(view: 'RenForgeGUI'):
    """
    Handle open project request from view signal.
    Delegates to legacy handler in view.
    """
    logger.debug("_handle_open_project called via signal")
    view._handle_open_project()


def _handle_translate_ai(view: 'RenForgeGUI'):
    """
    Handle AI translate request from view signal.
    Delegates to legacy action_handler.
    """
    import gui.gui_action_handler as action_handler
    logger.debug("_handle_translate_ai called via signal")
    action_handler.edit_with_ai(view)


def _handle_translate_google(view: 'RenForgeGUI'):
    """
    Handle Google Translate request from view signal.
    Delegates to legacy action_handler.
    """
    import gui.gui_action_handler as action_handler
    logger.debug("_handle_translate_google called via signal")
    action_handler.translate_with_google(view)


def _handle_batch_google(view: 'RenForgeGUI'):
    """
    Handle Batch Google Translate request from view signal.
    Delegates to legacy action_handler.
    """
    import gui.gui_action_handler as action_handler
    logger.debug("_handle_batch_google called via signal")
    action_handler.batch_translate_google(view)


def _handle_batch_ai(view: 'RenForgeGUI'):
    """
    Handle Batch AI Translate request from view signal.
    Delegates to gui_action_handler.
    """
    import gui.gui_action_handler as action_handler
    logger.debug("_handle_batch_ai called via signal")
    action_handler.batch_translate_ai(view)



