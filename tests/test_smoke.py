# -*- coding: utf-8 -*-
"""
Smoke Tests for RenForge

Verifies that critical application components initialize and interact correctly.
"""

import pytest
from pathlib import Path

def test_smoke_bootstrap_and_wiring(qtbot):
    """
    Smoke test: bootstrap + controller wiring.
    Verifies that the application starts up and controllers are wired to the view.
    """
    from app_bootstrap import bootstrap
    
    # Run bootstrap
    controller, view = bootstrap()
    
    # Add view to qtbot for memory management
    qtbot.addWidget(view)
    
    # Verify controller initialization
    assert controller is not None
    assert view is not None
    
    # Verify wiring (bridge properties)
    assert view._app_controller is controller
    
    # Verify sub-controllers are accessible (via DI or manually injected)
    # ProjectController and BatchController are usually created in bootstrap and wired
    assert view.project_controller is not None
    assert view.batch_controller is not None
    
    # Clean up
    view.close()

def test_smoke_file_open(qtbot, temp_rpy_file: Path):
    """
    Smoke test: Open a file via controller.
    Verifies the end-to-end flow of opening a file.
    """
    from app_bootstrap import bootstrap
    from interfaces.i_controller import IFileController
    from interfaces.di_container import DIContainer
    import os
    
    # Bootstrap app
    controller, view = bootstrap()
    qtbot.addWidget(view)
    
    # Get file controller from app controller or container
    file_controller = DIContainer.instance().resolve(IFileController)
    assert file_controller is not None
    
    # Create a spy for signal tracking (if possible, otherwise just check state)
    # We'll check if file open modifies the project model
    
    # Simulate file opening (bypassing the file dialog part, calling the logic directly)
    # Since we can't easily mock the file dialog in a smoke test without mocking libraries,
    # we will trigger the controller's logic if possible, OR
    # we can use the signal flow if we simulate the view signal.
    
    # Let's try to just open the file via the controller directly, 
    # which is what the view signal handler ultimately does (or calls legacy manager).
    # Since PR-4, open_file goes to app_bootstrap's _handle_open_file -> legacy manager open_file_dialog.
    # That opens a dialog, which blocks.
    
    # Instead, we should test the *result* of an open action, 
    # or use the legacy manager's load_file method which is what the dialog calls.
    
    import gui.gui_file_manager as file_manager
    
    # Call the core load logic directly to verify it works
    # This avoids the blocking file dialog
    # load_file(main_window, file_path, selected_mode)
    file_manager.load_file(view, str(temp_rpy_file), "translate")
    
    # Verify file is loaded
    assert str(temp_rpy_file) in view.file_data
    
    # Verify state sync (PR-3)
    # Project model should have the file open
    project = controller.project
    assert project.is_file_open(str(temp_rpy_file))
    assert project.active_file_path == str(temp_rpy_file)
    
    # Clean up
    view.close()
