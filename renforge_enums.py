"""
RenForge Enum Tanımları

Parser bağlam tipleri ve öğe tipleri için tip-güvenli enum'lar.
"""

from enum import Enum


class ContextType(str, Enum):
    """Parser bağlam tipleri"""
    GLOBAL = 'global'
    SCREEN = 'screen'
    LABEL = 'label'
    PYTHON = 'python'
    TRANSLATE = 'translate'
    TRANSLATE_STRINGS = 'translate_strings'
    MENU = 'menu'
    VARIABLE = 'variable'
    IMAGE_DEF = 'image_def'
    TRANSFORM_DEF = 'transform_def'
    STYLE_DEF = 'style_def'
    DEFINE_DEF = 'define_def'


class ItemType(str, Enum):
    """Parse edilen öğe tipleri"""
    DIALOGUE = 'dialogue'
    NARRATION = 'narration'
    CHOICE = 'choice'
    TRANSLATE_TRANSLATION = 'translate_translation'
    TRANSLATE_OLD = 'translate_old'
    TRANSLATE_NEW = 'translate_new'
    TRANSLATE_POTENTIAL_ORIGINAL = 'translate_potential_original'
    SCREEN_TEXT_PROPERTY = 'screen_text_property'
    SCREEN_BUTTON = 'screen_button'
    SCREEN_LABEL = 'screen_label'
    SCREEN_TEXT_STATEMENT = 'screen_text_statement'
    VARIABLE = 'variable'


class FileMode(str, Enum):
    """Dosya çalışma modları"""
    DIRECT = 'direct'
    TRANSLATE = 'translate'
