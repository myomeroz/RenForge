# -*- coding: utf-8 -*-
"""
Plugin Hook System

Event-based hook system for plugin integration.
Plugins can register callbacks for various application events.
"""

from enum import Enum
from typing import Callable, Dict, List, Any, Optional

from renforge_logger import get_logger

logger = get_logger("plugins.hooks")


class Hook(Enum):
    """
    Available hooks that plugins can register for.
    
    Hooks are fired at specific points in the application lifecycle.
    """
    # Application lifecycle
    APP_STARTUP = "app_startup"
    APP_SHUTDOWN = "app_shutdown"
    
    # File operations
    FILE_OPENED = "file_opened"
    FILE_SAVED = "file_saved"
    FILE_CLOSED = "file_closed"
    
    # Translation events
    BEFORE_TRANSLATE = "before_translate"
    AFTER_TRANSLATE = "after_translate"
    TRANSLATION_ERROR = "translation_error"
    
    # Parsing events
    BEFORE_PARSE = "before_parse"
    AFTER_PARSE = "after_parse"
    
    # UI events
    TAB_CHANGED = "tab_changed"
    ITEM_SELECTED = "item_selected"
    
    # Settings
    SETTINGS_CHANGED = "settings_changed"


# Type alias for hook callbacks
HookCallback = Callable[..., Any]


class HookManager:
    """
    Manages hook registration and execution.
    
    Provides a simple pub/sub mechanism for plugins to react
    to application events.
    
    Usage:
        manager = HookManager.instance()
        
        # Register a callback
        manager.register(Hook.FILE_OPENED, my_callback)
        
        # Trigger a hook
        manager.trigger(Hook.FILE_OPENED, file_path="/path/to/file.rpy")
    """
    
    _instance: Optional['HookManager'] = None
    
    def __init__(self):
        self._hooks: Dict[Hook, List[HookCallback]] = {h: [] for h in Hook}
    
    @classmethod
    def instance(cls) -> 'HookManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = HookManager()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton (for testing)."""
        cls._instance = None
    
    def register(self, hook: Hook, callback: HookCallback) -> bool:
        """
        Register a callback for a hook.
        
        Args:
            hook: The hook to register for
            callback: Function to call when hook is triggered
            
        Returns:
            True if registered successfully
        """
        if callback in self._hooks[hook]:
            return False  # Already registered
        
        self._hooks[hook].append(callback)
        logger.debug(f"Registered callback for {hook.value}")
        return True
    
    def unregister(self, hook: Hook, callback: HookCallback) -> bool:
        """
        Unregister a callback from a hook.
        
        Args:
            hook: The hook to unregister from
            callback: The callback to remove
            
        Returns:
            True if unregistered successfully
        """
        if callback not in self._hooks[hook]:
            return False
        
        self._hooks[hook].remove(callback)
        logger.debug(f"Unregistered callback from {hook.value}")
        return True
    
    def trigger(self, hook: Hook, **kwargs) -> List[Any]:
        """
        Trigger a hook, calling all registered callbacks.
        
        Args:
            hook: The hook to trigger
            **kwargs: Arguments to pass to callbacks
            
        Returns:
            List of return values from callbacks
        """
        results = []
        
        for callback in self._hooks[hook]:
            try:
                result = callback(**kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook callback error ({hook.value}): {e}")
        
        if self._hooks[hook]:
            logger.debug(f"Triggered {hook.value}: {len(self._hooks[hook])} callbacks")
        
        return results
    
    def trigger_until(self, hook: Hook, stop_value: Any = True, **kwargs) -> Optional[Any]:
        """
        Trigger a hook until a callback returns the stop value.
        
        Useful for hooks where a plugin can "handle" the event
        and prevent further processing.
        
        Args:
            hook: The hook to trigger
            stop_value: Value that causes iteration to stop
            **kwargs: Arguments to pass to callbacks
            
        Returns:
            The value that caused stopping, or None
        """
        for callback in self._hooks[hook]:
            try:
                result = callback(**kwargs)
                if result == stop_value:
                    return result
            except Exception as e:
                logger.error(f"Hook callback error ({hook.value}): {e}")
        
        return None
    
    def get_callback_count(self, hook: Hook) -> int:
        """Get the number of callbacks registered for a hook."""
        return len(self._hooks[hook])
    
    def clear(self, hook: Optional[Hook] = None):
        """
        Clear callbacks.
        
        Args:
            hook: Specific hook to clear, or None for all
        """
        if hook:
            self._hooks[hook] = []
        else:
            self._hooks = {h: [] for h in Hook}
    
    def __repr__(self) -> str:
        total = sum(len(callbacks) for callbacks in self._hooks.values())
        return f"HookManager(callbacks={total})"
