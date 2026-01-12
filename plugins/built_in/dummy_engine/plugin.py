
from typing import Dict, Any, List
from interfaces.i_plugin import ITranslationEngine

class DummyEngine(ITranslationEngine):
    
    def on_load(self, context: Any) -> None:
        pass
        
    def on_unload(self) -> None:
        pass

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return [
            {"key": "prefix", "label": "Prefix", "type": "text", "default": "[TEST] "}
        ]

    def translate_batch(self, 
                        items: List[Dict], 
                        source_lang: str, 
                        target_lang: str, 
                        config: Dict[str, Any],
                        cancel_token: Any = None,
                        timeout: int = 30) -> List[Dict]:
        
        prefix = config.get("prefix", "[TEST] ")
        results = []
        
        for item in items:
            if cancel_token and hasattr(cancel_token, 'is_set') and cancel_token.is_set():
                results.append({"i": item["i"], "error": "Canceled"})
                continue
                
            # Simulate work
            # time.sleep(0.01) 
            
            translated = f"{prefix}{item.get('masked', '')}"
            results.append({"i": item["i"], "t": translated})
            
        return results

    def get_supported_languages(self) -> List[str]:
        return ["en", "tr", "es", "fr", "de"]
        
    def is_available(self, config: Dict[str, Any]) -> bool:
        return True
