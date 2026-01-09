import re
import os, sys
from pathlib import Path

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Development mode: use directory containing this config file (project root)
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

VERSION = "0.3.10-ALPHA"
DEFAULT_UI_LANGUAGE = "tr"  # Supported: "tr" (Turkish), "en" (English)
ABOUT_TEXT = (
    "<p style='text-align: center; font-size: 14pt;'>RenForge - Ren'Py scripts editor</p>"
    "<p style='text-align: center; font-size: 12pt;'>Using: <a style='color: #fff' href=\"https://github.com/Lattyware/unrpa\">unrpa by Lattyware</a> and <a style='color: #fff' href=\"https://github.com/CensoredUsername/unrpyc\">unrpyc by CensoredUsername</a></p>"
    f"<p style='text-align: center; font-size: 12pt;'>v{VERSION}</p>"
)

DEFAULT_MODEL_NAME = "gemini-2.0-flash"

REQUEST_DELAY_SECONDS = 1  
_available_models_cache = None 

CONTEXT_LINES = 15 
BREAKPOINT_MARKER = "# renforge-breakpoint" 
DEFAULT_MODE_SELECTION_METHOD = None 
DEFAULT_USE_DETECTED_TARGET_LANG = True 
BATCH_TRANSLATE_DELAY = 0.01
ALLOW_EMPTY_STRINGS = True

SETTINGS_DIR = Path.home() / ".renforge" 
SETTINGS_FILE_PATH = SETTINGS_DIR / "settings.json"

DEFAULT_AUTO_PREPARE_PROJECT = True 

TRANSLATE_BLOCK_REGEX = re.compile(r'^\s*translate\s+(\w+)\s+(\w+):')
OLD_STRING_REGEX = re.compile(r'^(\s*)old\s+"((?:\\.|[^"\\])*)"(.*)$')
NEW_STRING_REGEX = re.compile(r'^(\s*)new\s+"((?:\\.|[^"\\])*)"(.*)$')

DEFAULT_TARGET_LANG = "tr"
DEFAULT_SOURCE_LANG = "en"

STYLE_DEFAULTS = {
    "text_color": "#f0f0f0",             
    "modified_text_color": "#ADD8E6",    
    "breakpoint_bg_color": "#5e5e3c",    
    "bg_even_color": "#2b2b2b",          
    "bg_odd_color": "#3c3f41",           
}

DIRECT_MODE_EDITABLE_TYPES = {
    "dialogue",
    "narration",
    "menu",
    "screen_text",
    "screen_textbutton",
    "screen_text_property",

}

# Optional glossary for AI translation term consistency
# Format: {"source_term": "target_term", ...}
# Example: {"MC": "Ana Karakter", "skill points": "yetenek puanları"}
TRANSLATION_GLOSSARY = {}

__all__ = [
    "VERSION", "ABOUT_TEXT",
    "DEFAULT_TARGET_LANG", "DEFAULT_SOURCE_LANG", "DEFAULT_MODEL_NAME",

    "CONTEXT_LINES", "BREAKPOINT_MARKER", "SETTINGS_FILE_PATH", "SETTINGS_DIR", 
    "DEFAULT_MODE_SELECTION_METHOD", "DEFAULT_USE_DETECTED_TARGET_LANG",
    "DIRECT_MODE_EDITABLE_TYPES", "BATCH_TRANSLATE_DELAY", "resource_path",
    "TRANSLATE_BLOCK_REGEX", "OLD_STRING_REGEX", "NEW_STRING_REGEX", 
    "Path", "REQUEST_DELAY_SECONDS", "DEFAULT_AUTO_PREPARE_PROJECT",
    "ALLOW_EMPTY_STRINGS", "TRANSLATION_GLOSSARY", 

]

# Import logger at the end to avoid circular imports
from renforge_logger import get_logger
_logger = get_logger("config")
_logger.debug("renforge_config.py loaded") 