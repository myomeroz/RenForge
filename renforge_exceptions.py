# -*- coding: utf-8 -*-
"""
RenForge Exceptions Module
Custom exception classes for structured error handling across the application.
"""


class RenForgeError(Exception):
    """
    Base exception class for all RenForge-related errors.
    
    Attributes:
        message: Human-readable error message
        details: Optional additional details (dict, string, etc.)
    """
    
    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# =============================================================================
# Parser Exceptions
# =============================================================================

class ParserError(RenForgeError):
    """Base exception for parser-related errors."""
    pass


class ParseError(ParserError):
    """Raised when a line cannot be parsed correctly."""
    
    def __init__(self, message: str, line_number: int = None, line_content: str = None):
        super().__init__(message, details={'line_number': line_number, 'content': line_content})
        self.line_number = line_number
        self.line_content = line_content


class FormatError(ParserError):
    """Raised when formatting a line from components fails."""
    
    def __init__(self, message: str, line_number: int = None):
        super().__init__(message, details={'line_number': line_number})
        self.line_number = line_number


# =============================================================================
# AI Exceptions
# =============================================================================

class AIError(RenForgeError):
    """Base exception for AI-related errors (Gemini, etc.)."""
    pass


class APIKeyError(AIError):
    """Raised when API key is missing or invalid."""
    pass


class ModelError(AIError):
    """Raised when there's an issue with the AI model."""
    
    def __init__(self, message: str, model_name: str = None):
        super().__init__(message, details={'model': model_name})
        self.model_name = model_name


class TranslationError(AIError):
    """Raised when AI translation fails."""
    
    def __init__(self, message: str, source_text: str = None, target_lang: str = None):
        super().__init__(message, details={'source_text': source_text, 'target_lang': target_lang})
        self.source_text = source_text
        self.target_lang = target_lang


class NetworkError(AIError):
    """Raised when there's a network connectivity issue."""
    pass


# =============================================================================
# Core/File Exceptions
# =============================================================================

class CoreError(RenForgeError):
    """Base exception for core module errors."""
    pass


class FileOperationError(CoreError):
    """Raised when a file operation (read/write) fails."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message, details={'file_path': file_path, 'operation': operation})
        self.file_path = file_path
        self.operation = operation


class ModeDetectionError(CoreError):
    """Raised when file mode (translate/direct) cannot be determined."""
    
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message, details={'file_path': file_path})
        self.file_path = file_path


class SaveError(CoreError):
    """Raised when saving changes fails."""
    
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message, details={'file_path': file_path})
        self.file_path = file_path


# =============================================================================
# GUI Exceptions
# =============================================================================

class GUIError(RenForgeError):
    """Base exception for GUI-related errors."""
    pass


class DialogError(GUIError):
    """Raised when a dialog operation fails."""
    pass


class TabError(GUIError):
    """Raised when a tab operation fails."""
    
    def __init__(self, message: str, tab_index: int = None):
        super().__init__(message, details={'tab_index': tab_index})
        self.tab_index = tab_index


class ValidationError(GUIError):
    """Raised when user input validation fails."""
    
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(message, details={'field': field, 'value': value})
        self.field = field
        self.value = value


# =============================================================================
# Settings Exceptions
# =============================================================================

class SettingsError(RenForgeError):
    """Base exception for settings-related errors."""
    pass


class SettingsLoadError(SettingsError):
    """Raised when loading settings fails."""
    pass


class SettingsSaveError(SettingsError):
    """Raised when saving settings fails."""
    pass
