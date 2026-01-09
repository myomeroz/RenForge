import sys
import os
import time
import re
import json
import random
from pathlib import Path
import socket

from renforge_logger import get_logger
logger = get_logger("ai")

import renforge_config as config
import renforge_settings as set
from renforge_exceptions import APIKeyError, ModelError, TranslationError, NetworkError

genai = None
GoogleTranslator = None
gemini_model = None
_loaded_api_key = None 
_available_models_cache = None 
no_ai = False 

def is_internet_available(host="8.8.8.8", port=53, timeout=1):

    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        logger.debug("[is_internet_available] Check successful.")
        return True
    except socket.error as ex:
        logger.debug(f"[is_internet_available] Check failed: {ex}")
        return False

def _lazy_import_genai():

    global genai, no_ai

    if 'google.generativeai' in sys.modules and genai is not None:
        return genai

    if genai is None:
        try:
            logger.debug("Lazy importing google.generativeai...")
            import google.generativeai as genai_local
            genai = genai_local
            logger.debug("Lazy import successful: google.generativeai")
            no_ai = False 
            return genai
        except ImportError:
            logger.error("Failed to lazy import google.generativeai. AI features disabled.")

            try:
                from PyQt6.QtWidgets import QApplication, QMessageBox

                is_gui_running = QApplication.instance() is not None
                if is_gui_running:
                     QMessageBox.critical(None, "Ошибка импорта",
                                       "Не удалось импортировать библиотеку 'google-generativeai'.\n"
                                       "Установите ее: pip install google-generativeai\n"
                                       "Функции ИИ будут недоступны.")
            except ImportError:
                 logger.info("PyQt6 not found, skipping GUI warning for google.generativeai import error.")
            no_ai = True 
            return None
    return genai

def _lazy_import_translator():

    global GoogleTranslator

    if 'deep_translator' in sys.modules and GoogleTranslator is not None:
        return GoogleTranslator

    if GoogleTranslator is None:
        try:
            logger.debug("Lazy importing deep_translator...")
            from deep_translator import GoogleTranslator as Translator_local
            GoogleTranslator = Translator_local
            logger.debug("Lazy import successful: deep_translator.GoogleTranslator")
            return GoogleTranslator
        except ImportError:
            logger.error("Failed to lazy import deep_translator. Translate features disabled.")

            try:
                from PyQt6.QtWidgets import QApplication, QMessageBox
                is_gui_running = QApplication.instance() is not None
                if is_gui_running:
                    QMessageBox.critical(None, "Ошибка импорта",
                                   "Не удалось импортировать библиотеку 'deep-translator'.\n"
                                   "Установите ее: pip install deep-translator\n"
                                   "Функции перевода Google будут недоступны.")
            except ImportError:
                 logger.info("PyQt6 not found, skipping GUI warning for deep_translator import error.")
            return None 
    return GoogleTranslator

# =============================================================================
# BATCH TRANSLATION UTILITIES - Token Masking and Validation
# =============================================================================

# Patterns to protect during translation (Ren'Py tags, placeholders, formatting)
RENPY_TOKEN_PATTERNS = [
    r'\{i\}', r'\{/i\}',           # Italic tags
    r'\{b\}', r'\{/b\}',           # Bold tags  
    r'\{u\}', r'\{/u\}',           # Underline tags
    r'\{s\}', r'\{/s\}',           # Strikethrough tags
    r'\{color=[^}]+\}', r'\{/color\}',  # Color tags
    r'\{size=[^}]+\}', r'\{/size\}',    # Size tags
    r'\{font=[^}]+\}', r'\{/font\}',    # Font tags
    r'\{w(?:=[\d.]+)?\}',          # Wait tags {w} {w=0.5}
    r'\{p(?:=[\d.]+)?\}',          # Pause tags {p} {p=1.0}
    r'\{nw\}',                     # No-wait tag
    r'\{fast\}',                   # Fast display
    r'\{cps=\d+\}', r'\{/cps\}',   # Characters per second
    r'\[[^\]]+\]',                 # Variable placeholders [name] [player]
    r'%\([^)]+\)[sd]',             # Python format %(name)s %(count)d
    r'%[sd]',                      # Simple Python format %s %d
    r'\{\d+\}',                    # Positional format {0} {1}
]

# Compiled pattern for efficiency
_TOKEN_REGEX = None

def _get_token_regex():
    """Get compiled regex for all token patterns."""
    global _TOKEN_REGEX
    if _TOKEN_REGEX is None:
        combined = '|'.join(f'({p})' for p in RENPY_TOKEN_PATTERNS)
        _TOKEN_REGEX = re.compile(combined)
    return _TOKEN_REGEX


def mask_renpy_tokens(text: str) -> tuple:
    """
    Replace Ren'Py tokens with masked placeholders ⟦T0⟧, ⟦T1⟧, etc.
    
    Args:
        text: Original text with Ren'Py tokens
        
    Returns:
        Tuple of (masked_text, token_map) where token_map is {placeholder: original}
    """
    if not text:
        return text, {}
    
    token_map = {}
    counter = [0]  # Use list for closure mutability
    
    def replacer(match):
        token = match.group(0)
        placeholder = f"⟦T{counter[0]}⟧"
        token_map[placeholder] = token
        counter[0] += 1
        return placeholder
    
    regex = _get_token_regex()
    masked_text = regex.sub(replacer, text)
    
    return masked_text, token_map


def unmask_renpy_tokens(text: str, token_map: dict) -> str:
    """
    Restore masked placeholders ⟦T0⟧ back to original Ren'Py tokens.
    
    Args:
        text: Text with masked placeholders
        token_map: Map of {placeholder: original_token}
        
    Returns:
        Text with original tokens restored
    """
    if not text or not token_map:
        return text
    
    result = text
    for placeholder, original in token_map.items():
        result = result.replace(placeholder, original)
    
    return result


def validate_tokens_preserved(original: str, translated: str, token_map: dict) -> list:
    """
    Check if all masked tokens survived translation.
    
    Args:
        original: Original text (with tokens)
        translated: Translated text (should have same placeholders or tokens)
        token_map: The token map from masking
        
    Returns:
        List of missing placeholder strings (empty if all preserved)
    """
    missing = []
    for placeholder in token_map.keys():
        if placeholder not in translated:
            missing.append(placeholder)
    return missing


