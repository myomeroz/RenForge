import sys
import os
import argparse

from renforge_logger import get_logger
logger = get_logger("main")

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    sys.path.insert(0, application_path)
    logger.debug(f"Running from bundle. Added to sys.path: {application_path}")
elif __file__:
    application_path = os.path.dirname(__file__)
    if application_path not in sys.path:
        sys.path.insert(0, application_path)
    logger.debug(f"Running from script. Added to sys.path: {application_path}")

logger.debug("Current sys.path: " + ", ".join(sys.path[:3]) + "...")

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QTimer
    GUI_AVAILABLE = True
except ImportError:
    logger.critical("PyQt6 is required to run RenForge but is not installed.")
    logger.critical("Please install it: pip install PyQt6")
    sys.exit(1) 

try:
    import renforge_config as config
    from renforge_settings import load_settings
    import locales
    from app_bootstrap import bootstrap
except ImportError as e:
    logger.critical(f"Failed to import RenForge modules: {e}")
    try:
        if QApplication.instance():
            QMessageBox.critical(None, "Module Import Error",
                                f"Failed to import RenForge modules:\n{e}\n\n")
    except Exception as msg_e:
         logger.error(f"Could not show GUI error message: {msg_e}")
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
    logger.info(f"UI language initialized: {ui_lang}")
    
    app = QApplication(sys.argv)
    
    # Phase 4: Use bootstrap to create controller and view with DI
    controller, window = bootstrap()
    logger.info("Bootstrap complete. Controller and View created.")

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
         logger.warning(f"Initial model '{window.selected_model}' not in default list, adding temporarily.")
         window.model_combo.insertItem(0, window.selected_model)
    window.model_combo.setCurrentText(window.selected_model)
    window.model_combo.blockSignals(False)

    window.show()
    logger.info("RenForge GUI started.")

    if args.input_file:
        input_path = os.path.abspath(args.input_file) 
        if os.path.exists(input_path) and os.path.isfile(input_path):
            logger.debug(f"Scheduling lazy loading for: {input_path}")
            
            initial_mode = "direct"
            file_name = os.path.basename(input_path)
            
            lang_suffixes = ["_ren.rpy", "_eng.rpy", "_chs.rpy", "_rus.rpy", "_es.rpy", "_pt.rpy", "_ja.rpy", "_ko.rpy", "_de.rpy", "_fr.rpy"] 
            if any(file_name.endswith(suffix) for suffix in lang_suffixes):
                initial_mode = "translate"
            
            # Phase 4 COMPLETE: Route file opening through controller only
            # UI update happens automatically via file_opened signal -> _on_file_opened_from_controller
            def open_startup_file(path, mode):
                logger.info(f"Opening startup file via controller: {path} (mode={mode})")
                controller.open_file(path, mode)
                # NOTE: UI update is now handled by file_opened signal in app_bootstrap.py
                # Legacy path (window._load_file) is no longer needed
            
            QTimer.singleShot(0, lambda f=input_path, m=initial_mode: open_startup_file(f, m))
        else:
            warning_message = f"The file specified at startup was not found or is not a file:\n{input_path}"
            logger.warning(warning_message)
            QTimer.singleShot(100, lambda msg=warning_message: QMessageBox.warning(window, "File Not Found", msg))
    
    exit_code = app.exec()
    logger.info(f"RenForge GUI finished with exit code {exit_code}.")
    sys.exit(exit_code)

if __name__ == "__main__":
    logger.info("Starting RenForge...")
    main()