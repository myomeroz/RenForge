# -*- coding: utf-8 -*-
"""
Base Parser Classes

Abstract base classes and Strategy pattern interfaces for parsing.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any, Protocol
from dataclasses import dataclass

from renforge_logger import get_logger
from renforge_enums import ContextType, ItemType
from models.parsed_file import ParsedItem

logger = get_logger("parser.base")


class ParserStrategy(Protocol):
    """
    Protocol for parser strategies.
    
    Defines the interface that all parser implementations must follow.
    Using Protocol allows structural subtyping without explicit inheritance.
    """
    
    def parse(self, lines: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
        """
        Parse lines into ParsedItems.
        
        Args:
            lines: List of file lines
            
        Returns:
            Tuple of (parsed items, detected language code or None)
        """
        ...
    
    def can_parse(self, lines: List[str]) -> bool:
        """
        Check if this parser can handle the given content.
        
        Args:
            lines: List of file lines
            
        Returns:
            True if this parser is appropriate for the content
        """
        ...


class BaseParser(ABC):
    """
    Abstract base class for parsers.
    
    Provides common functionality for all parser implementations.
    """
    
    def __init__(self):
        self._current_context: ContextType = ContextType.GLOBAL
        self._current_indent: int = 0
        self._items: List[ParsedItem] = []
        
    @abstractmethod
    def parse(self, lines: List[str]) -> Tuple[List[ParsedItem], Optional[str]]:
        """Parse lines into ParsedItems."""
        pass
    
    @abstractmethod
    def can_parse(self, lines: List[str]) -> bool:
        """Check if this parser can handle the content."""
        pass
    
    def _get_indentation(self, line: str) -> int:
        """Get the number of leading spaces."""
        return len(line) - len(line.lstrip(' '))
    
    def _is_blank_or_comment(self, line: str) -> bool:
        """Check if line is blank or a comment."""
        stripped = line.strip()
        return not stripped or stripped.startswith('#')
    
    def _extract_text_from_match(self, match, group_indices: Tuple[int, ...]) -> Optional[str]:
        """
        Extract text from regex match groups.
        
        Args:
            match: Regex match object
            group_indices: Tuple of group indices to try
            
        Returns:
            First non-None group value, or None
        """
        for idx in group_indices:
            try:
                value = match.group(idx)
                if value is not None:
                    return value
            except IndexError:
                continue
        return None
    
    def _create_item(
        self,
        line_index: int,
        original_text: str,
        current_text: str,
        item_type: ItemType,
        context: ContextType,
        parsed_data: dict
    ) -> ParsedItem:
        """Create a ParsedItem with standard fields."""
        return ParsedItem(
            line_index=line_index,
            original_text=original_text,
            current_text=current_text,
            initial_text=current_text,
            type=item_type,
            context=context,
            parsed_data=parsed_data,
        )
    
    def reset(self):
        """Reset parser state for new file."""
        self._current_context = ContextType.GLOBAL
        self._current_indent = 0
        self._items = []
