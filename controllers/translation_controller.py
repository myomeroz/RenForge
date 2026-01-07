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

from PyQt6.QtCore import QObject, pyqtSignal, QThread, QProcess
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from renforge_logger import get_logger
from locales import tr
from models.parsed_file import ParsedFile, ParsedItem
from models.settings_model import SettingsModel
import renforge_core as core
import renforge_ai as ai

logger = get_logger("controllers.translation")


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
            translated = core.translate_text(text, source, target)
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
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Translate/edit a single text with AI.
        
        Args:
            text: Text to translate/edit
            model: AI model name (uses default if not provided)
            context: Additional context for AI
            
        Returns:
            AI response text, or None on failure
        """
        model_name = model or self.selected_model
        
        if not model_name:
            self.translation_error.emit(tr("error_no_model"))
            return None
        
        try:
            result = ai.translate_with_ai(text, model_name, context)
            logger.debug(f"AI translated with {model_name}")
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
            
            text = item.current_text
            if not text or not text.strip():
                continue
            
            try:
                translated = core.translate_text(text, source, target)
                
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
            
            text = item.current_text
            if not text or not text.strip():
                continue
            
            try:
                translated = ai.translate_with_ai(text, model_name)
                
                if translated:
                    parsed_file.update_item_text(idx, translated)
                    self.item_translated.emit(idx, translated)
                    results['success_count'] += 1
                else:
                    results['error_count'] += 1
                    results['errors'].append(f"Line {item.line_index}: Empty AI response")
                    
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append(f"Line {item.line_index}: {str(e)}")
            
            self.translation_progress.emit(i + 1, total)
            if progress_callback:
                progress_callback(i + 1, total)
        
        self._is_translating = False
        self.translation_completed.emit(results['success_count'])
        
        return results
    
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
