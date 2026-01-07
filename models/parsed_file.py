# -*- coding: utf-8 -*-
"""
RenForge ParsedFile Model

Extends TabData to provide a complete file model with:
- File operations (load, save)
- Observer pattern for change notifications
- Encapsulated business logic
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Callable
from pathlib import Path

from renforge_enums import ItemType, FileMode, ContextType
from renforge_logger import get_logger

logger = get_logger("models.parsed_file")


@dataclass
class ParsedItem:
    """
    Represents a single editable item (dialogue, string, etc.) in the editor.
    Unifies 'Translate' and 'Direct' mode items into a single structure.

    Attributes:
        line_index (int): The line number in the file (0-indexed).
        original_text (str): The original source text.
        current_text (str): The text currently being edited.
        initial_text (str): The text value at the start of the session.
        type (ItemType): The type of the item.
        parsed_data (Dict[str, Any]): Low-level parser data.
        context (ContextType): The context in which the item was found.
        is_modified_session (bool): True if modified in current session.
        has_breakpoint (bool): True if a breakpoint is set.
        original_line_index (Optional[int]): (Translate Mode) Original line number.
        character_trans (Optional[str]): (Translate Mode) Character tag.
        block_language (Optional[str]): (Translate Mode) Language code.
        character_tag (Optional[str]): Character tag for the item.
        variable_name (Optional[str]): Variable name if applicable.
    """
    line_index: int
    original_text: str
    current_text: str
    initial_text: str
    type: ItemType
    parsed_data: Dict[str, Any]
    context: ContextType = ContextType.GLOBAL
    
    is_modified_session: bool = False
    has_breakpoint: bool = False
    
    original_line_index: Optional[int] = None
    character_trans: Optional[str] = None
    block_language: Optional[str] = None
    character_tag: Optional[str] = None
    variable_name: Optional[str] = None

    def get_text(self) -> str:
        """Get the current text content."""
        return self.current_text

    def set_text(self, value: str):
        """Set the current text content and update modification status."""
        self.current_text = value
        self.is_modified_session = (self.current_text != self.initial_text)

    def reset_to_initial(self):
        """Reset current text to initial value."""
        self.current_text = self.initial_text
        self.is_modified_session = False

    def __getitem__(self, key):
        """Backward compatibility for dictionary access."""
        if hasattr(self, key):
            return getattr(self, key)
        if key == 'text':
            return self.current_text
        raise KeyError(f"'{key}' not found in ParsedItem")

    def get(self, key, default=None):
        """Backward compatibility for dictionary get."""
        try:
            return self[key]
        except KeyError:
            return default
            
    def copy(self):
        """Create a copy of this item."""
        from dataclasses import replace
        return replace(self)


class ParsedFile:
    """
    Represents a complete parsed file with all its items and state.
    Implements the Observer pattern for change notifications.
    
    This is the primary Model class for file data in MVC architecture.
    """
    
    def __init__(
        self,
        file_path: str,
        mode: FileMode,
        lines: List[str],
        items: List[ParsedItem],
        breakpoints: Optional[Set[int]] = None,
        output_path: Optional[str] = None,
        target_language: Optional[str] = None,
        source_language: Optional[str] = None,
        selected_model: Optional[str] = None
    ):
        """
        Initialize a ParsedFile model.
        
        Args:
            file_path: Absolute path to the source file.
            mode: The editing mode (direct or translate).
            lines: List of all lines in the file.
            items: List of parsed editable items.
            breakpoints: Set of line numbers with breakpoints.
            output_path: Path where the file will be saved.
            target_language: Target language code.
            source_language: Source language code.
            selected_model: Selected AI model name.
        """
        self._file_path = file_path
        self._mode = mode
        self._lines = lines
        self._items = items
        self._breakpoints = breakpoints or set()
        self._output_path = output_path or file_path
        self._target_language = target_language
        self._source_language = source_language
        self._selected_model = selected_model
        
        # State
        self._item_index = -1
        self._is_modified = False
        
        # Observer pattern - callbacks for change notifications
        self._observers: Dict[str, List[Callable]] = {
            'modified': [],
            'item_changed': [],
            'items_updated': [],
            'breakpoints_changed': [],
        }
        
        logger.debug(f"ParsedFile created: {Path(file_path).name} ({mode.value}, {len(items)} items)")

    # =============================================================================
    # PROPERTIES
    # =============================================================================
    
    @property
    def file_path(self) -> str:
        return self._file_path
    
    @property
    def mode(self) -> FileMode:
        return self._mode
    
    @property
    def lines(self) -> List[str]:
        return self._lines
    
    @property
    def items(self) -> List[ParsedItem]:
        return self._items
    
    @property
    def breakpoints(self) -> Set[int]:
        return self._breakpoints
    
    @property
    def output_path(self) -> str:
        return self._output_path
    
    @output_path.setter
    def output_path(self, value: str):
        self._output_path = value
    
    @property
    def item_index(self) -> int:
        return self._item_index
    
    @item_index.setter
    def item_index(self, value: int):
        if self._item_index != value:
            self._item_index = value
            self._notify('item_changed', value)
    
    @property
    def is_modified(self) -> bool:
        return self._is_modified
    
    @is_modified.setter
    def is_modified(self, value: bool):
        if self._is_modified != value:
            self._is_modified = value
            self._notify('modified', value)
    
    @property
    def target_language(self) -> Optional[str]:
        return self._target_language
    
    @target_language.setter
    def target_language(self, value: Optional[str]):
        self._target_language = value
    
    @property
    def source_language(self) -> Optional[str]:
        return self._source_language
    
    @source_language.setter
    def source_language(self, value: Optional[str]):
        self._source_language = value
    
    @property
    def selected_model(self) -> Optional[str]:
        return self._selected_model
    
    @selected_model.setter
    def selected_model(self, value: Optional[str]):
        self._selected_model = value

    # =============================================================================
    # OBSERVER PATTERN
    # =============================================================================
    
    def subscribe(self, event: str, callback: Callable):
        """
        Subscribe to an event.
        
        Args:
            event: Event name ('modified', 'item_changed', 'items_updated', 'breakpoints_changed')
            callback: Function to call when event occurs
        """
        if event in self._observers:
            self._observers[event].append(callback)
        else:
            logger.warning(f"Unknown event type: {event}")
    
    def unsubscribe(self, event: str, callback: Callable):
        """Unsubscribe from an event."""
        if event in self._observers and callback in self._observers[event]:
            self._observers[event].remove(callback)
    
    def _notify(self, event: str, *args):
        """Notify all subscribers of an event."""
        for callback in self._observers.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Error in observer callback for '{event}': {e}")

    # =============================================================================
    # ITEM OPERATIONS
    # =============================================================================
    
    def get_item(self, index: int) -> Optional[ParsedItem]:
        """Get item at index, or None if out of bounds."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def get_current_item(self) -> Optional[ParsedItem]:
        """Get the currently selected item."""
        return self.get_item(self._item_index)
    
    def update_item_text(self, index: int, new_text: str) -> bool:
        """
        Update the text of an item.
        
        Args:
            index: Item index
            new_text: New text value
            
        Returns:
            True if update was successful
        """
        item = self.get_item(index)
        if item:
            item.set_text(new_text)
            self.is_modified = True
            self._notify('items_updated', [index])
            return True
        return False
    
    def get_modified_items(self) -> List[int]:
        """Get indices of all modified items."""
        return [i for i, item in enumerate(self._items) if item.is_modified_session]
    
    def revert_item(self, index: int) -> bool:
        """Revert an item to its initial text."""
        item = self.get_item(index)
        if item and item.is_modified_session:
            item.reset_to_initial()
            self._notify('items_updated', [index])
            # Check if file is still modified
            self.is_modified = any(i.is_modified_session for i in self._items)
            return True
        return False
    
    def revert_all(self) -> int:
        """Revert all modified items. Returns count of reverted items."""
        reverted = []
        for i, item in enumerate(self._items):
            if item.is_modified_session:
                item.reset_to_initial()
                reverted.append(i)
        
        if reverted:
            self._notify('items_updated', reverted)
            self.is_modified = False
        
        return len(reverted)

    # =============================================================================
    # BREAKPOINT OPERATIONS
    # =============================================================================
    
    def toggle_breakpoint(self, line_index: int) -> bool:
        """
        Toggle breakpoint on a line.
        
        Args:
            line_index: The line index to toggle
            
        Returns:
            True if breakpoint was added, False if removed
        """
        if line_index in self._breakpoints:
            self._breakpoints.discard(line_index)
            added = False
        else:
            self._breakpoints.add(line_index)
            added = True
        
        self._notify('breakpoints_changed', line_index, added)
        return added
    
    def clear_breakpoints(self) -> int:
        """Clear all breakpoints. Returns count cleared."""
        count = len(self._breakpoints)
        self._breakpoints.clear()
        self._notify('breakpoints_changed', None, False)
        return count

    # =============================================================================
    # LINE OPERATIONS
    # =============================================================================
    
    def update_line(self, index: int, content: str) -> bool:
        """Update a line in the file."""
        if 0 <= index < len(self._lines):
            self._lines[index] = content
            return True
        return False
    
    def get_line(self, index: int) -> Optional[str]:
        """Get a line by index."""
        if 0 <= index < len(self._lines):
            return self._lines[index]
        return None

    # =============================================================================
    # UTILITY
    # =============================================================================
    
    @property
    def filename(self) -> str:
        """Get just the filename without path."""
        return Path(self._file_path).name
    
    @property
    def item_count(self) -> int:
        """Get the number of items."""
        return len(self._items)
    
    def __repr__(self) -> str:
        return f"ParsedFile({self.filename}, mode={self._mode.value}, items={len(self._items)})"
