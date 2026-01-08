# -*- coding: utf-8 -*-
"""
Translate Mode Parser

Parser for Ren'Py translation files (translate blocks with old/new pairs or comment/dialogue pairs).
"""

from typing import List, Tuple, Optional

from renforge_logger import get_logger
from renforge_enums import ContextType, ItemType
from models.parsed_file import ParsedItem
from parser.base import BaseParser
from parser.patterns import RenpyPatterns

logger = get_logger("parser.translate")


class TranslateParser(BaseParser):
    """
    Parser for translation mode files.
    
    Handles two formats:
    1. Traditional old/new pairs:
        translate turkish label_id:
            old "Hello"
            new "Merhaba"
    
    2. Comment/dialogue pairs (Ren'Py generated):
        translate turkish label_id:
        #   character "Hello"
            character "Merhaba"
    """
    
    def __init__(self):
        super().__init__()
        self._detected_language: Optional[str] = None
        self._pending_old_text: Optional[str] = None
        self._pending_old_line: Optional[int] = None
        self._pending_original_from_comment: Optional[str] = None
        self._pending_comment_line: Optional[int] = None
    
    def can_parse(self, lines: List[str]) -> bool:
        """Check if file contains translate blocks."""
        for line in lines[:100]:  # Check first 100 lines
            if RenpyPatterns.is_translate_block_start(line):
                return True
        return False
    
    def parse(self, lines: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
        """
        Parse translation file into items.
        
        Returns:
            Tuple of (items list, detected language code)
        """
        self.reset()
        
        for i, line in enumerate(lines):
            self._process_line(i, line)
        
        logger.debug(f"Parsed {len(self._items)} items, language: {self._detected_language}")
        return self._items, self._detected_language
    
    def _process_line(self, line_index: int, line: str):
        """Process a single line."""
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            return
        
        # Check for translate block start
        match = RenpyPatterns.TRANSLATE_START.match(stripped)
        if match:
            lang_code = match.group(1)
            if not self._detected_language:
                self._detected_language = lang_code
            self._current_context = ContextType.TRANSLATE
            return
        
        # =================================
        # FORMAT 1: old/new pairs
        # =================================
        
        # Handle old line
        match = RenpyPatterns.TRANSLATE_OLD.match(line)
        if match:
            self._pending_old_text = match.group(2)
            self._pending_old_line = line_index
            return
        
        # Handle new line - pair with pending old
        match = RenpyPatterns.TRANSLATE_NEW.match(line)
        if match:
            new_text = match.group(2)
            indent = match.group(1)
            suffix = match.group(3)
            
            original = self._pending_old_text or ""
            
            item = self._create_item(
                line_index=line_index,
                original_text=original,
                current_text=new_text,
                item_type=ItemType.DIALOGUE,
                context=self._current_context,
                parsed_data={
                    'indent': indent,
                    'prefix': 'new ',
                    'suffix': suffix,
                    'old_line_index': self._pending_old_line,
                    'reconstruction_rule': 'translate_new',
                }
            )
            self._items.append(item)
            
            # Clear pending
            self._pending_old_text = None
            self._pending_old_line = None
            return
        
        # =================================
        # FORMAT 2: Comment/dialogue pairs
        # (Ren'Py generated translation files)
        # =================================
        
        # Handle comment line with dialogue (original text)
        # Format: #   character_id "text" or # "text"
        if stripped.startswith('#'):
            comment_content = stripped[1:].lstrip()
            
            # Try to extract text from comment
            original_text = self._extract_text_from_comment(comment_content)
            if original_text is not None:
                self._pending_original_from_comment = original_text
                self._pending_comment_line = line_index
            return
        
        # Handle dialogue line after comment (translated text)
        # Format:     character_id "text" or "text"
        if self._pending_original_from_comment is not None:
            # Extract text AND character info
            extraction_result = self._extract_data_from_dialogue(line)
            
            if extraction_result:
                translated_text, char_str = extraction_result
                
                item = self._create_item(
                    line_index=line_index,
                    original_text=self._pending_original_from_comment,
                    current_text=translated_text,
                    item_type=ItemType.DIALOGUE,
                    context=self._current_context,
                    parsed_data={
                        'indent': line[:len(line) - len(line.lstrip())],
                        'original_line': line,
                        'character': char_str, # Store character tag
                        'comment_line_index': self._pending_comment_line,
                        'reconstruction_rule': 'translate_dialogue',
                    }
                )
                self._items.append(item)
                
                # Clear pending
                self._pending_original_from_comment = None
                self._pending_comment_line = None
                return
    
    def _extract_text_from_comment(self, content: str) -> Optional[str]:
        """Extract quoted text from a comment line."""
        # Try dialogue pattern: character_id [modifiers] "text"
        match = RenpyPatterns.DIALOGUE_COMMENT.match(content)
        if match:
            return match.group(4)
        
        # Try narration pattern: "text"
        match = RenpyPatterns.NARRATION_COMMENT.match(content)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_data_from_dialogue(self, line: str) -> Optional[Tuple[str, str]]:
        """
        Extract text and character from a dialogue line.
        Returns: (text, character_string) or None
        """
        # Try dialogue pattern
        match = RenpyPatterns.DIALOGUE.match(line)
        if match:
            text = match.group(5)
            # Reconstruct character string (char + modifiers)
            char = match.group(2) or ""
            mod = match.group(3) or ""
            char_full = f"{char}{mod}".strip()
            # If modifiers exist, add space if needed? 
            # Actually group(3) usually includes leading space if pattern is correct?
            # Let's rely on group 2 and 3.
            # In parse_line: prefix = f'{character}{modifiers} '
            # Here we just need 'character' key for format_line_from_components
            if mod:
                 char_full = f"{char}{mod}"
            else:
                 char_full = char
            return text, char_full if char_full else ""
        
        # Try narration pattern
        match = RenpyPatterns.NARRATION.match(line)
        if match:
            return match.group(2), ""
        
        return None
    
    def reset(self):
        """Reset parser state."""
        super().reset()
        self._detected_language = None
        self._pending_old_text = None
        self._pending_old_line = None
        self._pending_original_from_comment = None
        self._pending_comment_line = None