def validate_translation_output(original: str, translated: str) -> tuple:
    """
    Validate translation output quality.
    
    Args:
        original: Original source text
        translated: Translation from AI
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not translated:
        return False, "Empty translation"
    
    translated = translated.strip()
    
    if not translated:
        return False, "Translation is only whitespace"
    
    # Check for truncation (translation too short relative to original)
    # Allow short translations for short originals
    min_ratio = 0.2 if len(original) > 20 else 0.1
    if len(translated) < len(original) * min_ratio and len(original) > 5:
        return False, f"Translation too short: {len(translated)} vs {len(original)} chars"
    
    # Check if first character is suspicious (starts with punctuation when original doesn't)
    if original and translated:
        orig_starts_punct = original[0] in '.,!?;:-"\''
        trans_starts_punct = translated[0] in '.,!?;:-"\''
        if trans_starts_punct and not orig_starts_punct:
            return False, f"Translation starts with unexpected punctuation: '{translated[0]}'"
    
    return True, None


# =============================================================================
# RATE LIMITING AND BATCH TRANSLATION
# =============================================================================

# Chunk size limits for batch translation
BATCH_CHUNK_MAX_CHARS = 6000  # Max characters per chunk
BATCH_CHUNK_MAX_ITEMS = 50    # Max items per chunk


def _call_gemini_with_backoff(prompt: str, max_retries: int = 4, json_mode: bool = False) -> tuple:
    """
    Call Gemini with exponential backoff + jitter on rate limits/errors.
    
    Args:
        prompt: The prompt to send to Gemini
        max_retries: Maximum number of retry attempts
        json_mode: If True, force JSON output mode
        
    Returns:
        Tuple of (response_text, error_message)
    """
    global gemini_model, no_ai
    
    if no_ai or gemini_model is None:
        return (None, "Gemini model not initialized")
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    # Generation config for JSON mode
    generation_config = None
    if json_mode:
        try:
            generation_config = {"response_mime_type": "application/json"}
        except Exception:
            pass  # SDK version may not support it
    
    for attempt in range(max_retries):
        try:
            if generation_config:
                response = gemini_model.generate_content(
                    prompt, 
                    safety_settings=safety_settings,
                    generation_config=generation_config
                )
            else:
                response = gemini_model.generate_content(prompt, safety_settings=safety_settings)
            
            if not response.parts:
                logger.warning(f"[_call_gemini_with_backoff] Empty response (attempt {attempt+1})")
                if attempt + 1 < max_retries:
                    time.sleep(1)
                    continue
                return (None, "Empty response from Gemini")
            
            return (response.text.strip(), None)
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit or transient errors
            is_retryable = any(keyword in error_str for keyword in [
                "429", "503", "quota", "rate", "limit", "timeout", 
                "deadline", "unavailable", "resource exhausted"
            ])
            
            if is_retryable and attempt + 1 < max_retries:
                # Exponential backoff with jitter
                delay = min(2 ** attempt + random.uniform(0, 1), 30)
                logger.warning(f"[_call_gemini_with_backoff] Rate limit/error, retrying in {delay:.1f}s: {e}")
                time.sleep(delay)
                continue
            
            logger.error(f"[_call_gemini_with_backoff] Final error: {e}")
            return (None, str(e))
    
    return (None, "Max retries exceeded")


def translate_text_batch_gemini_strict(
    items: list,
    source_lang: str,
    target_lang: str,
    model: str = None,
    glossary: dict = None
) -> dict:
    """
    Batch translate multiple items with strict JSON contract.
    
    This function:
    - Masks Ren'Py tokens to protect them during translation
    - Uses chunking for large batches
    - Validates token preservation
    - Retries with repair prompt on validation failure
    - Falls back to original text on final failure (safe mode)
    
    Args:
        items: List of strings to translate
        source_lang: Source language (e.g., 'english', 'auto' for auto-detect)
        target_lang: Target language (e.g., 'turkish')
        model: Optional model name (uses current gemini_model)
        glossary: Optional dict of term mappings {source_term: target_term}
        
    Returns:
        {
          "translations": [{"i": 0, "t": "translated text"}, ...],
          "meta": {"model": "...", "source_lang": "...", "target_lang": "..."},
          "errors": [{"i": idx, "error": "..."}, ...]  # failed items
        }
    """
    global gemini_model, no_ai
    
    result = {
        "translations": [],
        "meta": {
            "model": model or (gemini_model.model_name if gemini_model else "unknown"),
            "source_lang": source_lang,
            "target_lang": target_lang
        },
        "errors": [],
        "stats": {
            "total": len(items),
            "success": 0,
            "failed": 0,
            "fallback": 0,  # Items where original was kept due to validation failure
            "retried": 0,   # Items that required repair prompt
            "empty_skipped": 0
        }
    }
    
    if no_ai or gemini_model is None:
        for i, item in enumerate(items):
            result["errors"].append({"i": i, "error": "Gemini not initialized"})
        result["stats"]["failed"] = len(items)
        return result
    
    if not is_internet_available():
        for i, item in enumerate(items):
            result["errors"].append({"i": i, "error": "No internet connection"})
        result["stats"]["failed"] = len(items)
        return result
    
    if not items:
        return result
    
    # Prepare items with masking
    prepared_items = []
    for i, text in enumerate(items):
        if not text or not text.strip():
            # Empty items get empty translation
            result["translations"].append({"i": i, "t": ""})
            result["stats"]["empty_skipped"] += 1
            continue
        
        masked_text, token_map = mask_renpy_tokens(text)
        prepared_items.append({
            "i": i,
            "original": text,
            "masked": masked_text,
            "token_map": token_map
        })
    
    if not prepared_items:
        return result
    
    # Split into chunks
    chunks = _split_into_chunks(prepared_items)
    total_chunks = len(chunks)
    logger.info(f"[translate_batch_strict] Processing {len(prepared_items)} items in {total_chunks} chunks")
    
    for chunk_idx, chunk in enumerate(chunks):
        chunk_start = time.time()
        chunk_result = _translate_chunk(chunk, source_lang, target_lang, glossary)
        chunk_time = time.time() - chunk_start
        
        # Merge results
        result["translations"].extend(chunk_result["translations"])
        result["errors"].extend(chunk_result["errors"])
        
        # Merge stats
        for key in ["success", "failed", "fallback", "retried"]:
            result["stats"][key] += chunk_result["stats"].get(key, 0)
        
        # Log chunk summary
        cs = chunk_result["stats"]
        logger.info(f"[translate_batch_strict] Chunk {chunk_idx+1}/{total_chunks}: "
                   f"success={cs.get('success', 0)}, failed={cs.get('failed', 0)}, "
                   f"fallback={cs.get('fallback', 0)}, time={chunk_time:.2f}s")
        
        # Small delay between chunks
        if chunk_idx + 1 < total_chunks:
            time.sleep(0.5)
    
    # Sort translations by index
    result["translations"].sort(key=lambda x: x["i"])
    
    # Log final summary
    s = result["stats"]
    logger.info(f"[translate_batch_strict] DONE: total={s['total']}, success={s['success']}, "
               f"failed={s['failed']}, fallback={s['fallback']}, retried={s['retried']}")
    
    return result


def _split_into_chunks(items: list) -> list:
    """Split items into chunks respecting size limits."""
    chunks = []
    current_chunk = []
    current_chars = 0
    
    for item in items:
        item_chars = len(item["masked"])
        
        # Check if adding this item would exceed limits
        if current_chunk and (
            current_chars + item_chars > BATCH_CHUNK_MAX_CHARS or 
            len(current_chunk) >= BATCH_CHUNK_MAX_ITEMS
        ):
            chunks.append(current_chunk)
            current_chunk = []
            current_chars = 0
        
        current_chunk.append(item)
        current_chars += item_chars
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def _translate_chunk(chunk: list, source_lang: str, target_lang: str, glossary: dict = None) -> dict:
    """Translate a single chunk of items with retry logic."""
    result = {
        "translations": [], 
        "errors": [],
        "stats": {"success": 0, "failed": 0, "fallback": 0, "retried": 0}
    }
    
    # Build source language instruction
    source_instruction = f"from {source_lang}" if source_lang.lower() != "auto" else "(auto-detect source language)"
    
    # Build glossary instruction
    glossary_instruction = ""
    if glossary:
        terms = ", ".join([f"{k}→{v}" for k, v in glossary.items()])
        glossary_instruction = f"\n- Use these term mappings: {terms}"
    
    # Build indexed source list
    items_json = json.dumps([{"i": item["i"], "s": item["masked"]} for item in chunk], ensure_ascii=False)
    
    # Collect all tokens for repair prompts
    all_tokens = set()
    for item in chunk:
        all_tokens.update(item["token_map"].keys())
    tokens_str = ', '.join(sorted(all_tokens)) if all_tokens else "(none)"
    
    base_prompt = f"""You are a strict translation engine for Ren'Py visual novel scripts.

