
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Callable

# Core API Version - Increment if breaking changes occur
RENFORGE_PLUGIN_API_VERSION = 1

class PluginType(Enum):
    ENGINE = "engine"
    TOOL = "tool"

class IPlugin(ABC):
    """
    Base interface for all RenForge plugins.
    Properties are populated from manifest.json on load.
    """
    
    def __init__(self):
        self.manifest: Dict[str, Any] = {}
        self.context: Any = None

    @property
    def id(self) -> str:
        return self.manifest.get("id", "unknown")
        
    @property
    def name(self) -> str:
        return self.manifest.get("name", "Unknown")
        
    @property
    def version(self) -> str:
        return self.manifest.get("version", "0.0.0")
        
    @property
    def plugin_type(self) -> PluginType:
        type_str = self.manifest.get("type", "engine")
        return PluginType(type_str)
        
    @abstractmethod
    def on_load(self, context: Any) -> None:
        """
        Initialize plugin. 
        context: PluginContext (logger, config_accessor, etc.)
        """
        pass
        
    @abstractmethod
    def on_unload(self) -> None:
        pass

class ITranslationEngine(IPlugin):
    """
    Interface for translation engines.
    """
    
    @abstractmethod
    def translate_batch(self, 
                        items: List[Dict], 
                        source_lang: str, 
                        target_lang: str, 
                        config: Dict[str, Any],
                        cancel_token: Any = None,
                        timeout: int = 30) -> List[Dict]:
        """
        Batch translate items with cancellation and timeout.
        
        Args:
            items: [{"i": i, "text": "...", "masked": "..."}]
            cancel_token: Object with .is_set() method (e.g. threading.Event)
            timeout: Seconds before giving up.
            
        Returns: 
            List[Dict]: [{"i": i, "t": "...", "error": "..."}]
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        pass
        
    @abstractmethod
    def is_available(self, config: Dict[str, Any]) -> bool:
        pass

class IToolPlugin(IPlugin):
    """
    Interface for processing tools (Pre/Post processors).
    """
    
    @abstractmethod
    def process(self, text: str, context: Dict[str, Any]) -> str:
        """
        Transform text.
        context keys: 'source_lang', 'target_lang', 'is_pre_process', 'item_data'
        """
        return text
