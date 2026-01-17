
import sys
import os
from PySide6.QtWidgets import QApplication

# Add project root to path
sys.path.append(os.getcwd())

# Mock logger
import renforge_logger
import logging
renforge_logger.get_logger = lambda x: logging.getLogger(x)

def test_ui_components():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("Testing MiniBatchBar instantiation...")
    try:
        from gui.widgets.mini_batch_bar import MiniBatchBar
        bar = MiniBatchBar()
        print("✅ MiniBatchBar instantiated")
    except Exception as e:
        print(f"❌ MiniBatchBar failed: {e}")
        sys.exit(1)

    print("Testing InspectorPanel instantiation...")
    try:
        from gui.panels.inspector_panel import InspectorPanel
        panel = InspectorPanel()
        print("✅ InspectorPanel instantiated")
    except Exception as e:
        print(f"❌ InspectorPanel failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_ui_components()
        print("\nAll UI smoke tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