TASK: Translate the following texts {source_instruction} to {target_lang}.

RULES:
1. Output MUST be valid JSON only: {{"translations":[{{"i":0,"t":"..."}},{{"i":1,"t":"..."}}]}}
2. Preserve ALL placeholders exactly: ⟦T0⟧, ⟦T1⟧, etc. - these MUST appear in the translation.
3. Keep punctuation, spacing, and formatting intact.
4. Translate naturally while maintaining original meaning and tone.
5. NO explanations, NO markdown, ONLY the JSON object.{glossary_instruction}

SOURCE TEXTS:
{items_json}

OUTPUT (JSON only):"""

    # Retry loop: up to 2 retries (3 total attempts)
    MAX_SCHEMA_RETRIES = 2
    translations = None
    last_response = None
    last_error = None
    
    for attempt in range(MAX_SCHEMA_RETRIES + 1):
        if attempt == 0:
            prompt = base_prompt
        else:
            # Repair prompt for retries
            logger.warning(f"[translate_chunk] Retry attempt {attempt}/{MAX_SCHEMA_RETRIES} due to parse/schema error")
            prompt = f"""Your previous response was INVALID. You MUST output JSON ONLY.

REQUIRED JSON SCHEMA (EXACT FORMAT):
{{"translations":[{{"i":0,"t":"translated text"}},{{"i":1,"t":"translated text"}}]}}

CRITICAL RULES:
- Output ONLY the JSON object, nothing else
- Each item must have "i" (index) and "t" (translation)
- DO NOT use {{"translation":"..."}} format - this is WRONG
- Include these tokens in translations: {tokens_str}

Your failed response started with: {last_response[:200] if last_response else 'N/A'}...

{base_prompt}"""
        
        response_text, error = _call_gemini_with_backoff(prompt, json_mode=True)
        
        if error:
            last_error = error
            logger.warning(f"[translate_chunk] API error on attempt {attempt+1}: {error}")
            continue
        
        last_response = response_text
        
        # Parse and validate schema
        translations = _parse_batch_response_strict(response_text)
        
        if translations is not None:
            # Success! Log if we retried
            if attempt > 0:
                logger.info(f"[translate_chunk] Schema parse succeeded on attempt {attempt+1}")
                result["stats"]["retried"] += len(chunk)
            break
        else:
            logger.warning(f"[translate_chunk] Schema validation failed on attempt {attempt+1}")
    
    # If all attempts failed, fallback all items to original
    if translations is None:
        logger.error(f"[translate_chunk] All {MAX_SCHEMA_RETRIES+1} attempts failed, falling back to original for {len(chunk)} items")
        for item in chunk:
            error_reason = last_error or "JSON schema validation failed after retries"
            logger.info(f"[translate_chunk] Fallback kept original for i={item['i']} reason={error_reason}")
            result["translations"].append({
                "i": item["i"], 
                "t": item["original"],
                "fallback": True,
                "error_reason": error_reason
            })
            result["errors"].append({"i": item["i"], "error": error_reason})
        result["stats"]["fallback"] = len(chunk)
        return result
    
    # Process each translation
    translated_indices = {t["i"]: t["t"] for t in translations}
    
    for item in chunk:
        idx = item["i"]
        
        if idx not in translated_indices:
            # Missing translation, use original as fallback
            error_reason = "Translation missing from response"
            logger.info(f"[translate_chunk] Fallback kept original for i={idx} reason={error_reason}")
            result["translations"].append({
                "i": idx, 
                "t": item["original"],
                "fallback": True,
                "error_reason": error_reason
            })
            result["errors"].append({"i": idx, "error": error_reason})
            result["stats"]["fallback"] += 1
            continue
        
        translated_masked = translated_indices[idx]
        
        # Validate token preservation
        missing_tokens = validate_tokens_preserved(item["masked"], translated_masked, item["token_map"])
        item_retried = False
        
        if missing_tokens:
            # Try to repair single item
            repaired = _repair_single_item(item, translated_masked, missing_tokens, target_lang)
            if repaired:
                translated_masked = repaired
                item_retried = True
                result["stats"]["retried"] += 1
            else:
                # Fallback to original
                error_reason = f"Missing tokens: {missing_tokens}"
                logger.info(f"[translate_chunk] Fallback kept original for i={idx} reason={error_reason}")
                result["translations"].append({
                    "i": idx, 
                    "t": item["original"],
                    "fallback": True,
                    "error_reason": error_reason
                })
                result["errors"].append({"i": idx, "error": error_reason})
                result["stats"]["fallback"] += 1
                continue
        
        # Unmask and clean up
        final_translation = unmask_renpy_tokens(translated_masked, item["token_map"])
        
        # Post-processing cleanup
        if final_translation:
            # Handle leading colon (always strip, never valid)
            if final_translation.startswith(":"):
                final_translation = final_translation.lstrip(": ").strip()
            
            # Handle leading dash/em-dash: only if original didn't have it
            original_starts_dash = item["original"].startswith("-") or item["original"].startswith("—")
            trans_starts_dash = final_translation.startswith("-") or final_translation.startswith("—")
            
            if trans_starts_dash and not original_starts_dash:
                # Try repair prompt to remove leading dash
                repair_result = _repair_leading_punctuation(final_translation, item["original"], target_lang)
                if repair_result:
                    final_translation = repair_result
                    result["stats"]["retried"] += 1
                else:
                    # Accept anyway but log warning (don't count as fallback)
                    logger.warning(f"[translate_chunk] i={idx} has leading dash not in original (accepted with warning)")
        
        result["translations"].append({"i": idx, "t": final_translation})
        result["stats"]["success"] += 1
    
    return result


def _repair_leading_punctuation(translation: str, original: str, target_lang: str) -> str:
    """
    Try to repair a translation that has unexpected leading punctuation.
    
    Returns:
        Repaired translation, or None if repair failed/unchanged
    """
    repair_prompt = f"""The translation below incorrectly starts with a dash/hyphen that was not in the original.
