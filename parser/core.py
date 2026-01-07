# -*- coding: utf-8 -*-
"""
Parser Core Functions

Main entry points for parsing, providing backward compatibility
with the old renforge_parser module.
"""

from typing import List, Tuple, Optional

from renforge_logger import get_logger
from renforge_models import ParsedItem
from parser.translate_parser import TranslateParser
from parser.direct_parser import DirectParser

logger = get_logger("parser.core")


def parse_file(lines: List[str], mode: Optional[str] = None) -> Tuple[List[ParsedItem], Optional[str]]:
    """
    Parse a Ren'Py file.
    
    Automatically detects the appropriate parser based on content,
    or uses the specified mode.
    
    Args:
        lines: List of file lines
        mode: Optional mode override ('translate' or 'direct')
        
    Returns:
        Tuple of (parsed items, detected language code or None)
    """
    if mode == "translate":
        parser = TranslateParser()
    elif mode == "direct":
        parser = DirectParser()
    else:
        # Auto-detect
        translate_parser = TranslateParser()
        if translate_parser.can_parse(lines):
            parser = translate_parser
        else:
            parser = DirectParser()
    
    return parser.parse(lines)


def parse_translate_mode(lines: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
    """
    Parse a file in translation mode.
    
    Args:
        lines: List of file lines
        
    Returns:
        Tuple of (parsed items, detected language code)
    """
    parser = TranslateParser()
    return parser.parse(lines)


def parse_direct_mode(lines: List[str]) -> List[ParsedItem]:
    """
    Parse a file in direct mode.
    
    Args:
        lines: List of file lines
        
    Returns:
        List of parsed items
    """
    parser = DirectParser()
    items, _ = parser.parse(lines)
    return items


def format_line_from_components(item_data: ParsedItem, new_text: str) -> str:
    """
    Reconstruct a file line from parsed components.
    
    Args:
        item_data: The ParsedItem with parsing metadata
        new_text: New text to insert
        
    Returns:
        Reconstructed line string
    """
    pd = item_data.parsed_data
    
    indent = pd.get('indent', '')
    prefix = pd.get('prefix', '')
    suffix = pd.get('suffix', '')
    
    # Handle translation mode (new "text")
    if prefix.strip() == 'new':
        return f'{indent}new "{new_text}"{suffix}'
    
    # Handle dialogue with character
    character = pd.get('character', '')
    modifiers = pd.get('modifiers', '')
    if character:
        return f'{indent}{character}{modifiers} "{new_text}"{suffix}'
    
    # Handle screen elements
    keyword = pd.get('keyword', '')
    if keyword:
        return f'{indent}{keyword} "{new_text}"{suffix}'
    
    # Default: simple quoted string
    return f'{indent}{prefix}"{new_text}"{suffix}'


# Backward compatibility: expose the main parsing function
def parse_file_contextually(lines_list: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
    """
    Parse file with context awareness.
    
    This is a backward compatibility wrapper around parse_file().
    """
    return parse_file(lines_list)
