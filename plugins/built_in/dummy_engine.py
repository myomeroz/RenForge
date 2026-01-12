
from typing import Dict, Any, List
from interfaces.i_plugin import ITranslationEngine, PluginType

class DummyEngine(ITranslationEngine):
    """
    A dummy translation engine for testing and demonstration.
    """
    
    @property
    def id(self) -> str:
        return "renforge.engine.dummy"
        
    @property
    def name(self) -> str:
        return "Dummy Engine (Test)"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    def on_load(self, context: Any) -> None:
        pass
        
    def on_unload(self) -> None:
        pass

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {"key": "prefix", "label": "Prefix", "type": "text", "default": "[TEST] "}
        ]

    def translate(self, text: str, source_lang: str, target_lang: str, config: Dict[str, Any]) -> str:
        prefix = config.get("prefix", "[TEST] ")
        return f"{prefix}{text}"

    def batch_translate(self, items: List[Dict], source_lang: str, target_lang: str, config: Dict[str, Any]) -> List[Dict]:
        results = []
        prefix = config.get("prefix", "[TEST] ")
        for item in items:
            # item has "masked" text
            translated = f"{prefix}{item.get('masked', '')}"
            results.append({"i": item["i"], "t": translated})
        return results

    def get_supported_languages(self) -> List[str]:
        return ["en", "tr", "es", "fr", "de"]
        
    def is_available(self, config: Dict[str, Any]) -> bool:
        return True