Remove the leading punctuation unless the original text requires it.

Original: {original}
Translation with error: {translation}

Output ONLY the corrected translation to {target_lang}, nothing else:"""
    
    response_text, error = _call_gemini_with_backoff(repair_prompt, max_retries=1)
    if error:
        return None
    
    response_text = response_text.strip()
    
    # Check if it actually removed the dash
    if response_text and not response_text.startswith("-") and not response_text.startswith("—"):
        return response_text
    
    # Repair didn't help
    return None


def _parse_batch_response_strict(response_text: str) -> list:
    """
    Parse batch translation response with STRICT schema validation.
    Rejects {"translation": ...} format - only accepts {"translations": [...]}
    
    Returns:
        List of {"i": idx, "t": text} or None if invalid
    """
    if not response_text:
        return None
    
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split('\n')
            lines = [l for l in lines if not l.startswith("```")]
            text = '\n'.join(lines).strip()
        
        data = json.loads(text)
        
        # STRICT: Must have "translations" key (plural), not "translation" (singular)
        if isinstance(data, dict):
            if "translation" in data and "translations" not in data:
                # WRONG SCHEMA - single translation format, reject it
                logger.warning("[_parse_batch_response_strict] Rejected wrong schema: found 'translation' instead of 'translations'")
                return None
            
            if "translations" in data:
                translations = data["translations"]
                if isinstance(translations, list):
                    # Validate each item has required fields
                    valid_items = []
                    for item in translations:
                        if isinstance(item, dict) and "i" in item and "t" in item:
                            valid_items.append({"i": item["i"], "t": item["t"]})
                    if valid_items:
                        return valid_items
                    else:
                        logger.warning("[_parse_batch_response_strict] No valid items in translations array")
                        return None
        
        # Allow bare list format as fallback
        if isinstance(data, list):
            valid_items = []
            for item in data:
                if isinstance(item, dict) and "i" in item and "t" in item:
                    valid_items.append({"i": item["i"], "t": item["t"]})
            if valid_items:
                return valid_items
        
    except json.JSONDecodeError as e:
        logger.warning(f"[_parse_batch_response_strict] JSON decode error: {e}")
        # Try regex extraction as last resort
        pattern = r'\{"i"\s*:\s*(\d+)\s*,\s*"t"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\}'
        matches = re.findall(pattern, response_text)
        if matches:
            logger.info(f"[_parse_batch_response_strict] Recovered {len(matches)} items via regex")
            return [{"i": int(m[0]), "t": m[1].replace('\\"', '"')} for m in matches]
    
    return None


def _parse_batch_response(response_text: str) -> list:
    """Parse batch translation response JSON."""
    if not response_text:
        return None
    
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split('\n')
            lines = [l for l in lines if not l.startswith("```")]
            text = '\n'.join(lines).strip()
        
        data = json.loads(text)
        
        if isinstance(data, dict) and "translations" in data:
            return data["translations"]
        elif isinstance(data, list):
            return data
        
    except json.JSONDecodeError:
        # Try regex extraction
        pattern = r'\{"i"\s*:\s*(\d+)\s*,\s*"t"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\}'
        matches = re.findall(pattern, response_text)
        if matches:
            return [{"i": int(m[0]), "t": m[1].replace('\\"', '"')} for m in matches]
    
    return None


def _retry_with_repair_prompt(original_prompt: str, chunk: list, failed_response: str) -> list:
    """Retry translation with a repair prompt after JSON parse failure."""
    token_list = set()
    for item in chunk:
        token_list.update(item["token_map"].keys())
    
    repair_prompt = f"""Your previous response was malformed. Output ONLY valid JSON.

REQUIRED FORMAT:
{{"translations":[{{"i":0,"t":"text"}},{{"i":1,"t":"text"}}]}}

CRITICAL: Include these exact tokens in translations: {', '.join(sorted(token_list))}

Previous failed response (DO NOT repeat this error):
{failed_response[:500]}

{original_prompt}"""
    
    response_text, error = _call_gemini_with_backoff(repair_prompt)
    if error:
        return None
    
    return _parse_batch_response(response_text)


def _repair_single_item(item: dict, translated: str, missing_tokens: list, target_lang: str) -> str:
    """Attempt to repair a single translation with missing tokens."""
    repair_prompt = f"""Fix this translation. CRITICAL: Include these exact tokens: {', '.join(missing_tokens)}

Original (masked): {item["masked"]}
Bad translation: {translated}

