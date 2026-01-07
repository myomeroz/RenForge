# -*- coding: utf-8 -*-
"""
Ren'Py Regex Patterns

Centralized regex patterns for parsing Ren'Py files.
"""

import re


class RenpyPatterns:
    """
    Collection of regex patterns for parsing Ren'Py syntax.
    
    Organized by category:
    - Context detection (screen, label, translate, etc.)
    - Text extraction (dialogue, narration, menu choices)
    - Translation mode specific (old/new pairs)
    """
    
    # =========================================================================
    # CONTEXT DETECTION PATTERNS
    # =========================================================================
    
    SCREEN_START = re.compile(r'^\s*screen\s+(\w+)\s*(\(.*\))?\s*:', re.IGNORECASE)
    LABEL_START = re.compile(r'^\s*label\s+(\w+)\s*:', re.IGNORECASE)
    PYTHON_START = re.compile(r'^\s*(python|init\s+python)\s*:', re.IGNORECASE)
    TRANSLATE_START = re.compile(r'^\s*translate\s+(\w+)\s+(\w+)\s*:', re.IGNORECASE)
    MENU_START = re.compile(r'^\s*menu\s*:', re.IGNORECASE)
    IMAGE_START = re.compile(r'^\s*image\s+([\w."\'=+\-\*\/\s]+)\s*:', re.IGNORECASE)
    TRANSFORM_START = re.compile(r'^\s*transform\s+([\w.]+)\s*(\(.*\))?\s*:', re.IGNORECASE)
    STYLE_START = re.compile(r'^\s*style\s+(\w+)\s*(?:is\s+(\w+))?\s*:', re.IGNORECASE)
    DEFINE_START = re.compile(r'^\s*(define|default)\s+([a-zA-Z_]\w*)\s*=.*', re.IGNORECASE)
    
    # =========================================================================
    # TEXT EXTRACTION PATTERNS
    # =========================================================================
    
    # Dialogue: "character [modifiers] 'text'"
    DIALOGUE = re.compile(r'^(\s*)([a-zA-Z0-9_]+)((?:\s+[a-zA-Z0-9_]+)*)?(?:\s+([a-z]+))?\s+"((?:\\.|[^"\\])*)"(.*)$')
    DIALOGUE_COMMENT = re.compile(r'^([a-zA-Z0-9_]+)((?:\s+[a-zA-Z0-9_]+)*)?(?:\s+([a-z]+))?\s+"((?:\\.|[^"\\])*)"(.*)$')
    
    # Narration: standalone quoted text
    NARRATION = re.compile(r'^(\s*)"((?:\\.|[^"\\])*)"(.*)$')
    NARRATION_COMMENT = re.compile(r'^"((?:\\.|[^"\\])*)"(.*)$')
    
    # Menu choice: "text":
    MENU_CHOICE = re.compile(r'^(\s*)"((?:\\.|[^"\\])*)"(\s*:.+?)$')
    
    # Variable assignment: $ var = "text"
    VAR_ASSIGN_DOLLAR = re.compile(r'^(\s*)\$\s+([a-zA-Z_]\w*)\s*=\s*"((?:\\.|[^"\\])*)"(.*)$')
    VAR_ASSIGN_PYTHON = re.compile(r'^(\s*)([a-zA-Z_]\w*)\s*=\s*"((?:\\.|[^"\\])*)"(.*)$')
    
    # =========================================================================
    # SCREEN-SPECIFIC PATTERNS
    # =========================================================================
    
    # Screen text elements
    _TEXT_PATTERN = r'(?:\_\(\s*"((?:\\.|[^"\\])*)"\s*\)|"((?:\\.|[^"\\])*)")'
    
    SCREEN_TEXT_STMT = re.compile(r'^(\s*)(text)\s+' + _TEXT_PATTERN + r'(.*)$', re.IGNORECASE)
    SCREEN_BUTTON = re.compile(r'^(\s*)(button|textbutton)\s+' + _TEXT_PATTERN + r'(.*)$', re.IGNORECASE)
    SCREEN_LABEL = re.compile(r'^(\s*)(label)\s+' + _TEXT_PATTERN + r'(.*)$', re.IGNORECASE)
    
    SCREEN_PROP = re.compile(
        r'^(\s*)'
        r'(\w+\s*.*?)??\s*'
        r'(text|tooltip|title|alt|placeholder)\s+'
        + _TEXT_PATTERN +
        r'(.*)$', 
        re.IGNORECASE
    )
    
    SCREEN_GENERIC_TEXT = re.compile(
        r'^(\s*)'
        r'(?:(text|button|textbutton|label)\s+)?'
        r'(?:'
            r'"((?:\\.|[^"\\])*)"'
          r'|'
            r'_\("((?:\\.|[^"\\])*)"\)'
        r')'
        r'(.*)$'
    )
    
    # =========================================================================
    # TRANSLATE MODE PATTERNS
    # =========================================================================
    
    TRANSLATE_OLD = re.compile(r'^(\s*)old\s+"((?:\\.|[^"\\])*)"(.*)$')
    TRANSLATE_NEW = re.compile(r'^(\s*)new\s+"((?:\\.|[^"\\])*)"(.*)$')
    TRANSLATE_COMMENT = re.compile(r'^(\s*)#\s?(.*)')
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    @staticmethod
    def get_indentation(line: str) -> int:
        """Get the number of leading spaces in a line."""
        return len(line) - len(line.lstrip(' '))
    
    @classmethod
    def is_translate_block_start(cls, line: str) -> bool:
        """Check if line starts a translate block."""
        return bool(cls.TRANSLATE_START.match(line.strip()))
    
    @classmethod
    def is_context_block_start(cls, line: str) -> bool:
        """Check if line starts any context block."""
        patterns = [
            cls.SCREEN_START,
            cls.LABEL_START,
            cls.PYTHON_START,
            cls.TRANSLATE_START,
            cls.MENU_START,
        ]
        stripped = line.strip()
        return any(p.match(stripped) for p in patterns)
