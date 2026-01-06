import sys
import os
import argparse

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    sys.path.insert(0, application_path)
    print(f"Running from bundle. Added to sys.path: {application_path}")
elif __file__:
    application_path = os.path.dirname(__file__)
    if application_path not in sys.path:
        sys.path.insert(0, application_path)
    print(f"Running from script. Added to sys.path: {application_path}")

print("Current sys.path:")

for p in sys.path:
    print(f"  - {p}")

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QTimer
    GUI_AVAILABLE = True
except ImportError:
    print("CRITICAL ERROR: PyQt6 is required to run RenForge but is not installed.")
    print("Please install it: pip install PyQt6")
    sys.exit(1) 

try:
    import renforge_config as config
    from renforge_settings import load_settings
    import locales
    from gui.renforge_gui import RenForgeGUI
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import RenForge modules: {e}")
    try:
        if QApplication.instance():
            QMessageBox.critical(None, "Module Import Error",
                                f"Failed to import RenForge modules:\n{e}\n\n")
    except Exception as msg_e:
         print(f"Could not show GUI error message: {msg_e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Interactive Ren'Py script editor with AI support (RenForge).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    parser.add_argument(
        "input_file",
        help="Path to the source .rpy file to open on startup (optional).",
        nargs='?',         
        default=None
    )
    parser.add_argument(
        "-tl", "--lang",
        default=config.DEFAULT_TARGET_LANG, 
        help="Default target language for new files and AI."
    )
    parser.add_argument(
        "-sl", "--source-lang",
        default=config.DEFAULT_SOURCE_LANG, 
        help="Default source language for new files and AI."
    )
    parser.add_argument(
        "--model",
        default=config.DEFAULT_MODEL_NAME, 
        help="Name of Google Gemini model."
    )
    
    args = parser.parse_args()
    
    # Load settings and initialize UI language BEFORE creating GUI
    initial_settings = load_settings()
    ui_lang = initial_settings.get("ui_language", config.DEFAULT_UI_LANGUAGE)
    locales.set_language(ui_lang)
    print(f"UI language initialized: {ui_lang}")
    
    app = QApplication(sys.argv)
    window = RenForgeGUI()

    window.target_language = args.lang
    window.source_language = args.source_lang
    window.selected_model = args.model
    
    target_index = window.target_lang_combo.findData(window.target_language)
    if target_index != -1:
        window.target_lang_combo.setCurrentIndex(target_index)
    source_index = window.source_lang_combo.findData(window.source_language)
    if source_index != -1:
        window.source_lang_combo.setCurrentIndex(source_index)
    
    window.model_combo.blockSignals(True)
    
    if window.model_combo.findText(window.selected_model) == -1:
         print(f"Warning: Initial model '{window.selected_model}' not in default list, adding temporarily.")
         window.model_combo.insertItem(0, window.selected_model)
    window.model_combo.setCurrentText(window.selected_model)
    window.model_combo.blockSignals(False)

    window.show()
    print("RenForge GUI started.")

    if args.input_file:
        input_path = os.path.abspath(args.input_file) 
        if os.path.exists(input_path) and os.path.isfile(input_path):
            print(f"Scheduling lazy loading for: {input_path}")
            
            initial_mode = "direct"
            file_name = os.path.basename(input_path)
            
            lang_suffixes = ["_ren.rpy", "_eng.rpy", "_chs.rpy", "_rus.rpy", "_es.rpy", "_pt.rpy", "_ja.rpy", "_ko.rpy", "_de.rpy", "_fr.rpy"] 
            if any(file_name.endswith(suffix) for suffix in lang_suffixes):
                initial_mode = "translate"
            QTimer.singleShot(0, lambda f=input_path, m=initial_mode: window._load_file(f, m))
        else:
            warning_message = f"The file specified at startup was not found or is not a file:\n{input_path}"
            print(f"Warning: {warning_message}")
            QTimer.singleShot(100, lambda msg=warning_message: QMessageBox.warning(window, "File Not Found", msg))
    
    exit_code = app.exec()
    print(f"RenForge GUI finished with exit code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    print("Starting RenForge...")
    main()