Output ONLY the fixed translation to {target_lang}, nothing else:"""
    
    response_text, error = _call_gemini_with_backoff(repair_prompt, max_retries=2)
    if error:
        return None
    
    # Check if repair worked
    missing = validate_tokens_preserved(item["masked"], response_text, item["token_map"])
    if missing:
        return None
    
    return response_text

def translate_text_batch_gemini(
    text: str,
    source_lang: str,
    target_lang: str,
    character_tag: str = None,
    retry_count: int = 0
) -> tuple:
    """
    Strict translation function for batch processing.
    Uses JSON-only output to prevent truncation and corruption.
    
    Args:
        text: Text to translate
        source_lang: Source language (e.g., 'english')
        target_lang: Target language (e.g., 'turkish')
        character_tag: Optional character name for context
        retry_count: Internal retry counter
        
    Returns:
        Tuple of (translated_text, error_message)
    """
    global gemini_model, no_ai
    
    if no_ai or gemini_model is None:
        return (None, "Gemini model not initialized")
    
    if not is_internet_available():
        return (None, "No internet connection")
    
    if not text or not text.strip():
        return ("", None)  # Empty input -> empty output
    
    # Mask Ren'Py tokens
    masked_text, token_map = mask_renpy_tokens(text)
    
    # Build strict translation prompt with JSON output
    character_context = f"The speaker is '{character_tag}'." if character_tag else ""
    
    prompt = f"""You are a strict translation engine for Ren'Py visual novel scripts.

TASK: Translate the following text from {source_lang} to {target_lang}.
{character_context}

RULES:
1. Output MUST be valid JSON: {{"translation":"your translation here"}}
2. Preserve ALL placeholders exactly: ⟦T0⟧, ⟦T1⟧, etc.
3. Keep punctuation, spacing, and formatting intact.
4. Do NOT add explanations or quotes around the text.
5. Translate naturally while maintaining original meaning and tone.

TEXT TO TRANSLATE:
{masked_text}

