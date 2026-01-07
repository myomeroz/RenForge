# -*- coding: utf-8 -*-
"""
Plugin Loader and Manager

Handles plugin discovery, loading, and lifecycle management.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from renforge_logger import get_logger
from plugins.base import Plugin, PluginInfo, PluginType

logger = get_logger("plugins.loader")


class PluginLoader:
    """
    Loads plugins from a directory.
    
    Searches for Python files containing Plugin subclasses.
    """
    
    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        Initialize the loader.
        
        Args:
            plugin_dir: Directory to search for plugins
        """
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent / "installed"
        self.plugin_dir = Path(plugin_dir)
    
    def discover(self) -> List[Type[Plugin]]:
        """
        Discover all plugins in the plugin directory.
        
        Returns:
            List of Plugin classes found
        """
        if not self.plugin_dir.exists():
            logger.debug(f"Plugin directory not found: {self.plugin_dir}")
            return []
        
        plugins = []
        
        for py_file in self.plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            
            try:
                plugin_class = self._load_plugin_file(py_file)
                if plugin_class:
                    plugins.append(plugin_class)
            except Exception as e:
                logger.error(f"Error loading plugin {py_file.name}: {e}")
        
        logger.info(f"Discovered {len(plugins)} plugins")
        return plugins
    
    def _load_plugin_file(self, path: Path) -> Optional[Type[Plugin]]:
        """Load a plugin from a Python file."""
        module_name = f"plugins.installed.{path.stem}"
        
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find Plugin subclasses in the module
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, Plugin) and 
                obj is not Plugin):
                logger.debug(f"Found plugin class: {name}")
                return obj
        
        return None
    
    def load_from_path(self, path: str) -> Optional[Type[Plugin]]:
        """
        Load a specific plugin file.
        
        Args:
            path: Path to the plugin file
            
        Returns:
            Plugin class, or None on failure
        """
        return self._load_plugin_file(Path(path))


class PluginManager:
    """
    Manages plugin lifecycle and registration.
    
    Provides methods to:
    - Register and unregister plugins
    - Activate and deactivate plugins
    - Query plugins by type
    """
    
    _instance: Optional['PluginManager'] = None
    
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._active_plugins: Dict[str, Plugin] = {}
        self._loader = PluginLoader()
    
    @classmethod
    def instance(cls) -> 'PluginManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = PluginManager()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton (for testing)."""
        cls._instance = None
    
    def register(self, plugin: Plugin) -> bool:
        """
        Register a plugin.
        
        Args:
            plugin: Plugin instance to register
            
        Returns:
            True if registered successfully
        """
        plugin_id = plugin.info.id
        
        if plugin_id in self._plugins:
            logger.warning(f"Plugin already registered: {plugin_id}")
            return False
        
        self._plugins[plugin_id] = plugin
        logger.info(f"Registered plugin: {plugin.info.name}")
        return True
    
    def unregister(self, plugin_id: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            plugin_id: ID of plugin to unregister
            
        Returns:
            True if unregistered successfully
        """
        if plugin_id not in self._plugins:
            return False
        
        # Deactivate if active
        if plugin_id in self._active_plugins:
            self.deactivate(plugin_id)
        
        del self._plugins[plugin_id]
        logger.info(f"Unregistered plugin: {plugin_id}")
        return True
    
    def activate(self, plugin_id: str) -> bool:
        """
        Activate a registered plugin.
        
        Args:
            plugin_id: ID of plugin to activate
            
        Returns:
            True if activated successfully
        """
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False
        
        if plugin_id in self._active_plugins:
            return True  # Already active
        
        plugin = self._plugins[plugin_id]
        try:
            plugin.activate()
            self._active_plugins[plugin_id] = plugin
            return True
        except Exception as e:
            logger.error(f"Failed to activate plugin {plugin_id}: {e}")
            return False
    
    def deactivate(self, plugin_id: str) -> bool:
        """
        Deactivate a plugin.
        
        Args:
            plugin_id: ID of plugin to deactivate
            
        Returns:
            True if deactivated successfully
        """
        if plugin_id not in self._active_plugins:
            return True
        
        plugin = self._active_plugins[plugin_id]
        try:
            plugin.deactivate()
            del self._active_plugins[plugin_id]
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type."""
        return [
            p for p in self._plugins.values()
            if p.info.plugin_type == plugin_type
        ]
    
    def get_active_plugins(self) -> List[Plugin]:
        """Get all active plugins."""
        return list(self._active_plugins.values())
    
    def discover_and_register(self):
        """Discover plugins and register them."""
        plugin_classes = self._loader.discover()
        
        for plugin_class in plugin_classes:
            try:
                plugin = plugin_class()
                self.register(plugin)
            except Exception as e:
                logger.error(f"Failed to instantiate plugin: {e}")
    
    @property
    def registered_count(self) -> int:
        """Get number of registered plugins."""
        return len(self._plugins)
    
    @property
    def active_count(self) -> int:
        """Get number of active plugins."""
        return len(self._active_plugins)
    
    def __repr__(self) -> str:
        return f"PluginManager(registered={self.registered_count}, active={self.active_count})"
