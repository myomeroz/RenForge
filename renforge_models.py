"""
RenForge Data Models

This module defines the data structures used throughout the application, providing
type safety and clear structure for parsed items and file data.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from renforge_enums import ItemType, FileMode, ContextType

@dataclass
class ParsedItem:
    """
    Represents a single editable item (dialogue, string, etc.) in the editor.
    Unifies 'Translate' and 'Direct' mode items into a single structure.

    Attributes:
        line_index (int): The line number in the file (0-indexed). 
                          For 'Translate' mode, this refers to the translation line.
        original_text (str): The original source text (e.g., English dialogue).
        current_text (str): The text currently being edited (translation or direct content).
        initial_text (str): The text value at the start of the editing session (used for modification tracking).
        type (ItemType): The type of the item (e.g., DIALOGUE, MENU, STRING).
        parsed_data (Dict[str, Any]): Low-level data from the parser (indentation, prefixes, etc.).
        context (ContextType): The context in which the item was found (e.g., LABEL, SCREEN).
        is_modified_session (bool): True if the item has been modified in the current session.
        has_breakpoint (bool): True if a breakpoint is set on this line.
        original_line_index (Optional[int]): (Translate Mode) Line number of the original text.
        character_trans (Optional[str]): (Translate Mode) Character tag for the translation line.
        block_language (Optional[str]): (Translate Mode) The language code of the translation block.
        character_tag (Optional[str]): Character tag (Original for translate mode, Current for direct).
        variable_name (Optional[str]): Name of the variable if the item is a variable definition.
    """
    # Common fields
    line_index: int
    original_text: str
    current_text: str
    initial_text: str
    type: ItemType
    parsed_data: Dict[str, Any]
    context: ContextType = ContextType.GLOBAL
    
    # State fields
    is_modified_session: bool = False
    has_breakpoint: bool = False
    
    # Translate Mode specific
    original_line_index: Optional[int] = None
    character_trans: Optional[str] = None
    block_language: Optional[str] = None
    
    # Direct Mode specific / Shared
    character_tag: Optional[str] = None
    variable_name: Optional[str] = None

    def get_text(self) -> str:
        """Get the current text content."""
        return self.current_text

    def set_text(self, value: str):
        """Set the current text content and update modification status."""
        self.current_text = value
        self.is_modified_session = (self.current_text != self.initial_text)

    def __getitem__(self, key):
        """Backward compatibility for dictionary access."""
        if hasattr(self, key):
            return getattr(self, key)
        if key == 'text':
            return self.current_text
        if key == 'parsed_data':
            return self.parsed_data
        raise KeyError(f"'{key}' not found in ParsedItem")

    def get(self, key, default=None):
        """Backward compatibility for dictionary get."""
        try:
            return self[key]
        except KeyError:
            return default
            
    def copy(self):
        """Backward compatibility for copy."""
        from dataclasses import replace
        return replace(self)

@dataclass
class TabData:
    """
    Represents the full state of an open file tab.

    Attributes:
        file_path (str): Absolute path to the source file.
        mode (FileMode): The editing mode ('direct' or 'translate').
        lines (List[str]): List of all lines in the file.
        items (List[ParsedItem]): List of parsed editable items.
        breakpoints (Set[int]): Set of line numbers with breakpoints.
        output_path (str): Path where the file will be saved. Defaults to file_path.
        item_index (int): Index of the currently selected item in `items` list.
        is_modified (bool): True if the file has unsaved changes.
        target_language (Optional[str]): (Translate Mode) Target language code.
        source_language (Optional[str]): (Translate Mode) Source language code.
        selected_model (Optional[str]): Selected AI model name for this tab.
    """
    file_path: str
    mode: FileMode
    lines: List[str]
    items: List[ParsedItem]
    breakpoints: Set[int]
    
    # Editor State
    output_path: str
    item_index: int = -1
    is_modified: bool = False
    
    # AI / Translation Context
    target_language: Optional[str] = None
    source_language: Optional[str] = None
    selected_model: Optional[str] = None

    def __post_init__(self):
        # Ensure output_path defaults to file_path if not provided (though it's non-optional above)
        if not self.output_path:
            self.output_path = self.file_path
