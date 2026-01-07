# -*- coding: utf-8 -*-
"""
RenForge Localization Module (Backward Compatibility Wrapper)

This module re-exports the localization functions from the new
renforge_localization module for backward compatibility.

All imports of `from locales import tr` will continue to work.
"""

# Re-export everything from the new localization module
from renforge_localization import (
    tr,
    set_language,
    get_language,
    SUPPORTED_UI_LANGUAGES,
    DEFAULT_UI_LANGUAGE,
    LocalizationManager,
)

# Backward compatibility: old code may import TRANSLATIONS directly
# We'll provide an empty dict to avoid import errors, but log a deprecation warning
from renforge_logger import get_logger
logger = get_logger("locales")

# Deprecated - kept for backward compatibility only
TRANSLATIONS = {}
logger.debug("locales.py wrapper loaded - using JSON-based localization from renforge_localization.py")

__all__ = [
    'tr',
    'set_language', 
    'get_language',
    'SUPPORTED_UI_LANGUAGES',
    'DEFAULT_UI_LANGUAGE',
    'LocalizationManager',
    'TRANSLATIONS',  # Deprecated
]
