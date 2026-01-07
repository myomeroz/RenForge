# -*- coding: utf-8 -*-
"""
Translate Mode Parser

Parser for Ren'Py translation files (translate blocks with old/new pairs).
"""

from typing import List, Tuple, Optional

from renforge_logger import get_logger
from renforge_enums import ContextType, ItemType
from renforge_models import ParsedItem
from parser.base import BaseParser
from parser.patterns import RenpyPatterns

logger = get_logger("parser.translate")


class TranslateParser(BaseParser):
    """
    Parser for translation mode files.
    
    Handles files with translate blocks containing old/new string pairs.
    Example:
        translate turkish start_label:
            old "Hello"
            new "Merhaba"
    """
    
    def __init__(self):
        super().__init__()
        self._detected_language: Optional[str] = None
        self._pending_old_text: Optional[str] = None
        self._pending_old_line: Optional[int] = None
    
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
                }
            )
            self._items.append(item)
            
            # Clear pending
            self._pending_old_text = None
            self._pending_old_line = None
            return
        
        # Handle comment-style translation (# dialogue)
        if stripped.startswith('#'):
            self._process_comment_line(line_index, line, stripped)
    
    def _process_comment_line(self, line_index: int, line: str, stripped: str):
        """Process a comment line that may contain dialogue."""
        # Extract content after #
        comment_content = stripped[1:].strip()
        
        # Try to match dialogue pattern
        match = RenpyPatterns.DIALOGUE_COMMENT.match(comment_content)
        if match:
            character = match.group(1)
            text = match.group(4)
            
            item = self._create_item(
                line_index=line_index,
                original_text=text,
                current_text=text,
                item_type=ItemType.DIALOGUE,
                context=self._current_context,
                parsed_data={
                    'character': character,
                    'is_comment': True,
                    'prefix': '',
                }
            )
            self._items.append(item)
            return
        
        # Try narration pattern
        match = RenpyPatterns.NARRATION_COMMENT.match(comment_content)
        if match:
            text = match.group(1)
            
            item = self._create_item(
                line_index=line_index,
                original_text=text,
                current_text=text,
                item_type=ItemType.NARRATION,
                context=self._current_context,
                parsed_data={
                    'is_comment': True,
                    'prefix': '',
                }
            )
            self._items.append(item)
    
    def reset(self):
        """Reset parser state."""
        super().reset()
        self._detected_language = None
        self._pending_old_text = None
        self._pending_old_line = None
