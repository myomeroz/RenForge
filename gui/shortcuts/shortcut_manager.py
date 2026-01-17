# -*- coding: utf-8 -*-
"""
RenForge Shortcut Manager

Centralized management for keyboard shortcuts.
Handles registration, settings persistence (via SettingsModel), 
active shortcut binding, and conflict detection.
"""

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut

from renforge_logger import get_logger
from models.settings_model import SettingsModel

logger = get_logger("gui.shortcuts")


class ShortcutManager(QObject):
    """
    Centralized keyboard shortcut manager.
    
    Responsibilities:
    - Maintains a registry of available actions and their default shortcuts.
    - Loads/Saves custom bindings via SettingsModel.
    - Binds handlers to active QShortcuts globally or per-context.
    - Handles conflict detection.
    
    Usage:
        mgr = ShortcutManager.instance()
        mgr.bind(window, "translate.selected", callback_func, context_widget=None)
    """
    
    _instance = None
    
    # Signals
    shortcuts_changed = Signal()
    
    # Default Keybinding Definitions
    # action_id -> {default: str, name: str, desc: str}
    DEFAULT_KEYMAP = {
        "translate.selected": {
            "default": "Ctrl+Return",
            "name": "Seçiliyi Çevir",
            "desc": "Seçili satırları çevirir"
        },
        "translate.batch": {
            "default": "Ctrl+Shift+Return",
            "name": "Toplu Çevir",
            "desc": "Tüm dosyayı toplu çevirir"
        },
        "batch.cancel": {
            "default": "Esc",
            "name": "İşlemi İptal Et",
            "desc": "Devam eden işlemi iptal eder"
        },
        "inspector.toggle": {
            "default": "F6",
            "name": "Inspector Panelini Göster/Gizle",
            "desc": "Sağ panelin görünürlüğünü değiştirir"
        },
        "inspector.log": {
            "default": "Ctrl+L",
            "name": "Log Panelini Aç",
            "desc": "Inspector Log sekmesini açar"
        },
        "inspector.batch": {
            "default": "Ctrl+1",
            "name": "Toplu İşlem Panelini Aç",
            "desc": "Inspector Toplu İşlem sekmesini açar"
        }
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Allow re-init protection if called multiple times, though __new__ handles singleton
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        super().__init__()
        self._settings = SettingsModel.instance()
        
        # Runtime state
        # registered_handlers: list of dicts {
        #   'action_id': str, 
        #   'callback': func, 
        #   'parent': QWidget, 
        #   'shortcut_obj': QShortcut, 
        #   'context': Qt.ShortcutContext
        # }
        self._handlers = []
        
        self._initialize_bindings()
        
        # Listen for setting changes
        self._settings.subscribe(SettingsModel.KEY_SHORTCUTS, self._on_settings_changed)
        self._settings.subscribe(SettingsModel.KEY_SHORTCUTS_ENABLED, self._on_toggle_changed)
        
        self._initialized = True
        logger.debug("ShortcutManager initialized")
    
    @classmethod
    def instance(cls) -> 'ShortcutManager':
        if cls._instance is None:
            cls._instance = ShortcutManager()
        return cls._instance

    def _initialize_bindings(self):
        """Initial load of bindings (doesn't bind Qt objects yet, just ready state)."""
        pass
    
    def get_action_map(self) -> dict:
        """Get dict of all known actions (defaults merged with overrides)."""
        overrides = self._settings.keyboard_shortcuts
        actions = {}
        
        for action_id, info in self.DEFAULT_KEYMAP.items():
            current_seq = overrides.get(action_id, info["default"])
            actions[action_id] = {
                "name": info["name"],
                "desc": info["desc"],
                "default": info["default"],
                "sequence": current_seq
            }
        return actions

    def get_sequence(self, action_id: str) -> str:
        """Get the current key sequence string for an action."""
        if not self._settings.keyboard_shortcuts_enabled:
            return ""
            
        overrides = self._settings.keyboard_shortcuts
        default = self.DEFAULT_KEYMAP.get(action_id, {}).get("default", "")
        return overrides.get(action_id, default)

    def set_sequence(self, action_id: str, sequence_str: str):
        """
        Update the key sequence for an action.
        Persists to settings and refreshes active bindings.
        
        Args:
            action_id: ID to bind
            sequence_str: New sequence or empty string to unbind
        """
        if action_id not in self.DEFAULT_KEYMAP:
            logger.warning(f"Attempt to set unknown action: {action_id}")
            return

        # Check conflict
        conflict_owner = self.check_conflict(sequence_str, exclude_action=action_id)
        if conflict_owner:
            owner_name = self.DEFAULT_KEYMAP[conflict_owner]['name']
            raise ValueError(f"Bu kısayol zaten kullanımda: {owner_name}")
            
        current_map = self._settings.keyboard_shortcuts.copy()
        
        # If new matches default, remove from overrides to keep clean
        default = self.DEFAULT_KEYMAP[action_id]["default"]
        
        if sequence_str == default:
            if action_id in current_map:
                del current_map[action_id]
        else:
            current_map[action_id] = sequence_str
            
        self._settings.keyboard_shortcuts = current_map
        self._settings.save()
        
        # Trigger update
        self.shortcuts_changed.emit()
        self._refresh_handlers()
        
    def reset_default(self, action_id: str):
        """Reset a specific action to default."""
        if action_id in self.DEFAULT_KEYMAP:
            default_seq = self.DEFAULT_KEYMAP[action_id]["default"]
            # To reset, we just need to ensure it's not in overrides map
            current_map = self._settings.keyboard_shortcuts.copy()
            if action_id in current_map:
                del current_map[action_id]
                self._settings.keyboard_shortcuts = current_map
                self._settings.save()
                self.shortcuts_changed.emit()
                self._refresh_handlers()

    def reset_all(self):
        """Reset all shortcuts to defaults."""
        self._settings.keyboard_shortcuts = {}
        self._settings.save()
        self.shortcuts_changed.emit()
        self._refresh_handlers()

    def check_conflict(self, sequence_str: str, exclude_action: str = None) -> str:
        """
        Check if sequence is already used.
        Returns action_id of owner if conflict, else None.
        """
        if not sequence_str:
            return None
            
        test_seq = QKeySequence(sequence_str).toString(QKeySequence.PortableText)
        current_map = self.get_action_map()
        
        for aid, info in current_map.items():
            if aid == exclude_action:
                continue
            
            existing = QKeySequence(info["sequence"]).toString(QKeySequence.PortableText)
            if existing == test_seq:
                return aid
        return None

    def bind(self, parent_widget, action_id: str, callback, 
             context: Qt.ShortcutContext = Qt.WindowShortcut):
        """
        Register and create a live bind for an action.
        
        Args:
            parent_widget: QWidget that owns the shortcut (usually MainWindow)
            action_id: Action ID string
            callback: Slot to call
            context: Shortcut scope
        """
        # Store definition
        handler_def = {
            'action_id': action_id,
            'parent': parent_widget,
            'callback': callback,
            'context': context,
            'shortcut_obj': None
        }
        
        # Create initial QShortcut object
        self._create_shortcut_object(handler_def)
        
        self._handlers.append(handler_def)
        logger.debug(f"Bound action '{action_id}' to {parent_widget}")

    def _create_shortcut_object(self, handler_def):
        """Internal: create QShortcut for a handler definition."""
        seq_str = self.get_sequence(handler_def['action_id'])
        if not seq_str:
            handler_def['shortcut_obj'] = None
            return

        sc = QShortcut(QKeySequence(seq_str), handler_def['parent'])
        sc.setContext(handler_def['context'])
        sc.activated.connect(handler_def['callback'])
        handler_def['shortcut_obj'] = sc
        return sc

    def _refresh_handlers(self):
        """Re-create all QShortcut objects with new key sequences."""
        logger.debug("Refreshing shortcut bindings...")
        enabled = self._settings.keyboard_shortcuts_enabled
        
        for h in self._handlers:
            # Delete old object
            if h['shortcut_obj']:
                h['shortcut_obj'].setEnabled(False)
                h['shortcut_obj'].setParent(None)
                h['shortcut_obj'].deleteLater()
                h['shortcut_obj'] = None
            
            if enabled:
                self._create_shortcut_object(h)

    def _on_settings_changed(self, value):
        """Observer callback for shortcut map changes."""
        self._refresh_handlers()
        
    def _on_toggle_changed(self, value):
        """Observer callback for enabled toggle."""
        self._refresh_handlers()
