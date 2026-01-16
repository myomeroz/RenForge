
import os
from PySide6.QtGui import QIcon
import renforge_config as config
from renforge_logger import get_logger

logger = get_logger("gui.utils")

def get_icon(name: str) -> QIcon:
    """
    Load an icon from the pics directory.
    If 'name' doesn't have an extension, tries .svg then .png.
    """
    # Handle full relative path or just name
    if "/" in name or "\\" in name:
        rel_path = name
    else:
        rel_path = f"pics/{name}"
        
    full_path = config.resource_path(rel_path)
    
    # Try exact match
    if os.path.isfile(full_path):
        return QIcon(full_path)
        
    # Try adding extensions
    for ext in [".svg", ".png", ".ico"]:
        test_path = full_path + ext
        if os.path.isfile(test_path):
            return QIcon(test_path)
            
    logger.debug(f"Icon not found: {name}")
    return QIcon()

def safe_icon(relative_path: str) -> QIcon:
    """Compatibility alias for get_icon, expects relative path."""
    return get_icon(relative_path)
