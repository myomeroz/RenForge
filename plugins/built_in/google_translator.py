
from typing import Dict, Any, List
from interfaces.i_plugin import ITranslationEngine
from renforge_logger import get_logger

logger = get_logger("plugin.google")

class GoogleTranslatePlugin(ITranslationEngine):
    """
    Google Translate (Free) plugin using deep-translator (or fallback).
    """

    @property
    def id(self) -> str:
        return "renforge.engine.google_free"

    @property
    def name(self) -> str:
        return "Google Translate (Free)"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def on_load(self, context: Any) -> None:
        logger.info("Google Translate Plugin loaded")

    def on_unload(self) -> None:
        pass

    def get_config_schema(self) -> List[Dict[str, Any]]:
        return []

    def translate(self, text: str, source_lang: str, target_lang: str, config: Dict[str, Any]) -> str:
        # Wrap the existing deep_translator logic used in renforge_ai
        # For now, simplistic implementation
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            return translator.translate(text)
        except ImportError:
            logger.error("deep_translator module not found.")
            return text + " [Error: deep_translator missing]"
        except Exception as e:
            logger.error(f"Google Translation failed: {e}")
            raise e

    def batch_translate(self, items: List[Dict], source_lang: str, target_lang: str, config: Dict[str, Any]) -> List[Dict]:
        """
        Naive batch implementation (one by one due to Free API limits usually).
        """
        results = []
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            
            # TODO: Improve with concurrent futures or proper batching if supported
            for item in items:
                masked_text = item.get('masked', '')
                if not masked_text:
                    results.append({"i": item["i"], "t": ""})
                    continue
                    
                try:
                    trans = translator.translate(masked_text)
                    results.append({"i": item["i"], "t": trans})
                except Exception as e:
                    logger.warning(f"Failed to translate item {item['i']}: {e}")
                    results.append({"i": item["i"], "error": str(e)})

        except ImportError:
             for item in items:
                 results.append({"i": item["i"], "error": "deep_translator missing"})
                 
        return results

    def get_supported_languages(self) -> List[str]:
        # Return common codes or dynamically fetch
        return ["en", "tr", "es", "fr", "de", "it", "jp", "ru"]

    def is_available(self, config: Dict[str, Any]) -> bool:
        return True
