# -*- coding: utf-8 -*-
"""
Parser Core Functions

Main entry points for parsing, providing backward compatibility
with the old renforge_parser module.
"""

from typing import List, Tuple, Optional, Dict, Any

from renforge_logger import get_logger
from renforge_enums import ItemType
from renforge_models import ParsedItem
from parser.translate_parser import TranslateParser
from parser.direct_parser import DirectParser
from parser.patterns import RenpyPatterns

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


def parse_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single line to identify its type and components.
    Used for 'Insert Line' functionality and ad-hoc parsing.
    
    Args:
        line: The raw line string
        
    Returns:
        Dictionary with parsed data, type, and text, or None if not recognized.
    """
    stripped = line.strip()
    # indent = len(line) - len(line.lstrip(' ')) # Not strictly needed for single line parse unless context matters
    
    # Try Dialogue
    match = RenpyPatterns.DIALOGUE.match(line)
    if match:
        character = match.group(2)
        modifiers = match.group(3) or ""
        text = match.group(5)
        suffix = match.group(6)
        return {
            'type': ItemType.DIALOGUE,
            'text': text,
            'character_tag': character,
            'indent': match.group(1),
            'character': character,
            'modifiers': modifiers,
            'prefix': f'{character}{modifiers} ',
            'suffix': suffix,
            'reconstruction_rule': 'standard'
        }

    # Try Narration
    match = RenpyPatterns.NARRATION.match(line)
    if match:
        text = match.group(2)
        suffix = match.group(3)
        return {
            'type': ItemType.NARRATION,
            'text': text,
            'character_tag': None,
            'indent': match.group(1),
            'prefix': '',
            'suffix': suffix,
            'reconstruction_rule': 'narration'
        }

    # Try Screen Text Statement
    match = RenpyPatterns.SCREEN_TEXT_STMT.match(line)
    if match:
        # Extract text from group 3 or 4
        text = match.group(3) or match.group(4)
        if text:
            return {
                'type': ItemType.SCREEN_TEXT_STATEMENT,
                'text': text,
                'character_tag': None,
                'indent': match.group(1),
                'keyword': match.group(2),
                'prefix': f'{match.group(2)} ',
                'suffix': match.group(5),
                'reconstruction_rule': 'screen_text_statement'
            }

    # Try Screen Button
    match = RenpyPatterns.SCREEN_BUTTON.match(line)
    if match:
        text = match.group(3) or match.group(4)
        if text:
             return {
                'type': ItemType.SCREEN_BUTTON,
                'text': text,
                'character_tag': None,
                'indent': match.group(1),
                'keyword': match.group(2),
                'prefix': f'{match.group(2)} ',
                'suffix': match.group(5),
                'reconstruction_rule': 'screen_button'
            }
            
    return None


# Backward compatibility: expose the main parsing function
def parse_file_contextually(lines_list: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
    """
    Parse file with context awareness.
    
    This is a backward compatibility wrapper around parse_file().
    """
    return parse_file(lines_list)
