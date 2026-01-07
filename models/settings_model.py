# -*- coding: utf-8 -*-
"""
RenForge Settings Model

Abstracts application settings with:
- Type-safe access to settings
- Change notifications via PyQt signals
- Validation and defaults
"""

from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
import json

from renforge_logger import get_logger
import renforge_config as config

logger = get_logger("models.settings")


class SettingsModel:
    """
    Singleton model for application settings.
    
    Provides:
    - Type-safe property access
    - Change notifications (Observer pattern)
    - Automatic persistence
    - Validation
    """
    
    _instance: Optional['SettingsModel'] = None
    _initialized: bool = False
    
    # Setting keys
    KEY_API_KEY = "api_key"
    KEY_MODE_SELECTION = "mode_selection_method"
    KEY_TARGET_LANG = "default_target_language"
    KEY_SOURCE_LANG = "default_source_language"
    KEY_MODEL = "default_selected_model"
    KEY_USE_DETECTED_LANG = "use_detected_target_lang"
    KEY_AUTO_PREPARE = "auto_prepare_project"
    KEY_UI_LANGUAGE = "ui_language"
    KEY_WINDOW_W = "window_size_w"
    KEY_WINDOW_H = "window_size_h"
    KEY_WINDOW_MAX = "window_maximized"
    
    def __new__(cls) -> 'SettingsModel':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if SettingsModel._initialized:
            return
        
        self._settings: Dict[str, Any] = {}
        self._observers: Dict[str, List[Callable]] = {}
        self._dirty = False
        
        # Load settings
        self._load()
        
        SettingsModel._initialized = True
        logger.debug("SettingsModel initialized")
    
    # =============================================================================
    # SINGLETON ACCESS
    # =============================================================================
    
    @classmethod
    def instance(cls) -> 'SettingsModel':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = SettingsModel()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
        cls._initialized = False

    # =============================================================================
    # PERSISTENCE
    # =============================================================================
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default settings."""
        return {
            self.KEY_API_KEY: None,
            self.KEY_MODE_SELECTION: config.DEFAULT_MODE_SELECTION_METHOD,
            self.KEY_TARGET_LANG: config.DEFAULT_TARGET_LANG,
            self.KEY_SOURCE_LANG: config.DEFAULT_SOURCE_LANG,
            self.KEY_MODEL: config.DEFAULT_MODEL_NAME,
            self.KEY_USE_DETECTED_LANG: config.DEFAULT_USE_DETECTED_TARGET_LANG,
            self.KEY_AUTO_PREPARE: config.DEFAULT_AUTO_PREPARE_PROJECT,
            self.KEY_UI_LANGUAGE: config.DEFAULT_UI_LANGUAGE,
            self.KEY_WINDOW_W: 1200,
            self.KEY_WINDOW_H: 800,
            self.KEY_WINDOW_MAX: False,
        }
    
    def _load(self):
        """Load settings from file."""
        self._settings = self._get_defaults()
        settings_file = config.SETTINGS_FILE_PATH
        
        if not settings_file.is_file():
            logger.info(f"Settings file not found, using defaults")
            return
        
        try:
            with settings_file.open('r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            if isinstance(loaded, dict):
                self._settings.update(loaded)
                self._validate_all()
                logger.debug("Settings loaded successfully")
            else:
                logger.warning("Settings file format invalid, using defaults")
                
        except json.JSONDecodeError:
            logger.error(f"Settings file corrupted, using defaults")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    
    def save(self) -> bool:
        """Save settings to file."""
        settings_file = config.SETTINGS_FILE_PATH
        
        try:
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with settings_file.open('w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
            
            self._dirty = False
            logger.info("Settings saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False
    
    def _validate_all(self):
        """Validate all settings."""
        defaults = self._get_defaults()
        
        # Mode selection
        if self._settings.get(self.KEY_MODE_SELECTION) not in [None, "auto", "manual"]:
            self._settings[self.KEY_MODE_SELECTION] = defaults[self.KEY_MODE_SELECTION]
        
        # Boolean settings
        for key in [self.KEY_USE_DETECTED_LANG, self.KEY_AUTO_PREPARE, self.KEY_WINDOW_MAX]:
            if not isinstance(self._settings.get(key), bool):
                self._settings[key] = defaults[key]
        
        # UI language
        if self._settings.get(self.KEY_UI_LANGUAGE) not in ["tr", "en"]:
            self._settings[self.KEY_UI_LANGUAGE] = defaults[self.KEY_UI_LANGUAGE]
        
        # Integer settings
        for key in [self.KEY_WINDOW_W, self.KEY_WINDOW_H]:
            if not isinstance(self._settings.get(key), int):
                self._settings[key] = defaults[key]

    # =============================================================================
    # OBSERVER PATTERN
    # =============================================================================
    
    def subscribe(self, key: str, callback: Callable[[Any], None]):
        """
        Subscribe to changes on a specific setting.
        
        Args:
            key: Setting key to watch
            callback: Function called with new value when setting changes
        """
        if key not in self._observers:
            self._observers[key] = []
        self._observers[key].append(callback)
    
    def unsubscribe(self, key: str, callback: Callable):
        """Unsubscribe from setting changes."""
        if key in self._observers and callback in self._observers[key]:
            self._observers[key].remove(callback)
    
    def _notify(self, key: str, value: Any):
        """Notify observers of a setting change."""
        for callback in self._observers.get(key, []):
            try:
                callback(value)
            except Exception as e:
                logger.error(f"Error in settings observer for '{key}': {e}")

    # =============================================================================
    # GENERIC ACCESS
    # =============================================================================
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = False):
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: New value
            save: If True, immediately persist to disk
        """
        old_value = self._settings.get(key)
        if old_value != value:
            self._settings[key] = value
            self._dirty = True
            self._notify(key, value)
            
            if save:
                self.save()

    # =============================================================================
    # TYPED PROPERTIES
    # =============================================================================
    
    @property
    def api_key(self) -> Optional[str]:
        return self._settings.get(self.KEY_API_KEY)
    
    @api_key.setter
    def api_key(self, value: Optional[str]):
        self.set(self.KEY_API_KEY, value)
    
    @property
    def mode_selection_method(self) -> Optional[str]:
        return self._settings.get(self.KEY_MODE_SELECTION)
    
    @mode_selection_method.setter
    def mode_selection_method(self, value: Optional[str]):
        if value not in [None, "auto", "manual"]:
            raise ValueError(f"Invalid mode selection method: {value}")
        self.set(self.KEY_MODE_SELECTION, value)
    
    @property
    def default_target_language(self) -> str:
        return self._settings.get(self.KEY_TARGET_LANG, "tr")
    
    @default_target_language.setter
    def default_target_language(self, value: str):
        self.set(self.KEY_TARGET_LANG, value)
    
    @property
    def default_source_language(self) -> str:
        return self._settings.get(self.KEY_SOURCE_LANG, "en")
    
    @default_source_language.setter
    def default_source_language(self, value: str):
        self.set(self.KEY_SOURCE_LANG, value)
    
    @property
    def default_model(self) -> Optional[str]:
        return self._settings.get(self.KEY_MODEL)
    
    @default_model.setter
    def default_model(self, value: Optional[str]):
        self.set(self.KEY_MODEL, value)
    
    @property
    def use_detected_target_lang(self) -> bool:
        return self._settings.get(self.KEY_USE_DETECTED_LANG, True)
    
    @use_detected_target_lang.setter
    def use_detected_target_lang(self, value: bool):
        self.set(self.KEY_USE_DETECTED_LANG, value)
    
    @property
    def auto_prepare_project(self) -> bool:
        return self._settings.get(self.KEY_AUTO_PREPARE, True)
    
    @auto_prepare_project.setter
    def auto_prepare_project(self, value: bool):
        self.set(self.KEY_AUTO_PREPARE, value)
    
    @property
    def ui_language(self) -> str:
        return self._settings.get(self.KEY_UI_LANGUAGE, "tr")
    
    @ui_language.setter
    def ui_language(self, value: str):
        if value not in ["tr", "en"]:
            raise ValueError(f"Invalid UI language: {value}")
        self.set(self.KEY_UI_LANGUAGE, value)
    
    @property
    def window_size(self) -> tuple:
        """Get window size as (width, height) tuple."""
        return (
            self._settings.get(self.KEY_WINDOW_W, 1200),
            self._settings.get(self.KEY_WINDOW_H, 800)
        )
    
    @window_size.setter
    def window_size(self, value: tuple):
        self.set(self.KEY_WINDOW_W, value[0])
        self.set(self.KEY_WINDOW_H, value[1])
    
    @property
    def window_maximized(self) -> bool:
        return self._settings.get(self.KEY_WINDOW_MAX, False)
    
    @window_maximized.setter
    def window_maximized(self, value: bool):
        self.set(self.KEY_WINDOW_MAX, value)

    # =============================================================================
    # UTILITY
    # =============================================================================
    
    @property
    def is_dirty(self) -> bool:
        """Check if settings have unsaved changes."""
        return self._dirty
    
    def to_dict(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return self._settings.copy()
    
    def __repr__(self) -> str:
        return f"SettingsModel(dirty={self._dirty})"
