# -*- coding: utf-8 -*-
"""
RenForge Parser Package

Modular parser for Ren'Py files using Strategy pattern.
Supports different parsing strategies for various file formats.
"""

from parser.base import BaseParser, ParserStrategy
from parser.translate_parser import TranslateParser
from parser.direct_parser import DirectParser
from parser.patterns import RenpyPatterns

# Re-export main parsing functions for backward compatibility
from parser.core import (
    parse_file,
    parse_translate_mode,
    parse_direct_mode,
    format_line_from_components,
)

__all__ = [
    'BaseParser',
    'ParserStrategy',
    'TranslateParser',
    'DirectParser',
    'RenpyPatterns',
    'parse_file',
    'parse_translate_mode',
    'parse_direct_mode',
    'format_line_from_components',
]
