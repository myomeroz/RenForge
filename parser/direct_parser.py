# -*- coding: utf-8 -*-
"""
Direct Mode Parser

Parser for standard Ren'Py script files (direct editing mode).
"""

from typing import List, Tuple, Optional

from renforge_logger import get_logger
from renforge_enums import ContextType, ItemType
from models.parsed_file import ParsedItem
from parser.base import BaseParser
from parser.patterns import RenpyPatterns

logger = get_logger("parser.direct")


# Keywords that indicate non-text statements
NON_TEXT_KEYWORDS = {
    'play', 'queue', 'stop', 'show', 'scene', 'hide', 'with', 'window', 'image',
    'movie', 'voice', 'sound', 'music', 'style', 'transform', 'animation',
    'call', 'jump', 'return', '$', 'init', 'python', 'label', 'screen', 'menu',
    'if', 'while', 'for', 'pass', 'add'
}


class DirectParser(BaseParser):
    """
    Parser for direct mode files.
    
    Handles standard Ren'Py script files with dialogue, narration,
    menu choices, and screen elements.
    """
    
    def __init__(self):
        super().__init__()
        self._in_menu = False
        self._menu_indent = 0
    
    def can_parse(self, lines: List[str]) -> bool:
        """
        Check if file is suitable for direct parsing.
        
        Returns True for any .rpy file that isn't a translate file.
        """
        for line in lines[:100]:
            if RenpyPatterns.is_translate_block_start(line):
                return False  # Use TranslateParser instead
        return True
    
    def parse(self, lines: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
        """
        Parse script file into items.
        
        Returns:
            Tuple of (items list, None for language detection)
        """
        self.reset()
        
        for i, line in enumerate(lines):
            self._process_line(i, line, lines)
        
        logger.debug(f"Parsed {len(self._items)} items in direct mode")
        return self._items, None
    
    def _process_line(self, line_index: int, line: str, all_lines: List[str]):
        """Process a single line."""
        stripped = line.strip()
        indent = self._get_indentation(line)
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            return
        
        # Update context based on block starts
        self._update_context(stripped, indent)
        
        # Skip non-text keywords
        first_word = stripped.split()[0] if stripped.split() else ''
        if first_word.lower() in NON_TEXT_KEYWORDS:
            return
        
        # Try to match text patterns
        if self._try_menu_choice(line_index, line, stripped, indent):
            return

        if self._try_dialogue(line_index, line, stripped, indent):
            return
        
        if self._try_narration(line_index, line, stripped, indent):
            return
        
        if self._current_context == ContextType.SCREEN:
            self._try_screen_text(line_index, line, stripped, indent)
    
    def _update_context(self, stripped: str, indent: int):
        """Update current context based on line content."""
        # Check for context block starts
        if RenpyPatterns.LABEL_START.match(stripped):
            self._current_context = ContextType.LABEL
            self._current_indent = indent
            return
        
        if RenpyPatterns.SCREEN_START.match(stripped):
            self._current_context = ContextType.SCREEN
            self._current_indent = indent
            return
        
        if RenpyPatterns.MENU_START.match(stripped):
            self._in_menu = True
            self._menu_indent = indent
            self._current_context = ContextType.MENU
            return
        
        if RenpyPatterns.PYTHON_START.match(stripped):
            self._current_context = ContextType.PYTHON
            self._current_indent = indent
            return
        
        # Exit menu if indent decreases
        if self._in_menu and indent <= self._menu_indent:
            self._in_menu = False
    
    def _try_dialogue(self, line_index: int, line: str, stripped: str, indent: int) -> bool:
        """Try to match dialogue pattern."""
        match = RenpyPatterns.DIALOGUE.match(line)
        if match:
            character = match.group(2)
            modifiers = match.group(3) or ""
            text = match.group(5)
            suffix = match.group(6)
            
            item = self._create_item(
                line_index=line_index,
                original_text=text,
                current_text=text,
                item_type=ItemType.DIALOGUE,
                context=self._current_context,
                parsed_data={
                    'indent': match.group(1),
                    'character': character,
                    'character_tag': character,
                    'modifiers': modifiers,
                    'prefix': f'{character}{modifiers} ',
                    'suffix': suffix,
                    'reconstruction_rule': 'standard',
                }
            )
            self._items.append(item)
            return True
        return False
    
    def _try_narration(self, line_index: int, line: str, stripped: str, indent: int) -> bool:
        """Try to match narration pattern."""
        match = RenpyPatterns.NARRATION.match(line)
        if match:
            text = match.group(2)
            suffix = match.group(3)
            
            item = self._create_item(
                line_index=line_index,
                original_text=text,
                current_text=text,
                item_type=ItemType.NARRATION,
                context=self._current_context,
                parsed_data={
                    'indent': match.group(1),
                    'prefix': '',
                    'suffix': suffix,
                    'reconstruction_rule': 'narration',
                }
            )
            self._items.append(item)
            return True
        return False
    
    def _try_menu_choice(self, line_index: int, line: str, stripped: str, indent: int) -> bool:
        """Try to match menu choice pattern."""
        if not self._in_menu:
            return False
        
        match = RenpyPatterns.MENU_CHOICE.match(line)
        if match:
            text = match.group(2)
            suffix = match.group(3)
            
            item = self._create_item(
                line_index=line_index,
                original_text=text,
                current_text=text,
                item_type=ItemType.CHOICE,
                context=ContextType.MENU,
                parsed_data={
                    'indent': match.group(1),
                    'prefix': '',
                    'suffix': suffix,
                    'reconstruction_rule': 'choice',
                }
            )
            self._items.append(item)
            return True
        return False
    
    def _try_screen_text(self, line_index: int, line: str, stripped: str, indent: int):
        """Try to match screen text elements."""
        # Try screen text statement
        match = RenpyPatterns.SCREEN_TEXT_STMT.match(line)
        if match:
            text = self._extract_text_from_match(match, (3, 4))
            if text:
                item = self._create_item(
                    line_index=line_index,
                    original_text=text,
                    current_text=text,
                    item_type=ItemType.SCREEN_TEXT_STATEMENT,
                    context=ContextType.SCREEN,
                    parsed_data={
                        'indent': match.group(1),
                        'keyword': match.group(2),
                        'prefix': f'{match.group(2)} ',
                        'suffix': match.group(5),
                        'reconstruction_rule': 'screen_text_statement',
                    }
                )
                self._items.append(item)
                return
        
        # Try button/textbutton
        match = RenpyPatterns.SCREEN_BUTTON.match(line)
        if match:
            text = self._extract_text_from_match(match, (3, 4))
            if text:
                item = self._create_item(
                    line_index=line_index,
                    original_text=text,
                    current_text=text,
                    item_type=ItemType.SCREEN_BUTTON,
                    context=ContextType.SCREEN,
                    parsed_data={
                        'indent': match.group(1),
                        'keyword': match.group(2),
                        'prefix': f'{match.group(2)} ',
                        'suffix': match.group(5),
                        'reconstruction_rule': 'screen_button',
                    }
                )
                self._items.append(item)
    
    def reset(self):
        """Reset parser state."""
        super().reset()
        self._in_menu = False
        self._menu_indent = 0
