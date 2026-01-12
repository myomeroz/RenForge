
from typing import Dict, List, Optional, Any
from core.plugin_manager import PluginManager
from core.text_utils import mask_renpy_tokens, unmask_renpy_tokens
from interfaces.i_plugin import ITranslationEngine
from renforge_logger import get_logger

logger = get_logger("core.translation_service")

class TranslationService:
    """
    Facade for translation operations. Handles:
    1. Plugin selection
    2. Token masking/unmasking (Safety)
    3. Glossary application (Consistency)
    4. Plugin delegation
    """
    
    def __init__(self, settings_model):
        self.settings_model = settings_model
        self.plugin_manager = PluginManager()
        # Lazy load glossary manager to avoid circular deps if any
        self.glossary_manager = None
        
    def _get_active_engine(self) -> Optional[ITranslationEngine]:
        # TODO: Get active engine ID from settings
        # For now, default to dummy or google if not set
        engine_id = self.settings_model.get("active_plugin_engine", "renforge.engine.google_free")
        engine = self.plugin_manager.get_engine(engine_id)
        if not engine:
            logger.warning(f"Active engine '{engine_id}' not found. Falling back to Dummy.")
            engine = self.plugin_manager.get_engine("renforge.engine.dummy")
        return engine

    def _get_engine_config(self, engine_id: str) -> Dict[str, Any]:
        # Retrieve plugin-specific config from settings
        plugins_config = self.settings_model.get("plugins_config", {})
        return plugins_config.get(engine_id, {})

    def batch_translate(self, items: List[Dict], source_lang: str, target_lang: str, 
                       cancel_token: Any = None) -> List[Dict]:
        """
        Process a batch of items with full pipeline:
        1. Tool Pre-processing (TODO)
        2. Core Safety (Masking)
        3. Engine Translation (with Rate Limit & Timeout)
        4. Core Unmasking
        5. Glossary Application
        6. Tool Post-processing (TODO)
        """
        engine = self._get_active_engine()
        if not engine:
            return [{"i": x["i"], "error": "No engine available"} for x in items]
            
        engine_config = self._get_engine_config(engine.id)
        
        # Rate Limiting (Simplistic)
        import time
        rate_limit_delay = float(engine_config.get("rate_limit_ms", 0)) / 1000.0
        if rate_limit_delay > 0:
            time.sleep(rate_limit_delay)
            
        # 1. Mask Tokens (Core Safety)
        masked_items = []
        for item in items:
            masked_text, map_ = mask_renpy_tokens(item["original"])
            masked_items.append({
                "i": item["i"],
                "masked": masked_text,
                "token_map": map_,
                "original": item["original"] 
            })
            
        # 2. Delegate to Plugin
        try:
            # Check API version compatibility or signature
            # Assuming updated plugins implement translate_batch with new signature
            # Fallback for old plugins if we supported mixed versions, but we enforce V1
            results = engine.translate_batch(
                masked_items, 
                source_lang, 
                target_lang, 
                engine_config,
                cancel_token=cancel_token,
                timeout=int(engine_config.get("timeout_sec", 30))
            )
        except Exception as e:
            logger.error(f"Batch translation failed in plugin {engine.name}: {e}")
            return [{"i": x["i"], "error": str(e)} for x in items]
            
        # 3. Process Results (Unmask + Glossary)
        final_results = []
        
        # Ensure Glossary Manager is ready
        if not self.glossary_manager:
            try:
                from core.glossary_manager import GlossaryManager
                self.glossary_manager = GlossaryManager()
            except Exception as e:
                logger.error(f"Failed to load GlossaryManager: {e}")

        # Map results by index for easy lookup
        result_map = {r["i"]: r for r in results}
        
        for m_item in masked_items:
            idx = m_item["i"]
            res = result_map.get(idx)
            
            if not res or "error" in res:
                final_results.append({
                    "i": idx, 
                    "error": res.get("error", "No result returned") if res else "Missing result"
                })
                continue
                
            translated_masked = res.get("t", "")
            
            # Unmask
            final_text = unmask_renpy_tokens(translated_masked, m_item["token_map"])
            
            # Apply Glossary (Post Processor)
            if self.glossary_manager:
                try:
                    final_text = self.glossary_manager.apply_to_text(final_text)
                except Exception as gl_err:
                    logger.warning(f"Glossary application failed for item {idx}: {gl_err}")
            
            # TODO: Run other Post-Process Tools
            
            final_results.append({"i": idx, "t": final_text})
            
        return final_results
