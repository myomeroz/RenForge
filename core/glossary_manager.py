
import re
import json
from renforge_logger import get_logger
import renforge_settings as rf_settings
from core.text_utils import mask_renpy_tokens, unmask_renpy_tokens

logger = get_logger("core.glossary")

class GlossaryManager:
    """
    Manages translation glossary terms and application logic.
    Persists data via renforge_settings.
    """
    
    MODE_EXACT = "exact"
    MODE_CASE_INSENSITIVE = "case" 
    MODE_REGEX = "regex"

    def __init__(self):
        self.terms = []
        self.load_from_settings()

    def load_from_settings(self):
        """Load glossary terms from global settings."""
        settings = rf_settings.load_settings()
        self.terms = settings.get("glossary_terms", [])
        logger.debug(f"Loaded {len(self.terms)} glossary terms.")

    def save_to_settings(self):
        """Save current terms to global settings."""
        settings = rf_settings.load_settings()
        settings["glossary_terms"] = self.terms
        rf_settings.save_settings(settings)

    def add_term(self, source, target, match_mode=MODE_CASE_INSENSITIVE, enabled=True):
        """Add or update a term."""
        # Simple implementation: unique by source
        for term in self.terms:
            if term["source"] == source:
                term["target"] = target
                term["mode"] = match_mode
                term["enabled"] = enabled
                self.save_to_settings()
                return
        
        self.terms.append({
            "source": source,
            "target": target,
            "mode": match_mode,
            "enabled": enabled
        })
        self.save_to_settings()

    def delete_term(self, source):
        """Delete term by source string."""
        self.terms = [t for t in self.terms if t["source"] != source]
        self.save_to_settings()

    def update_term(self, index, data):
        """Update term at specific index."""
        if 0 <= index < len(self.terms):
            self.terms[index] = data
            self.save_to_settings()

    def apply_to_text(self, text):
        """
        Apply enabled glossary terms to text.
        PROTECTS: Ren'Py tokens (like tags and variables) are masked first.
        """
        if not text or not self.terms:
            return text

        # 1. Mask Tokens (Safety First)
        masked_text, token_map = mask_renpy_tokens(text)
        
        # 2. Apply Replacements
        final_text = masked_text
        
        # Sort terms by length (longest first) to avoid partial replacement issues in simple modes
        sorted_terms = sorted(self.terms, key=lambda t: len(t["source"]), reverse=True)

        for term in sorted_terms:
            if not term.get("enabled", True):
                continue

            source = term["source"]
            target = term["target"]
            mode = term.get("mode", self.MODE_CASE_INSENSITIVE)

            try:
                if mode == self.MODE_REGEX:
                    final_text = re.sub(source, target, final_text)
                
                elif mode == self.MODE_CASE_INSENSITIVE:
                    # Case-insensitive replacement using regex
                    pattern = re.escape(source)
                    final_text = re.sub(pattern, target, final_text, flags=re.IGNORECASE)
                    
                else: # MODE_EXACT
                    final_text = final_text.replace(source, target)
            except Exception as e:
                logger.error(f"Error applying glossary term '{source}': {e}")
                continue

        # 3. Unmask
        return unmask_renpy_tokens(final_text, token_map)

    def get_terms(self):
        return self.terms

    def merge_glossary(self, imported_terms: list, strategy: str = "MERGE_PREFER_LOCAL"):
        """
        Merge imported terms into current glossary.
        Strategies:
        - SKIP: Do nothing (should be handled by caller, but safety check)
        - OVERWRITE: Replace entire list
        - MERGE_PREFER_LOCAL: Add new, keep local on conflict
        - MERGE_PREFER_IMPORTED: Add new, overwrite local on conflict
        """
        if strategy == "SKIP":
            return
            
        if strategy == "OVERWRITE":
            self.terms = imported_terms
            self.save_to_settings()
            logger.info(f"Glossary overwritten with {len(self.terms)} terms.")
            return

        # Merge logic
        # Map by source for conflict detection
        local_map = {t["source"]: t for t in self.terms}
        imported_map = {t["source"]: t for t in imported_terms}
        
        merged_map = local_map.copy()
        
        for src, imp_term in imported_map.items():
            if src in merged_map:
                # Conflict
                if strategy == "MERGE_PREFER_IMPORTED":
                    merged_map[src] = imp_term
                # else PREFER_LOCAL: keep existing, do nothing
            else:
                # New term
                merged_map[src] = imp_term
                
        # Reconstruct list
        self.terms = list(merged_map.values())
        self.save_to_settings()
        logger.info(f"Glossary merged. Total terms: {len(self.terms)}")

