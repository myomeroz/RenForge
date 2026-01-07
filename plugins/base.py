# -*- coding: utf-8 -*-
"""
Plugin Base Classes

Defines the interface that all plugins must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

from renforge_logger import get_logger

logger = get_logger("plugins.base")


class PluginType(Enum):
    """Types of plugins supported by RenForge."""
    TRANSLATOR = "translator"      # Translation service plugins
    PARSER = "parser"              # Custom file format parsers
    UI = "ui"                      # UI extension plugins
    EXPORTER = "exporter"          # Export format plugins
    HOOK = "hook"                  # Hook-based event plugins


@dataclass
class PluginInfo:
    """
    Metadata about a plugin.
    
    Attributes:
        id: Unique plugin identifier
        name: Human-readable plugin name
        version: Plugin version string
        description: Short description
        author: Plugin author
        plugin_type: Type of plugin
        dependencies: List of required dependencies
        config_schema: Optional config schema for settings
    """
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.HOOK
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Plugin id is required")
        if not self.name:
            self.name = self.id


class Plugin(ABC):
    """
    Base class for all plugins.
    
    All plugins must inherit from this class and implement
    the required methods.
    
    Example:
        class MyPlugin(Plugin):
            @property
            def info(self) -> PluginInfo:
                return PluginInfo(
                    id="my_plugin",
                    name="My Plugin",
                    version="1.0.0",
                )
            
            def activate(self):
                print("Plugin activated!")
    """
    
    def __init__(self):
        self._is_active = False
        self._config: Dict[str, Any] = {}
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        pass
    
    @property
    def is_active(self) -> bool:
        """Check if plugin is currently active."""
        return self._is_active
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self._config.copy()
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure the plugin.
        
        Args:
            config: Configuration dictionary
        """
        self._config.update(config)
        logger.debug(f"Plugin {self.info.id} configured")
    
    def activate(self):
        """
        Called when plugin is activated.
        
        Override to perform initialization.
        """
        self._is_active = True
        logger.info(f"Plugin activated: {self.info.name} v{self.info.version}")
    
    def deactivate(self):
        """
        Called when plugin is deactivated.
        
        Override to perform cleanup.
        """
        self._is_active = False
        logger.info(f"Plugin deactivated: {self.info.name}")
    
    def __repr__(self) -> str:
        return f"Plugin({self.info.id}, active={self._is_active})"


class TranslatorPlugin(Plugin):
    """
    Base class for translator plugins.
    
    Translator plugins provide custom translation services.
    """
    
    @abstractmethod
    def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Optional[str]:
        """
        Translate text.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text, or None on failure
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.
        
        Returns:
            List of language codes (e.g., ['en', 'tr', 'de'])
        """
        pass
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="base_translator",
            name="Base Translator",
            version="0.0.0",
            plugin_type=PluginType.TRANSLATOR,
        )


class ParserPlugin(Plugin):
    """
    Base class for parser plugins.
    
    Parser plugins provide support for custom file formats.
    """
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        Check if this parser can handle the file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if parser can handle this file
        """
        pass
    
    @abstractmethod
    def parse(self, lines: List[str]) -> List[Any]:
        """
        Parse file lines.
        
        Args:
            lines: File content as lines
            
        Returns:
            List of parsed items
        """
        pass
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="base_parser",
            name="Base Parser",
            version="0.0.0",
            plugin_type=PluginType.PARSER,
        )
