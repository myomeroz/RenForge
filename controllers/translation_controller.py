# -*- coding: utf-8 -*-
"""
RenForge Translation Controller

Handles all translation-related business logic:
- Single item translation (Google/AI)
- Batch translation operations
- Translation settings management
"""

from typing import List, Optional, Dict, Any, Callable
from dataclasses import replace

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QRunnable, pyqtSlot, QThreadPool
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from renforge_logger import get_logger
from locales import tr
from models.parsed_file import ParsedFile, ParsedItem
from models.settings_model import SettingsModel
import renforge_ai as ai

logger = get_logger("controllers.translation")



# =============================================================================
# WORKER CLASSES
# =============================================================================

class BatchAIWorkerSignals(QObject):
    """Signals for the BatchAIWorker."""
    progress = pyqtSignal(int, int)
    # Update signal signature to match RenForgeGUI/BatchController slot for direct connection
    # (int, str, dict) -> index, text, item_data
    item_updated = pyqtSignal(int, str, dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

class BatchAIWorker(QRunnable):
    """Background worker for batch AI translation."""
    
    def __init__(self, parsed_file: ParsedFile, indices: List[int], model: str, source_lang: str, target_lang: str, controller: 'TranslationController'):
        super().__init__()
        self.parsed_file = parsed_file
        self.indices = indices
        self.model = model
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.controller = controller
        self.signals = BatchAIWorkerSignals()
        self._is_canceled = False
        
    def cancel(self):
        self._is_canceled = True
        
    @pyqtSlot()
    def run(self):
        import time
        import renforge_config as config
        import renforge_ai as ai_module
        
        results = {'success_count': 0, 'error_count': 0, 'errors': [], 'canceled': False, 'processed': 0}
        total = len(self.indices)
        results['total'] = total
        
        # Batch size for worker-level chunking (keeps UI responsive vs sending all at once)
        WORKER_BATCH_SIZE = 50
        
        # Process in chunks
        for i in range(0, total, WORKER_BATCH_SIZE):
            if self._is_canceled:
                results['canceled'] = True
                break
                
            # Get chunk indices
            chunk_indices = self.indices[i : i + WORKER_BATCH_SIZE]
            
            # Prepare batch payload
            batch_items = []
            valid_indices = []
            
            for idx in chunk_indices:
                item = self.parsed_file.get_item(idx)
                if not item:
                    continue
                
                text = item.original_text or item.current_text
                if not text or not text.strip():
                    continue
                
                batch_items.append(text)
                valid_indices.append(idx)
            
            if not batch_items:
                # Just advance progress if no valid items in this chunk
                self.signals.progress.emit(min(i + WORKER_BATCH_SIZE, total), total)
                continue
                
            try:
                # Call AI with batch
                batch_result = ai_module.translate_text_batch_gemini_strict(
                    items=batch_items,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    glossary=getattr(config, 'TRANSLATION_GLOSSARY', None)
                )
                
                # Process errors map
                item_errors = {}
                if batch_result.get("errors"):
                    for err in batch_result["errors"]:
                        item_errors[err.get("i")] = err.get("error")
                
                # Process translations
                if batch_result.get("translations"):
                    for t_item in batch_result["translations"]:
                        if self._is_canceled:
                            break
                            
                        # Map internal batch index (0..N) back to real file index
                        internal_idx = t_item.get("i")
                        if internal_idx is not None and internal_idx < len(valid_indices):
                            real_idx = valid_indices[internal_idx]
                            translated = t_item.get("t")
                            
                            if translated:
                                # Update file model
                                self.parsed_file.update_item_text(real_idx, translated)
                                
                                # Check for fallback
                                error_reason = None
                                if t_item.get("fallback"):
                                    error_reason = t_item.get("error_reason")
                                    # Could emit a special status here if UI supported it
                                
                                # Emit update
                                self.signals.item_updated.emit(real_idx, translated, {'file_path': self.parsed_file.file_path})
                                results['success_count'] += 1
                                
                                if error_reason:
                                    results['error_count'] += 1
                                    results['errors'].append(f"Line {self.parsed_file.get_item(real_idx).line_index}: Fallback - {error_reason}")
                            else:
                                # Empty translation?
                                results['error_count'] += 1
                                results['errors'].append(f"Line {self.parsed_file.get_item(real_idx).line_index}: Empty result")
                
                # Report chunk errors for items completely missing from translations (e.g. API error)
                for internal_idx, error_msg in item_errors.items():
                    if internal_idx < len(valid_indices):
                        real_idx = valid_indices[internal_idx]
                        if not any(t.get("i") == internal_idx for t in batch_result.get("translations", [])):
                             results['error_count'] += 1
                             results['errors'].append(f"Line {self.parsed_file.get_item(real_idx).line_index}: {error_msg}")

                if self._is_canceled:
                    results['canceled'] = True
                    break
                    
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"BatchAIWorker Error details:\n{error_trace}")
                
                # Whole batch failed?
                results['error_count'] += len(batch_items)
                results['errors'].append(f"Batch Error (lines {valid_indices[0]}...): {str(e)}")
            
            # Emit progress
            processed_so_far = min(i + WORKER_BATCH_SIZE, total)
            self.signals.progress.emit(processed_so_far, total)
            
            # Throttle between chunks
            if not self._is_canceled:
                time.sleep(getattr(config, 'BATCH_AI_DELAY', 0.5))
        
        results['processed'] = results['success_count'] + results['error_count']
        self.signals.finished.emit(results)

