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
    KEY_RECENT_FILES = "recent_files"  # List of recently opened file paths
    KEY_RECENT_PROJECTS = "recent_projects"  # List of recently opened project paths
    
    # Session persistence (v2)
    KEY_OPEN_TABS = "session_open_tabs"  # List of open file paths
    KEY_ACTIVE_TAB = "session_active_tab"  # Currently active file path
    
    # UI Layout persistence
    KEY_SIDEBAR_COLLAPSED = "ui_sidebar_collapsed"  # bool - sidebar daraltılmış mı
    KEY_INSPECTOR_VISIBLE = "ui_inspector_visible"  # bool - inspector görünür mü
    KEY_INSPECTOR_WIDTH = "ui_inspector_width"  # int - inspector genişliği (piksel)
    
    # Keyboard Shortcuts
    KEY_SHORTCUTS = "keyboard_shortcuts"  # Dict[str, str] - action_id -> sequence string
    KEY_SHORTCUTS_ENABLED = "keyboard_shortcuts_enabled"  # bool - global toggle
    
    # Retry Policy (Stage 14)
    KEY_RETRY_PROFILE = "retry_profile"  # str - "Kapalı" / "Yumuşak" / "Agresif"
    KEY_BATCH_CHUNK_SIZE = "batch_chunk_size"  # int - default chunk size for batch
    
    # Translation Memory (Stage 16.1)
    KEY_TM_ENABLED = "tm_enabled"  # bool - enable TM lookup
    KEY_TM_AUTO_APPLY_EXACT = "tm_auto_apply_exact"  # bool - auto-apply exact matches
    
    # Glossary (Stage 16.2)
    KEY_GLOSSARY_ENABLED = "glossary_enabled"  # bool - enable glossary checks
    KEY_GLOSSARY_MODE = "glossary_mode"  # "qc_only" | "enforce"
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
            # UI Layout defaults
            self.KEY_SIDEBAR_COLLAPSED: False,
            self.KEY_INSPECTOR_VISIBLE: True,
            self.KEY_INSPECTOR_WIDTH: 300,
            # Shortcuts logic
            self.KEY_SHORTCUTS: {},  # Empty means use manager defaults
            self.KEY_SHORTCUTS_ENABLED: True,
            # Retry Policy (Stage 14)
            self.KEY_RETRY_PROFILE: "Yumuşak",
            self.KEY_BATCH_CHUNK_SIZE: 20,
            # Translation Memory (Stage 16.1)
            self.KEY_TM_ENABLED: True,
            self.KEY_TM_AUTO_APPLY_EXACT: True,
            # Glossary (Stage 16.2)
            self.KEY_GLOSSARY_ENABLED: True,
            self.KEY_GLOSSARY_MODE: "qc_only",
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
    # RECENT FILES & PROJECTS
    # =============================================================================
    
    @property
    def recent_files(self) -> List[str]:
        """Get list of recently opened file paths."""
        return self._settings.get(self.KEY_RECENT_FILES, [])
    
    def add_recent_file(self, file_path: str, max_count: int = 20):
        """Add a file to recents (moves to front if exists)."""
        recents = self.recent_files.copy()
        # Remove if exists
        if file_path in recents:
            recents.remove(file_path)
        # Add to front
        recents.insert(0, file_path)
        # Limit size
        recents = recents[:max_count]
        self.set(self.KEY_RECENT_FILES, recents)
    
    def clear_recent_files(self):
        """Clear recent files list."""
        self.set(self.KEY_RECENT_FILES, [])
    
    @property
    def recent_projects(self) -> List[str]:
        """Get list of recently opened project paths."""
        return self._settings.get(self.KEY_RECENT_PROJECTS, [])
    
    def add_recent_project(self, project_path: str, max_count: int = 10):
        """Add a project to recents (moves to front if exists)."""
        recents = self.recent_projects.copy()
        if project_path in recents:
            recents.remove(project_path)
        recents.insert(0, project_path)
        recents = recents[:max_count]
        self.set(self.KEY_RECENT_PROJECTS, recents)

    # =============================================================================
    # SESSION PERSISTENCE (v2)
    # =============================================================================
    
    @property
    def open_tabs(self) -> List[str]:
        """Get list of open file paths from last session."""
        return self._settings.get(self.KEY_OPEN_TABS, [])
    
    @property
    def active_tab(self) -> Optional[str]:
        """Get active file path from last session."""
        return self._settings.get(self.KEY_ACTIVE_TAB, None)
    
    def save_session(self, open_tabs: List[str], active_tab: Optional[str]):
        """
        Save current session state (called on app close).
        
        Args:
            open_tabs: List of currently open file paths
            active_tab: Currently active file path
        """
        self.set(self.KEY_OPEN_TABS, open_tabs)
        self.set(self.KEY_ACTIVE_TAB, active_tab)
        self.save()
        logger.debug(f"Session saved: {len(open_tabs)} tabs, active={active_tab}")
    
    def clear_session(self):
        """Clear saved session (after successful restore)."""
        self.set(self.KEY_OPEN_TABS, [])
        self.set(self.KEY_ACTIVE_TAB, None)

    # =============================================================================
    # UI LAYOUT PERSISTENCE
    # =============================================================================
    
    @property
    def sidebar_collapsed(self) -> bool:
        """Sidebar daraltılmış durumu."""
        return self._settings.get(self.KEY_SIDEBAR_COLLAPSED, False)
    
    @sidebar_collapsed.setter
    def sidebar_collapsed(self, value: bool):
        self.set(self.KEY_SIDEBAR_COLLAPSED, value)
    
    @property
    def inspector_visible(self) -> bool:
        """Inspector panel görünürlük durumu."""
        return self._settings.get(self.KEY_INSPECTOR_VISIBLE, True)
    
    @inspector_visible.setter
    def inspector_visible(self, value: bool):
        self.set(self.KEY_INSPECTOR_VISIBLE, value)
    
    @property
    def inspector_width(self) -> int:
        """Inspector panel genişliği (piksel)."""
        return self._settings.get(self.KEY_INSPECTOR_WIDTH, 300)
    
    @inspector_width.setter
    def inspector_width(self, value: int):
        # Sınırla: 200-500 arası
        value = max(200, min(500, value))
        self.set(self.KEY_INSPECTOR_WIDTH, value)

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
    
    @property
    def keyboard_shortcuts(self) -> Dict[str, str]:
        """Get stored keyboard shortcuts (action_id -> sequence)."""
        return self._settings.get(self.KEY_SHORTCUTS, {})
    
    @keyboard_shortcuts.setter
    def keyboard_shortcuts(self, value: Dict[str, str]):
        self.set(self.KEY_SHORTCUTS, value)
    
    @property
    def keyboard_shortcuts_enabled(self) -> bool:
        """Are custom keyboard shortcuts enabled?"""
        return self._settings.get(self.KEY_SHORTCUTS_ENABLED, True)
    
    @keyboard_shortcuts_enabled.setter
    def keyboard_shortcuts_enabled(self, value: bool):
        self.set(self.KEY_SHORTCUTS_ENABLED, value)
    
    # =========================================================================
    # RETRY POLICY (Stage 14)
    # =========================================================================
    
    @property
    def retry_profile(self) -> str:
        """Get retry profile name."""
        return self._settings.get(self.KEY_RETRY_PROFILE, "Yumuşak")
    
    @retry_profile.setter
    def retry_profile(self, value: str):
        self.set(self.KEY_RETRY_PROFILE, value)
    
    @property
    def batch_chunk_size(self) -> int:
        """Get default batch chunk size."""
        return self._settings.get(self.KEY_BATCH_CHUNK_SIZE, 20)
    
    @batch_chunk_size.setter
    def batch_chunk_size(self, value: int):
        self.set(self.KEY_BATCH_CHUNK_SIZE, max(1, min(100, value)))
    
    # =========================================================================
    # TRANSLATION MEMORY (Stage 16.1)
    # =========================================================================
    
    @property
    def tm_enabled(self) -> bool:
        """Is Translation Memory lookup enabled?"""
        return self._settings.get(self.KEY_TM_ENABLED, True)
    
    @tm_enabled.setter
    def tm_enabled(self, value: bool):
        self.set(self.KEY_TM_ENABLED, value)
    
    @property
    def tm_auto_apply_exact(self) -> bool:
        """Auto-apply exact TM matches during batch translation?"""
        return self._settings.get(self.KEY_TM_AUTO_APPLY_EXACT, True)
    
    @tm_auto_apply_exact.setter
    def tm_auto_apply_exact(self, value: bool):
        self.set(self.KEY_TM_AUTO_APPLY_EXACT, value)
    
    # =========================================================================
    # GLOSSARY (Stage 16.2)
    # =========================================================================
    
    @property
    def glossary_enabled(self) -> bool:
        """Is glossary checking enabled?"""
        return self._settings.get(self.KEY_GLOSSARY_ENABLED, True)
    
    @glossary_enabled.setter
    def glossary_enabled(self, value: bool):
        self.set(self.KEY_GLOSSARY_ENABLED, value)
    
    @property
    def glossary_mode(self) -> str:
        """Glossary mode: 'qc_only' or 'enforce'."""
        return self._settings.get(self.KEY_GLOSSARY_MODE, "qc_only")
    
    @glossary_mode.setter
    def glossary_mode(self, value: str):
        if value not in ("qc_only", "enforce"):
            value = "qc_only"
        self.set(self.KEY_GLOSSARY_MODE, value)
    
    def __repr__(self) -> str:
        return f"SettingsModel(dirty={self._dirty})"
