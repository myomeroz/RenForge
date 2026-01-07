# -*- coding: utf-8 -*-
"""
RenForge Localization Manager
Modern JSON-based localization system with dynamic language loading.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from renforge_logger import get_logger
logger = get_logger("localization")


class LocalizationManager:
    """
    Singleton class for managing application localization.
    Loads translations from JSON files in the locales directory.
    """
    
    _instance: Optional['LocalizationManager'] = None
    _initialized: bool = False
    
    # Supported UI languages
    SUPPORTED_LANGUAGES = {
        "tr": "Türkçe",
        "en": "English"
    }
    DEFAULT_LANGUAGE = "tr"
    
    def __new__(cls) -> 'LocalizationManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if LocalizationManager._initialized:
            return
        
        self._current_language = self.DEFAULT_LANGUAGE
        self._translations: Dict[str, Dict[str, str]] = {}
        self._locales_dir = self._get_locales_dir()
        
        # Load all available translations
        self._load_all_translations()
        
        LocalizationManager._initialized = True
        logger.debug(f"LocalizationManager initialized. Languages loaded: {list(self._translations.keys())}")
    
    def _get_locales_dir(self) -> Path:
        """Get the path to the locales directory."""
        # Try relative to this file first
        module_dir = Path(__file__).parent
        locales_dir = module_dir / "locales"
        
        if locales_dir.exists():
            return locales_dir
        
        # Try current working directory
        cwd_locales = Path.cwd() / "locales"
        if cwd_locales.exists():
            return cwd_locales
        
        # Fallback - try to find renforge_config for resource_path
        try:
            import renforge_config as config
            return Path(config.resource_path("locales"))
        except (ImportError, AttributeError):
            pass
        
        logger.warning(f"Locales directory not found. Using default: {locales_dir}")
        return locales_dir
    
    def _load_all_translations(self) -> None:
        """Load all translation files from the locales directory."""
        if not self._locales_dir.exists():
            logger.error(f"Locales directory does not exist: {self._locales_dir}")
            return
        
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            self._load_language(lang_code)
    
    def _load_language(self, lang_code: str) -> bool:
        """
        Load translations for a specific language.
        
        Args:
            lang_code: Language code (e.g., 'tr', 'en')
            
        Returns:
            True if successful, False otherwise
        """
        json_path = self._locales_dir / f"{lang_code}.json"
        
        if not json_path.exists():
            logger.warning(f"Translation file not found: {json_path}")
            return False
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self._translations[lang_code] = json.load(f)
            
            logger.debug(f"Loaded {len(self._translations[lang_code])} translations for '{lang_code}'")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading {json_path}: {e}")
            return False
    
    def reload_language(self, lang_code: str) -> bool:
        """
        Reload translations for a specific language (for hot-reload support).
        
        Args:
            lang_code: Language code to reload
            
        Returns:
            True if successful
        """
        return self._load_language(lang_code)
    
    def set_language(self, lang_code: str) -> bool:
        """
        Set the current UI language.
        
        Args:
            lang_code: Language code to set
            
        Returns:
            True if language was set successfully
        """
        if lang_code not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language code: '{lang_code}'")
            return False
        
        if lang_code not in self._translations:
            if not self._load_language(lang_code):
                logger.error(f"Cannot set language '{lang_code}': translations not available")
                return False
        
        self._current_language = lang_code
        logger.debug(f"UI language set to: {lang_code}")
        return True
    
    def get_language(self) -> str:
        """Get the current language code."""
        return self._current_language
    
    def translate(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.
        
        Args:
            key: Translation key
            **kwargs: Format parameters for the translated string
            
        Returns:
            Translated string, or the key itself if not found
        """
        # Get translations for current language, fallback to English, then empty dict
        translations = self._translations.get(
            self._current_language,
            self._translations.get("en", {})
        )
        
        text = translations.get(key, key)
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing format key {e} for translation '{key}'")
            except Exception as e:
                logger.warning(f"Error formatting translation '{key}': {e}")
        
        return text
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get dictionary of available language codes and names."""
        return self.SUPPORTED_LANGUAGES.copy()
    
    def has_key(self, key: str) -> bool:
        """Check if a translation key exists in the current language."""
        translations = self._translations.get(self._current_language, {})
        return key in translations


# =============================================================================
# GLOBAL SINGLETON INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================

_manager: Optional[LocalizationManager] = None


def _get_manager() -> LocalizationManager:
    """Get or create the LocalizationManager singleton."""
    global _manager
    if _manager is None:
        _manager = LocalizationManager()
    return _manager


# Convenience functions for backward compatibility with old locales.py API
def tr(key: str, **kwargs) -> str:
    """
    Translate a key to the current language.
    This is the main function used throughout the application.
    """
    return _get_manager().translate(key, **kwargs)


def set_language(lang_code: str) -> bool:
    """Set the current UI language."""
    return _get_manager().set_language(lang_code)


def get_language() -> str:
    """Get the current UI language code."""
    return _get_manager().get_language()


# Backward compatibility constants
SUPPORTED_UI_LANGUAGES = LocalizationManager.SUPPORTED_LANGUAGES
DEFAULT_UI_LANGUAGE = LocalizationManager.DEFAULT_LANGUAGE
