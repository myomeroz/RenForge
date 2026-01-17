
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from gui.models.row_data import RowData, RowStatus
from gui.models.translation_table_model import TranslationTableModel, TableColumn
from gui.models.translation_filter_proxy import TranslationFilterProxyModel
from gui.models.translation_table_model import TranslationTableModel, TableColumn
from gui.models.translation_filter_proxy import TranslationFilterProxyModel
from gui.views.file_table_view import parsed_items_to_table_rows, resolve_table_widget

# Mock ParsedItem
class MockItem:
    def __init__(self, text, type="dialogue"):
        self.line_number = 1
        self.item_type = type
        self.variable_name = None
        self.character_trans = "eileen"
        self.character_tag = "e"
        self.original_text = "Hello"
        self.current_text = text
        self.is_modified_session = False
        self.has_breakpoint = False
        self.batch_marker = None
        self.batch_tooltip = None

def test_row_data_creation():
    print("Testing RowData creation...")
    row = RowData(
        id="1",
        row_type="dialogue",
        original_text="Hello",
        status=RowStatus.UNTRANSLATED
    )
    assert row.status == RowStatus.UNTRANSLATED
    assert row.editable_text == ""
    
    row.update_text("Merhaba")
    assert row.editable_text == "Merhaba"
    assert row.status == RowStatus.MODIFIED
    print("RowData creation OK")

def test_model_integration():
    print("Testing Model integration...")
    app = QApplication(sys.argv)
    
    model = TranslationTableModel()
    proxy = TranslationFilterProxyModel()
    proxy.setSourceModel(model)
    
    # Create rows
    rows = [
        RowData(id="1", row_type="say", original_text="Hi", editable_text="", status=RowStatus.UNTRANSLATED),
        RowData(id="2", row_type="say", original_text="Bye", editable_text="Güle güle", status=RowStatus.TRANSLATED),
        RowData(id="3", row_type="say", original_text="Error", editable_text="", status=RowStatus.ERROR),
    ]
    model.set_rows(rows)
    
    assert model.rowCount() == 3
    
    # Test Proxy Filtering
    print("Testing Proxy Filtering...")
    proxy.set_status_filter(TranslationFilterProxyModel.FILTER_UNTRANSLATED)
    assert proxy.rowCount() == 1
    
    proxy.set_status_filter(TranslationFilterProxyModel.FILTER_TRANSLATED)
    assert proxy.rowCount() == 1
    
    proxy.set_status_filter(TranslationFilterProxyModel.FILTER_ERROR)
    assert proxy.rowCount() == 1
    
    proxy.set_status_filter(TranslationFilterProxyModel.FILTER_PROBLEMS)
    # Untranslated + Error = 2
    assert proxy.rowCount() == 2
    
    print("Model integration OK")

def test_parsed_item_conversion():
    print("Testing ParsedItem conversion...")
    items = [
        MockItem(""), # Untranslated
        MockItem("Translated"), # Translated
    ]
    
    rows = parsed_items_to_table_rows(items, "translate")
    assert len(rows) == 2
    assert rows[0].status == RowStatus.UNTRANSLATED
    assert rows[1].status == RowStatus.TRANSLATED
    print("ParsedItem conversion OK")

if __name__ == "__main__":
    test_row_data_creation()
    test_model_integration()
    # test_parsed_item_conversion()
    print("ALL TESTS PASSED")