class BatchGoogleWorker(QRunnable):
    """Background worker for batch Google translation."""
    
    def __init__(self, parsed_file: ParsedFile, indices: List[int], source_lang: str, target_lang: str, controller: 'TranslationController'):
        super().__init__()
        self.parsed_file = parsed_file
        self.indices = indices
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.controller = controller
        self.signals = BatchAIWorkerSignals() # Reuse same signals class as it has progress, item_updated etc.
        self._is_canceled = False
        
    def cancel(self):
        self._is_canceled = True
        
    @pyqtSlot()
    def run(self):
        import time
        import renforge_config as config
        
        results = {'success_count': 0, 'error_count': 0, 'errors': [], 'canceled': False, 'processed': 0}
        total = len(self.indices)
        results['total'] = total
        
        # Init translator
        try:
            Translator = ai._lazy_import_translator()
            if not Translator:
                self.signals.error.emit(tr("error_library_not_found_msg"))
                results['errors'].append("GoogleTranslator library not found")
                self.signals.finished.emit(results)
                return
                
            translator = Translator(source=self.source_lang, target=self.target_lang)
        except Exception as e:
            self.signals.error.emit(f"Init failed: {e}")
            results['errors'].append(str(e))
            self.signals.finished.emit(results)
            return
        
        for i, idx in enumerate(self.indices):
            if self._is_canceled:
                results['canceled'] = True
                break
            
            item = self.parsed_file.get_item(idx)
            if not item:
                continue
            
            text = item.original_text or item.current_text
            if not text or not text.strip():
                self.signals.progress.emit(i + 1, total)
                continue
            
            try:
                translated = translator.translate(text)
                
                if self._is_canceled:
                    results['canceled'] = True
                    break
                
                if translated:
                    self.parsed_file.update_item_text(idx, translated)
                    # Emit with file_path for robust context resolution
                    self.signals.item_updated.emit(idx, translated, {'file_path': self.parsed_file.file_path})
                    results['success_count'] += 1
                else:
                    results['error_count'] += 1
                    results['errors'].append(f"Line {item.line_index}: Empty result")
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append(f"Line {item.line_index}: {str(e)}")
            
            self.signals.progress.emit(i + 1, total)
            
            if not self._is_canceled:
                time.sleep(getattr(config, 'BATCH_TRANSLATE_DELAY', 0.1))
        
        results['processed'] = results['success_count'] + results['error_count']
        self.signals.finished.emit(results)