OUTPUT (JSON only):"""

    max_attempts = 2 if retry_count == 0 else 1
    
    for attempt in range(max_attempts):
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = gemini_model.generate_content(prompt, safety_settings=safety_settings)
            
            if not response.parts:
                logger.warning(f"[translate_batch_legacy] Empty response from Gemini (attempt {attempt+1})")
                continue
            
            raw_output = response.text.strip()
            logger.debug(f"[translate_batch_legacy] Raw output: {raw_output[:200]}...")
            
            # Parse JSON output
            translated = None
            
            # Try to extract JSON
            try:
                # Handle potential markdown code blocks
                if raw_output.startswith("```"):
                    # Remove code fence
                    lines = raw_output.split('\n')
                    json_lines = [l for l in lines if not l.startswith("```")]
                    raw_output = '\n'.join(json_lines).strip()
                
                # Try direct JSON parse
                data = json.loads(raw_output)
                translated = data.get("translation", "")
                
            except json.JSONDecodeError:
                # Fallback: Try to extract translation from partial JSON
                match = re.search(r'"translation"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', raw_output)
                if match:
                    translated = match.group(1).replace('\\"', '"')
                else:
                    # Last resort: Use the raw text if it looks reasonable
                    if not raw_output.startswith('{') and len(raw_output) > 0:
                        translated = raw_output
                    else:
                        logger.warning(f"[translate_batch_legacy] Failed to parse JSON: {raw_output[:100]}")
                        continue
            
            if not translated:
                continue
            
            # Validate token preservation
            missing_tokens = validate_tokens_preserved(masked_text, translated, token_map)
            if missing_tokens:
                logger.warning(f"[translate_batch_legacy] Missing tokens: {missing_tokens}")
                if attempt + 1 < max_attempts:
                    # Retry with stricter prompt
                    prompt = prompt.replace(
                        "Preserve ALL placeholders exactly",
                        f"CRITICAL: You MUST include these exact placeholders in your translation: {', '.join(token_map.keys())}"
                    )
                    continue
                # On final attempt, log but continue anyway
            
            # Unmask tokens
            final_translation = unmask_renpy_tokens(translated, token_map)
            
            # Post-processing cleanups
            # Remove leading colon/dash which is a common AI artifact (e.g. "Translation: ..." or "- ...")
            if final_translation:
                # Check for explicit artifact patterns
                if final_translation.startswith(":"):
                    final_translation = final_translation.lstrip(": ").strip()
                elif final_translation.startswith("- ") and not text.startswith("-"):
                    # Only strip dash if original didn't have it
                    final_translation = final_translation.lstrip("- ").strip()
            
            # Validate output quality
            is_valid, error = validate_translation_output(text, final_translation)
            if not is_valid:
                logger.warning(f"[translate_batch] Validation failed: {error}")
                if attempt + 1 < max_attempts:
                    continue
                # Return anyway but log the issue
            
            # Add small delay between API calls
            time.sleep(getattr(config, 'REQUEST_DELAY_SECONDS', 0.3))
            
            return (final_translation, None)
            
        except Exception as e:
            logger.error(f"[translate_batch] Error (attempt {attempt+1}): {e}")
            if attempt + 1 >= max_attempts:
                return (None, str(e))
    
    return (None, "Failed after all retry attempts")


def get_google_languages() -> dict | None:

    if not is_internet_available():
        logger.warning("Cannot get languages: Internet connection not available.")
        return None

    Translator = _lazy_import_translator()
    if Translator is None:
        logger.warning("Cannot get languages: deep_translator not available.")
        return None
    try:

        name_code_dict = Translator().get_supported_languages(as_dict=True)

        code_name_dict = {code: name for name, code in name_code_dict.items()}
        return code_name_dict
    except Exception as e:
        logger.error(f"Error getting supported languages from deep_translator: {e}")
        return None

def load_api_key():

    logger.debug("[load_api_key] Called. Attempting to load settings...") 
    settings = set.load_settings() 

    if not isinstance(settings, dict):
        logger.error(f"[load_api_key] set.load_settings did not return a dictionary (returned {type(settings)}).")
        return None
    key = settings.get("api_key") 
    if key:

        if isinstance(key, str) and key.strip():
            masked_key = f"...{key[-4:]}" if len(key) >=4 else key
            logger.debug(f"[load_api_key] Found valid key ending with {masked_key}.") 
            return key 
        else:
            logger.warning(f"[load_api_key] Found 'api_key' but it's not a valid non-empty string. Returning None.")
            return None 
    else:
        logger.debug(f"[load_api_key] Key 'api_key' not found or is None. Returning None.") 
        return None 

def save_api_key(api_key):

    settings = set.load_settings() 

    if not isinstance(settings, dict):
         settings = {}
         logger.warning("set.load_settings did not return dict in save_api_key. Starting fresh.")

    action_taken = "unchanged" 
    current_api_key = settings.get("api_key")

    if api_key: 
        if current_api_key != api_key:
            settings["api_key"] = api_key 
            action_taken = "saved" 
            logger.debug(f"Preparing to save/update API key in {config.SETTINGS_FILE_PATH}")
        else:

            logger.debug(f"API key unchanged, no action needed.")
            return "unchanged", settings 
    else: 
        if current_api_key is not None:
            settings.pop("api_key", None) 
            action_taken = "removed" 
            logger.debug(f"Preparing to remove API key from {config.SETTINGS_FILE_PATH}")
        else:

            logger.debug(f"API key not in settings, no removal needed.")
            return "unchanged", settings 

    if action_taken in ["saved", "removed"]:
        logger.debug(f"Attempting to save settings...")

        if set.save_settings(settings): 
            if action_taken == "saved":
                logger.info(f"API key saved/updated successfully.")
            elif action_taken == "removed":
                logger.info(f"API key removed successfully.")
            return action_taken, settings 
        else:

            logger.error(f"Error saving settings file during API key update.")

            return "error", settings 
    else:

        return "unchanged", settings 

def prompt_for_api_key(force_prompt=False):

    global _loaded_api_key
    current_key = load_api_key()
    if current_key and not force_prompt:
        return current_key

    logger.info("Google Gemini API key required.")
    if current_key:
        logger.info(f"Current key: ...{current_key[-4:]}")
        try:
            change = input("Change key? (y/n): ").lower()
            if change != 'y':
                return current_key
        except (EOFError, KeyboardInterrupt):
             logger.info("Input cancelled.")
             return current_key 

    else:
        logger.info("Key not found.")

    while True:
        try:
            new_key = input("Введите ваш Google API ключ: ").strip()
            if new_key:
                if save_api_key(new_key):
                    return new_key
                else:

                    logger.warning("Retry.")
                    continue 
            else:
                logger.warning("Key cannot be empty.")
        except EOFError:
            logger.info("Input cancelled.")
            return None 
        except KeyboardInterrupt:
            logger.info("Input interrupted.")
            return None 

def get_available_models(force_refresh=False):

    global _available_models_cache, no_ai, genai
    logger.debug(f"[get_available_models] Called. Force refresh: {force_refresh}")

    if _available_models_cache and not force_refresh:
        logger.debug(f"[get_available_models] Returning cached models: {len(_available_models_cache)} models")
        return _available_models_cache

    genai_module = _lazy_import_genai()
    if no_ai or genai_module is None:
        logger.warning("[get_available_models] Failed: AI module not available.")
        return None

    if not load_api_key():
         logger.warning("[get_available_models] Failed: API key not configured.")
         no_ai = True 
         _available_models_cache = None 
         return None

    if not is_internet_available():
        logger.warning("[get_available_models] Failed: Internet connection not available.")
        no_ai = True 
        _available_models_cache = None 
        return None

    try:
        logger.debug("[get_available_models] Attempting to list models via API...")
        available_models = []

        for m in genai_module.list_models():

            if 'generateContent' in m.supported_generation_methods and 'embed' not in m.name.lower():

                available_models.append(m.name)

        if available_models:

            available_models.sort()
            _available_models_cache = available_models 
            logger.info(f"[get_available_models] Success. Found {len(available_models)} models.")

            return available_models
        else:
            logger.warning("[get_available_models] API returned no suitable models.")
            _available_models_cache = [] 
            return []
    except ImportError:

        logger.error("[get_available_models] google.generativeai not imported.")
        no_ai = True
        _available_models_cache = None
        return None
    except Exception as e:

        error_str = str(e).lower()
        logger.error(f"[get_available_models] Failed to list models from Gemini API: {e}")
        no_ai = True 
        _available_models_cache = None 

        network_error_keywords = ["deadline exceeded", "timeout", "connection refused", "network is unreachable", "dns lookup", "unavailable", "service unavailable", "404", "503"]
        auth_error_keywords = ["api key", "permission denied", "authentication", "invalid", "403", "401"]

        is_network_error = any(keyword in error_str for keyword in network_error_keywords)
        is_auth_error = any(keyword in error_str for keyword in auth_error_keywords)

        if is_network_error:
             logger.warning("[get_available_models] Error seems network-related.")
        elif is_auth_error:
             logger.warning("[get_available_models] Error likely related to API Key.")
        else:
             logger.warning("[get_available_models] An unexpected error occurred.")

        return None

def configure_gemini(model_name_to_use=None):

    global gemini_model, no_ai, genai 

    if gemini_model is None or no_ai:
        logger.debug("[configure_gemini] Checking internet connection...")
        if not is_internet_available():
            logger.warning("[configure_gemini] Failed: Internet connection not available.")
            no_ai = True
            gemini_model = None

            return False

    if genai and gemini_model and not no_ai and gemini_model.model_name.endswith(model_name_to_use):
        logger.debug(f"Skipping configure_gemini: Already configured for {model_name_to_use}")
        return True 

    if model_name_to_use is None:
        model_name_to_use = config.DEFAULT_MODEL_NAME
    logger.debug(f"Target model: {model_name_to_use}") 

    genai_module = _lazy_import_genai()
    if genai_module is None:
        no_ai = True 
        gemini_model = None 
        logger.error("configure_gemini failed: google.generativeai module not imported.")
        return False 

    api_key = load_api_key()

    is_gui = 'PyQt6.QtWidgets' in sys.modules and sys.modules['PyQt6.QtWidgets'].QApplication.instance() is not None

    if api_key:

        masked_key = f"...{api_key[-4:]}" if len(api_key) >= 4 else api_key
        logger.debug(f"API Key loaded successfully (ends with: {masked_key})") 
    else:
        logger.warning("API Key not found in settings.") 
        if not is_gui:
            logger.info("GUI not detected, prompting for API key in console...") 
            api_key = prompt_for_api_key(force_prompt=True)
        else:

            no_ai = True
            gemini_model = None
            logger.warning("configure_gemini failed: API Key missing (GUI detected).")
            return False 

    if not api_key and not is_gui:
        logger.info("API key not found in settings. Prompting...")
        api_key = prompt_for_api_key(force_prompt=True) 

    if not api_key:
        no_ai = True
        gemini_model = None
        logger.warning("configure_gemini failed: API Key still missing after prompt.")
        return False 

    try:

        logger.debug("[configure_gemini] Checking internet connection before creating model object...")
        if not is_internet_available():
             logger.warning("[configure_gemini] Failed: Internet connection lost before creating model.")
             no_ai = True
             gemini_model = None

             is_gui = 'PyQt6.QtWidgets' in sys.modules and sys.modules['PyQt6.QtWidgets'].QApplication.instance() is not None
             if is_gui:
                try:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(None, "Сетевая ошибка Gemini", "Не удалось создать объект модели Gemini.\nПроверьте ваше интернет-соединение.")
                except Exception as msg_err:
                    logger.error(f"Could not show GUI error message box: {msg_err}")
             return False
        masked_key_for_config = f"...{api_key[-4:]}" if len(api_key) >= 4 else api_key
        logger.debug(f"Configuring genai with key ending in {masked_key_for_config}") 
        genai_module.configure(api_key=api_key)
        logger.debug("genai.configure called successfully.") 

        logger.debug(f"Attempting to create/verify model: {model_name_to_use}") 

        gemini_model = genai_module.GenerativeModel(
             model_name_to_use
        )

        logger.debug(f"[configure_gemini] Model object created. gemini_model is None={gemini_model is None}") 

        logger.info(f"Model '{model_name_to_use}' object created successfully.") 
        no_ai = False 
        return True 
    except ImportError:

        logger.error("[configure_gemini] google.generativeai not imported.")
        no_ai = True
        gemini_model = None
        return False
    except Exception as e:

        no_ai = True 
        gemini_model = None 
        logger.error(f"Error during Gemini configuration or model creation: {e}")

        error_str = str(e).lower()
        gui_message_title = "Ошибка Gemini"
        gui_message_text = f"Не удалось настроить Gemini API или создать модель '{model_name_to_use}'.\n\nОшибка: {e}"

        network_error_keywords = ["deadline exceeded", "timeout", "connection refused", "network is unreachable", "dns lookup", "unavailable", "service unavailable", "404", "503"]
        auth_error_keywords = ["api key", "permission denied", "authentication", "invalid", "403", "401"]

        is_network_error = any(keyword in error_str for keyword in network_error_keywords)
        is_auth_error = any(keyword in error_str for keyword in auth_error_keywords)

        if is_network_error:
            logger.warning("Error seems network-related during configuration.")
            gui_message_title = "Сетевая ошибка Gemini"
            gui_message_text = f"Не удалось связаться с Gemini API.\nПроверьте ваше интернет-соединение.\n\nОшибка: {e}"
        elif is_auth_error:

            logger.warning("Error likely related to API Key validity or permissions.")
            gui_message_title = "Ошибка API ключа Gemini"
            gui_message_text = (f"Не удалось настроить Gemini API.\n"
                                f"Проверьте правильность и действительность вашего API ключа и доступ к модели '{model_name_to_use}'.\n\n"
                                f"Ошибка: {e}")
        elif ("not found" in error_str) and model_name_to_use in str(e):

             logger.warning(f"Error: Model '{model_name_to_use}' not found or unavailable.")
             gui_message_title = "Модель Gemini не найдена"
             gui_message_text = f"Указанная модель '{model_name_to_use}' не найдена или недоступна для вашего ключа.\nПроверьте имя модели или выберите другую.\n\nОшибка: {e}"
        else:
             logger.warning("An unexpected error occurred during configuration.")

        is_gui = 'PyQt6.QtWidgets' in sys.modules and sys.modules['PyQt6.QtWidgets'].QApplication.instance() is not None
        if is_gui:
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(None, gui_message_title, gui_message_text)
            except Exception as msg_err:
                logger.error(f"Could not show GUI error message box: {msg_err}")

        return False 

def refine_text_with_gemini(original_text, current_text, user_instruction, context_info,
                            source_lang, target_lang, mode, character_tag=None):

    global gemini_model, no_ai
    if no_ai or gemini_model is None:
        return (None, "Модель Gemini не инициализирована или недоступна.")

    if not is_internet_available():
        logger.warning("[refine_text_with_gemini] Failed: Internet connection not available.")

        return (None, "Отсутствует подключение к интернету для запроса к Gemini.")

    context_prompt = "Context (surrounding lines):\n"
    marker = ""
    line_num_str = ""
    tag_prefix = ""
    display_content = ""
    text_to_show = ""

    for info in context_info:
        marker = ">> " if info["is_target"] else "   " 
        line_num_str = f"L{info['line_index']+1}:"
        tag_prefix = f"[{info['character_tag']}] " if info.get('character_tag') else ""

        if mode == "translate":
            if info.get("is_translation_line"): 
                context_prompt += f"{marker}{line_num_str} Original ({source_lang}): {tag_prefix}{info['original']}\n"
                context_prompt += f"{marker}{line_num_str} Current Translation ({target_lang}): {tag_prefix}{info['translated']}\n\n"
            elif info.get("is_original_comment"): 

                 context_prompt += f"{marker}{line_num_str} Original Line ({source_lang}): {tag_prefix}{info['original']}\n\n"

            else: 
                display_content = (info['content'][:75] + '...') if len(info['content']) > 75 else info['content']
                context_prompt += f"{marker}{line_num_str} Raw Line: {tag_prefix}{display_content}\n\n"
        else: 
            text_to_show = info.get('current_text') 
            if text_to_show is not None and info.get("is_editable"): 
                 context_prompt += f"{marker}{line_num_str} Editable Text ({target_lang}): {tag_prefix}{text_to_show}\n\n"

            else: 
                display_content = (info['content'][:75] + '...') if len(info['content']) > 75 else info['content']
                context_prompt += f"{marker}{line_num_str} Raw Line: {display_content}\n\n"

    character_info = f"The character speaking is '{character_tag}'." if character_tag else "This is narration or menu text."

    if mode == "translate":
        prompt = (
            f"You are an expert editor revising translations for a Ren'Py visual novel script.\n"
            f"Your task is to refine the 'Current Translation' based on the 'Original Text' and the 'User Instruction', considering the provided 'Context'.\n"
            f"{character_info}\n"
            f"Source Language: {source_lang}\n"
            f"Target Language: {target_lang}\n\n"
            f"Original Text:\n\"\"\"\n{original_text}\n\"\"\"\n\n"
            f"Current Translation:\n\"\"\"\n{current_text}\n\"\"\"\n\n"
            f"User Instruction:\n\"\"\"\n{user_instruction}\n\"\"\"\n\n"
            f"{context_prompt}"
            f"Constraints:\n"
            f"- Preserve the original meaning and intent.\n"
            f"- Maintain the character's voice and tone (if applicable).\n"
            f"- Ensure grammatical correctness and natural phrasing in the *{target_lang}* language.\n"
            f"- Keep Ren'Py tags (like {{w}}, {{p}}) and text variables (like [variable_name]) unchanged.\n"
            f"- ONLY output the refined translation text, without any explanations or quotation marks around it.\n\n"
            f"Refined Translation ({target_lang}):\n"
        )
    else: 
        prompt = (
            f"You are an expert editor revising a script for a Ren'Py visual novel.\n"
            f"Your task is to refine the 'Current Text' based on the 'User Instruction', considering the provided 'Context'.\n"
            f"{character_info}\n"
            f"Language: {target_lang}\n\n"
            f"Current Text:\n\"\"\"\n{current_text}\n\"\"\"\n\n"
            f"User Instruction:\n\"\"\"\n{user_instruction}\n\"\"\"\n\n"
            f"{context_prompt}"
            f"Constraints:\n"
            f"- Preserve the original meaning and intent.\n"
            f"- Maintain the character's voice and tone (if applicable).\n"
            f"- Ensure grammatical correctness and natural phrasing in the *{target_lang}* language.\n"
            f"- Keep Ren'Py tags (like {{w}}, {{p}}) and text variables (like [variable_name]) unchanged.\n"
            f"- ONLY output the refined text, without any explanations or quotation marks around it.\n\n"
            f"Refined Text ({target_lang}):\n"
        )

    retries = 3
    for attempt in range(retries):
        try:
            logger.debug(f"Before generate_content call (Attempt {attempt+1}): gemini_model type = {type(gemini_model)}")
            if not hasattr(gemini_model, 'generate_content') or not callable(gemini_model.generate_content):
                 error_msg = f"Ошибка: gemini_model (type: {type(gemini_model)}) не имеет вызываемого метода 'generate_content'."
                 logger.error(error_msg)
                 no_ai = True 
                 return (None, error_msg)
            logger.debug(f"Attempt {attempt + 1}/{retries}: Sending refinement request to Gemini...")

            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            try:
                 response = gemini_model.generate_content(prompt, safety_settings=safety_settings)
                 logger.debug(f"API call returned. Response type: {type(response)}")
            except TypeError as te:

                 logger.critical(f"CRITICAL TYPE ERROR during API call: {te}")
                 logger.debug(f"gemini_model type at time of error: {type(gemini_model)}")
                 no_ai = True 
                 return (None, f"TypeError при вызове Gemini API: {te}. Проверьте состояние модели.")
            except Exception as api_call_e:

                 logger.error(f"ERROR during actual API call: {type(api_call_e).__name__}: {api_call_e}")

                 raise api_call_e

            time.sleep(config.REQUEST_DELAY_SECONDS)

            if response.parts:
                refined_text = response.text.strip()

                if refined_text.startswith(''):
                    refined_text = refined_text[3:-3].strip()
                elif refined_text.startswith('"') and refined_text.endswith('"'):
                    refined_text = refined_text[1:-1].strip()

                logger.debug(f"Gemini suggested: \"{refined_text}\"")

                text_before_refinement = current_text
                original_vars = re.findall(r'(\[.*?\])', text_before_refinement) 
                refined_vars = re.findall(r'(\[.*?\])', refined_text)

                if original_vars != refined_vars:
                     logger.warning(f"Variable set [...] might have changed! Original: {original_vars}, Refined: {refined_vars}")

                return (refined_text, None) 
            else:

                error_msg = "Received empty or blocked response from Gemini."
                block_reason = None
                finish_reason = None
                try:

                     if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                          block_reason = response.prompt_feedback.block_reason

                     if hasattr(response, 'candidates') and response.candidates:
                         finish_reason = response.candidates[0].finish_reason

                     if block_reason:
                         error_msg += f" Block Reason: {block_reason}."
                     elif finish_reason and finish_reason != 1: 
                          error_msg += f" Finish Reason: {finish_reason}." 
                     else:
                          error_msg += " Reason unknown."

                except Exception as feedback_error:
                    logger.warning(f"Error retrieving feedback from Gemini response: {feedback_error}")
                    error_msg += " Could not retrieve specific reason."

                logger.warning(error_msg)

                if attempt + 1 == retries:
                    return (None, error_msg)

                delay = config.REQUEST_DELAY_SECONDS * (attempt + 2)
                logger.debug(f"Retrying after {delay} seconds...")
                time.sleep(delay)
                continue 

        except Exception as e:

            error_msg = f"Error calling Gemini API (Attempt {attempt + 1}/{retries}): {e}"
            logger.error(error_msg)
            error_str = str(e).lower()

            auth_error_keywords = ["api key", "permission denied", "authentication", "invalid", "403", "401"]
            rate_limit_keywords = ["rate limit", "429"]
            network_error_keywords = ["deadline exceeded", "timeout", "connection refused", "network is unreachable", "dns lookup", "unavailable", "service unavailable", "503"] 

            is_auth_error = any(keyword in error_str for keyword in auth_error_keywords)
            is_rate_limit = any(keyword in error_str for keyword in rate_limit_keywords)
            is_network_error = any(keyword in error_str for keyword in network_error_keywords) 

            if is_auth_error:
                 final_error = f"Authentication/Permission error with Gemini API: {e}. Check your API key."
                 logger.error(final_error)
                 no_ai = True 
                 return (None, final_error)

            if is_network_error:
                 final_error = f"Network error contacting Gemini API (during request): {e}."
                 logger.error(final_error)

                 return (None, final_error)

            if is_rate_limit:

                pass 

            elif attempt + 1 == retries:
                final_error = f"Failed to refine text after {retries} attempts. Last error: {e}"
                logger.error(final_error)

                return (None, final_error)
            else:

                time.sleep(config.REQUEST_DELAY_SECONDS * 2)

    return (None, f"Failed to get response from Gemini after {retries} attempts.")

def refine_text_with_gemini_translate(original_text, current_translation, user_instruction, context_info, source_lang, target_lang, character_tag=None):

    return refine_text_with_gemini(original_text, current_translation, user_instruction, context_info,
                                   source_lang, target_lang, "translate", character_tag)

def refine_text_with_gemini_direct(current_text, user_instruction, context_info, target_lang, character_tag=None):

    return refine_text_with_gemini(current_text, current_text, user_instruction, context_info,
                                   None, target_lang, "direct", character_tag) 