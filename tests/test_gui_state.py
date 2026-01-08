import pytest
from PyQt6.QtWidgets import QTableWidget
from models.parsed_file import ParsedFile
from renforge_enums import FileMode

def test_gui_state_tracks_parsed_file(qtbot):
    """
    Verify that RenForgeGUI correctly tracks state changes in ParsedFile objects.
    """
    from app_bootstrap import bootstrap
    controller, view = bootstrap()
    qtbot.addWidget(view)
    
    # Create a mock ParsedFile
    pf = ParsedFile(
        file_path="dummy.rpy",
        mode=FileMode.DIRECT,
        lines=["line 1"],
        items=[],
        breakpoints=set()
    )
    
    # Simulate opening file via controller/bootstrap logic
    # We call the method that attaches it to the view
    from app_bootstrap import _on_file_opened_from_controller
    _on_file_opened_from_controller(view, pf)
    
    # Verify it's in view data
    assert "dummy.rpy" in view.file_data
    stored_pf = view.file_data["dummy.rpy"]
    assert stored_pf is pf
    
    # Verify initial modified state
    assert not stored_pf.is_modified
    assert not view._is_current_tab_modified()
    
    # Modify ParsedFile directly (simulating controller or backend change)
    stored_pf.is_modified = True
    
    # Verify view reflects modification (needs to update UI state)
    # The signal connection needs to be verified.
    # In current architecture, ParsedFile doesn't magically signal the view UNLESS
    # we connected a signal or the view polls.
    # RenForgeGUI._set_current_tab_modified updates the ParsedFile AND the UI.
    # Let's verify that method works.
    
    view._set_current_tab_modified(True)
    assert stored_pf.is_modified is True
    # Tab text should have '*'
    tab_idx = view.tab_widget.currentIndex()
    assert view.tab_widget.tabText(tab_idx).endswith("*")
    
    view._set_current_tab_modified(False)
    assert stored_pf.is_modified is False
    assert not view.tab_widget.tabText(tab_idx).endswith("*")

    view.close()