class TranslationController(QObject):
    """
    Controller for translation operations.
    
    Responsibilities:
    - Coordinate translation requests between View and AI/Core modules
    - Manage batch translation workers
    - Handle translation settings
    
    Signals:
        translation_started: Emitted when translation begins
        translation_progress(int, int): Emitted with (current, total) during batch
        translation_completed(int): Emitted with count of translated items
        translation_error(str): Emitted with error message
        item_translated(int, str): Emitted with (index, translated_text) for each item
    """
    
    # Signals
    translation_started = pyqtSignal()
    translation_progress = pyqtSignal(int, int)  # current, total
    translation_completed = pyqtSignal(int)  # count
    translation_error = pyqtSignal(str)
    item_translated = pyqtSignal(int, str)  # index, new_text
    
    def __init__(self, settings: Optional[SettingsModel] = None):
        """
        Initialize the translation controller.
        
        Args:
            settings: Settings model instance (uses singleton if not provided)
        """
        super().__init__()
        self._settings = settings or SettingsModel.instance()
        self._current_worker: Optional[QThread] = None
        self._is_translating = False
        
        logger.debug("TranslationController initialized")

    def check_google_availability(self) -> tuple[bool, Optional[str]]:
        """
        Check if Google Translate is available (internet + library).
        
        Returns:
            (is_available, error_message_key)
        """
        if not ai.is_internet_available():
            return False, "google_trans_unavailable_net"
            
        Translator = ai._lazy_import_translator()
        if Translator is None:
            return False, "google_trans_unavailable_lib"
            
        return True, None

    def check_ai_availability(self) -> tuple[bool, Optional[str]]:
        """
        Check if AI is available (settings + model check).
        
        Returns:
            (is_available, error_message_key)
        """
        # Note: ensuring Gemini initialized usually requires UI interaction if fail,
        # but here we just check state.
        if not ai.is_internet_available():
            return False, "batch_ai_unavailable_net"

        if ai.no_ai:
            return False, "edit_ai_gemini_unavailable"
            
        if ai.gemini_model is None:
            return False, "edit_ai_gemini_unavailable"
            
        return True, None

    
    # =========================================================================
    # PROPERTIES
    # =========================================================================
    
    @property
    def is_translating(self) -> bool:
        """Check if a translation is in progress."""
        return self._is_translating
    
    @property
    def source_language(self) -> str:
        """Get default source language."""
        return self._settings.default_source_language
    
    @property
    def target_language(self) -> str:
        """Get default target language."""
        return self._settings.default_target_language
    
    @property
    def selected_model(self) -> Optional[str]:
        """Get selected AI model."""
        return self._settings.default_model
    
    # =========================================================================
    # SINGLE ITEM TRANSLATION
    # =========================================================================
    
    def translate_single_google(
        self, 
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> Optional[str]:
        """
        Translate a single text with Google Translate.
        
        Args:
            text: Text to translate
            source_lang: Source language code (uses default if not provided)
            target_lang: Target language code (uses default if not provided)
            
        Returns:
            Translated text, or None on failure
        """
        source = source_lang or self.source_language
        target = target_lang or self.target_language
        
        try:
            Translator = ai._lazy_import_translator()
            if Translator is None:
                self.translation_error.emit(tr("error_library_not_found_msg"))
                return None
            
            translator = Translator(source=source, target=target)
            translated = translator.translate(text)
            logger.debug(f"Google translated: '{text[:30]}...' -> '{translated[:30] if translated else 'None'}...'")
            return translated
        except Exception as e:
            logger.error(f"Google translation failed: {e}")
            self.translation_error.emit(str(e))
            return None
    
    def translate_single_ai(
        self,
        text: str,
        model: Optional[str] = None,
        context: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> Optional[str]:
        """
        Translate/edit a single text with AI.
        
        Args:
            text: Text to translate/edit
            model: AI model name (uses default if not provided)
            context: Additional context for AI
            source_lang: Source language (uses default if not provided)
            target_lang: Target language (uses default if not provided)
            
        Returns:
            AI response text, or None on failure
        """
        model_name = model or self.selected_model
        source = source_lang or self.source_language
        target = target_lang or self.target_language
        
        if not model_name:
            self.translation_error.emit(tr("error_no_model"))
            return None
        
        if ai.no_ai or ai.gemini_model is None:
            self.translation_error.emit(tr("edit_ai_gemini_unavailable"))
            return None
        
        try:
            user_instruction = context or "Translate this text accurately while preserving formatting tags"
            result, error_msg = ai.refine_text_with_gemini_translate(
                original_text=text,
                current_translation="",
                user_instruction=user_instruction,
                context_info=[],
                source_lang=source,
                target_lang=target,
                character_tag=None
            )
            
            if error_msg:
                logger.warning(f"AI translation returned error: {error_msg}")
                self.translation_error.emit(error_msg)
                return None
            
            logger.debug(f"AI translated with Gemini")
            return result
        except Exception as e:
            logger.error(f"AI translation failed: {e}")
            self.translation_error.emit(str(e))
            return None
    
    # =========================================================================
    # BATCH TRANSLATION
    # =========================================================================
    
    def translate_batch_google(
        self,
        parsed_file: ParsedFile,
        indices: List[int],
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Translate multiple items with Google Translate.
        
        Args:
            parsed_file: The ParsedFile containing items
            indices: List of item indices to translate
            source_lang: Source language code
            target_lang: Target language code
            progress_callback: Optional callback for progress (current, total)
            
        Returns:
            Dict with 'success_count', 'error_count', 'errors' keys
        """
        source = source_lang or self.source_language
        target = target_lang or self.target_language
        
        # Initialize Google Translator
        Translator = ai._lazy_import_translator()
        if Translator is None:
            self.translation_error.emit(tr("error_library_not_found_msg"))
            return {'success_count': 0, 'error_count': 1, 'errors': ['GoogleTranslator not available']}
        
        try:
            self._translator = Translator(source=source, target=target)
        except Exception as e:
            self.translation_error.emit(str(e))
            return {'success_count': 0, 'error_count': 1, 'errors': [str(e)]}
        
        self._is_translating = True
        self.translation_started.emit()
        
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        total = len(indices)
        
        for i, idx in enumerate(indices):
            if not self._is_translating:  # Check for cancellation
                break
            
            item = parsed_file.get_item(idx)
            if not item:
                continue
            
            text = item.original_text or item.current_text
            if not text or not text.strip():
                continue
            
            try:
                translated = self._translator.translate(text)
                
                if translated:
                    parsed_file.update_item_text(idx, translated)
                    self.item_translated.emit(idx, translated)
                    results['success_count'] += 1
                else:
                    results['error_count'] += 1
                    results['errors'].append(f"Line {item.line_index}: Empty result")
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append(f"Line {item.line_index}: {str(e)}")
            
            # Progress update
            self.translation_progress.emit(i + 1, total)
            if progress_callback:
                progress_callback(i + 1, total)
        
        self._is_translating = False
        self.translation_completed.emit(results['success_count'])
        
        return results
    
    def translate_batch_ai(
        self,
        parsed_file: ParsedFile,
        indices: List[int],
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Translate multiple items with AI.
        
        Args:
            parsed_file: The ParsedFile containing items
            indices: List of item indices to translate
            model: AI model name
            progress_callback: Optional callback for progress
            
        Returns:
            Dict with 'success_count', 'error_count', 'errors' keys
        """
        model_name = model or self.selected_model
        
        if not model_name:
            self.translation_error.emit(tr("error_no_model"))
            return {'success_count': 0, 'error_count': 1, 'errors': ['No model selected']}
        
        self._is_translating = True
        self.translation_started.emit()
        
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        total = len(indices)
        
        for i, idx in enumerate(indices):
            if not self._is_translating:
                break
            
            item = parsed_file.get_item(idx)
            if not item:
                continue
            
            text = item.original_text or item.current_text
            if not text or not text.strip():
                continue
            
            try:
                source = self.source_language
                target = self.target_language
                
                translated, error_msg = ai.refine_text_with_gemini_translate(
                    original_text=text,
                    current_translation="",
                    user_instruction="Translate this text accurately while preserving formatting tags",
                    context_info=[],
                    source_lang=source,
                    target_lang=target,
                    character_tag=getattr(item, 'character_tag', None)
                )
                
                if translated and not error_msg:
                    parsed_file.update_item_text(idx, translated)
                    self.item_translated.emit(idx, translated)
                    results['success_count'] += 1
                else:
                    results['error_count'] += 1
                    err_detail = error_msg if error_msg else "Empty AI response"
                    results['errors'].append(f"Line {item.line_index}: {err_detail}")
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append(f"Line {item.line_index}: {str(e)}")
            
            self.translation_progress.emit(i + 1, total)
            if progress_callback:
                progress_callback(i + 1, total)
        
        self._is_translating = False
        self.translation_completed.emit(results['success_count'])
        
        return results

    def start_batch_ai_translation(
        self,
        parsed_file: ParsedFile,
        indices: List[int],
        model: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ) -> tuple:
        """
        Start an asynchronous batch AI translation.
        
        Args:
            parsed_file: The file to translate
            indices: List of item indices
            model: Optional model name override
            source_lang: Optional source language override
            target_lang: Optional target language override
            
        Returns:
            Tuple of (worker, signals)
        """
        model_name = model or self.selected_model
        source = source_lang or self.source_language
        target = target_lang or self.target_language
        
        # Create worker
        worker = BatchAIWorker(parsed_file, indices, model_name, source, target, self)
        
        # Start in thread pool
        QThreadPool.globalInstance().start(worker)
        
        return worker, worker.signals

    def start_batch_google_translation(
        self,
        parsed_file: ParsedFile,
        indices: List[int],
        source_lang: str,
        target_lang: str
    ) -> tuple:
        """
        Start an asynchronous batch Google translation.
        
        Args:
            parsed_file: The file to translate
            indices: List of item indices
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Tuple of (worker, signals)
        """
        worker = BatchGoogleWorker(parsed_file, indices, source_lang, target_lang, self)
        QThreadPool.globalInstance().start(worker)
        return worker, worker.signals
    
    def cancel_translation(self):
        """Cancel ongoing translation."""
        if self._is_translating:
            self._is_translating = False
            logger.info("Translation cancelled by user")
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def get_translation_stats(self, parsed_file: ParsedFile) -> Dict[str, int]:
        """
        Get translation statistics for a file.
        
        Args:
            parsed_file: The ParsedFile to analyze
            
        Returns:
            Dict with 'total', 'translated', 'untranslated', 'modified' counts
        """
        stats = {
            'total': parsed_file.item_count,
            'translated': 0,
            'untranslated': 0,
            'modified': 0
        }
        
        for item in parsed_file.items:
            if item.is_modified_session:
                stats['modified'] += 1
            
            if item.current_text and item.current_text.strip():
                if item.current_text != item.original_text:
                    stats['translated'] += 1
                else:
                    stats['untranslated'] += 1
            else:
                stats['untranslated'] += 1
        
        return stats
    
    def __repr__(self) -> str:
        return f"TranslationController(translating={self._is_translating})"
