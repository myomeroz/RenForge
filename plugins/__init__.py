# -*- coding: utf-8 -*-
"""
RenForge Plugin System

Extensible plugin architecture for adding new features:
- Custom translators (Ollama, DeepL, etc.)
- Custom parsers for new file formats
- UI extensions
"""

from plugins.base import Plugin, PluginInfo, PluginType
from plugins.loader import PluginLoader, PluginManager
from plugins.hooks import HookManager, Hook

__all__ = [
    'Plugin',
    'PluginInfo',
    'PluginType',
    'PluginLoader',
    'PluginManager',
    'HookManager',
    'Hook',
]
