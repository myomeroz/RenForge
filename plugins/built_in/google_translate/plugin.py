
from typing import Dict, Any, List
from interfaces.i_plugin import ITranslationEngine
from renforge_logger import get_logger

logger = get_logger("plugin.google")

class GoogleTranslatePlugin(ITranslationEngine):

    def on_load(self, context: Any) -> None:
        logger.info("Google Translate Plugin loaded")

    def on_unload(self) -> None:
        pass

    def get_config_schema(self) -> List[Dict[str, Any]]:
        # No special config for Google Translate (Free)
        return []

    def translate_batch(self, 
                        items: List[Dict], 
                        source_lang: str, 
                        target_lang: str, 
                        config: Dict[str, Any],
                        cancel_token: Any = None,
                        timeout: int = 30) -> List[Dict]:
        results = []
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            
            for item in items:
                if cancel_token and hasattr(cancel_token, 'is_set') and cancel_token.is_set():
                    results.append({"i": item["i"], "error": "Canceled"})
                    continue

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
        except Exception as e:
             logger.error(f"Google Engine Error: {e}")
             for item in items:
                 results.append({"i": item["i"], "error": str(e)})
                 
        return results

    def get_supported_languages(self) -> List[str]:
        return ["en", "tr", "es", "fr", "de", "it", "jp", "ru"]

    def is_available(self, config: Dict[str, Any]) -> bool:
        return True
