# -*- coding: utf-8 -*-
"""
RenForge File Controller

Handles file-related business logic:
- Opening and parsing files
- Saving files
- File mode detection
"""

from typing import Optional, List, Tuple
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from renforge_logger import get_logger
from locales import tr
from models.parsed_file import ParsedFile, ParsedItem
from models.project_model import ProjectModel
from models.settings_model import SettingsModel
from renforge_enums import FileMode
import renforge_parser as parser
import renforge_core as core

logger = get_logger("controllers.file")


class FileController(QObject):
    """
    Controller for file operations.
    
    Responsibilities:
    - Open and parse Ren'Py files
    - Save files with updated content
    - Detect file mode (direct/translate)
    - Manage file state
    
    Signals:
        file_opened(ParsedFile): Emitted when a file is successfully opened
        file_saved(str): Emitted with file path when saved
        file_closed(str): Emitted with file path when closed
        file_error(str): Emitted with error message
        mode_detection_needed(str, str): Emitted when manual mode selection needed (path, detected)
    """
    
    file_opened = pyqtSignal(object)  # ParsedFile
    file_saved = pyqtSignal(str)  # path
    file_closed = pyqtSignal(str)  # path
    file_error = pyqtSignal(str)  # message
    mode_detection_needed = pyqtSignal(str, str)  # path, detected_mode
    
    def __init__(
        self, 
        project_model: Optional[ProjectModel] = None,
        settings: Optional[SettingsModel] = None
    ):
        """
        Initialize the file controller.
        
        Args:
            project_model: Project model instance
            settings: Settings model instance
        """
        super().__init__()
        self._project = project_model or ProjectModel()
        self._settings = settings or SettingsModel.instance()
        
        logger.debug("FileController initialized")
    
    # =========================================================================
    # FILE OPENING
    # =========================================================================
    
    def open_file(
        self, 
        file_path: str, 
        mode: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[ParsedFile]:
        """
        Open and parse a Ren'Py file.
        
        Args:
            file_path: Path to the file
            mode: 'direct' or 'translate', or None for auto-detect
            output_path: Optional different save path
            
        Returns:
            ParsedFile instance, or None on failure
        """
        path = Path(file_path)
        
        if not path.is_file():
            self.file_error.emit(tr("error_file_not_found", path=file_path))
            return None
        
        if path.suffix.lower() != '.rpy':
            self.file_error.emit(tr("error_invalid_extension"))
            return None
        
        # Check if already open
        if self._project.is_file_open(file_path):
            logger.info(f"File already open: {path.name}")
            return self._project.get_file(file_path)
        
        try:
            # Read file content
            lines = core.read_file_lines(file_path)
            if lines is None:
                self.file_error.emit(tr("error_reading_file", path=file_path))
                return None
            
            # Detect mode if not specified
            file_mode = self._determine_mode(lines, mode)
            
            # Parse file
            items, detected_lang = self._parse_file(lines, file_mode)
            
            if items is None:
                self.file_error.emit(tr("error_parsing_file", path=file_path))
                return None
            
            # Create ParsedFile
            parsed_file = ParsedFile(
                file_path=file_path,
                mode=file_mode,
                lines=lines,
                items=items,
                output_path=output_path or file_path,
                target_language=detected_lang or self._settings.default_target_language,
                source_language=self._settings.default_source_language,
                selected_model=self._settings.default_model
            )
            
            # Add to project
            self._project.add_file(parsed_file)
            
            self.file_opened.emit(parsed_file)
            logger.info(f"Opened file: {path.name} ({file_mode.value}, {len(items)} items)")
            
            return parsed_file
            
        except Exception as e:
            logger.error(f"Error opening file {file_path}: {e}")
            self.file_error.emit(str(e))
            return None
    
    def _determine_mode(self, lines: List[str], requested_mode: Optional[str]) -> FileMode:
        """Determine the file mode."""
        if requested_mode == "translate":
            return FileMode.TRANSLATE
        elif requested_mode == "direct":
            return FileMode.DIRECT
        
        # Auto-detect
        detected = self._detect_mode(lines)
        
        # Check settings for auto/manual
        if self._settings.mode_selection_method == "manual":
            # Will need to emit signal for UI to ask user
            pass
        
        return detected
    
    def _detect_mode(self, lines: List[str]) -> FileMode:
        """
        Detect file mode from content.
        
        Returns:
            FileMode.TRANSLATE if translation blocks found, else DIRECT
        """
        for line in lines[:100]:  # Check first 100 lines
            stripped = line.strip()
            if stripped.startswith("translate ") and ":" in stripped:
                return FileMode.TRANSLATE
        
        return FileMode.DIRECT
    
    def _parse_file(
        self, 
        lines: List[str], 
        mode: FileMode
    ) -> Tuple[Optional[List[ParsedItem]], Optional[str]]:
        """
        Parse file lines into ParsedItems.
        
        Returns:
            Tuple of (items list, detected language code)
        """
        try:
            if mode == FileMode.TRANSLATE:
                items, detected_lang = parser.parse_translate_mode(lines)
            else:
                items = parser.parse_direct_mode(lines)
                detected_lang = None
            
            return items, detected_lang
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None, None
    
    # =========================================================================
    # FILE SAVING
    # =========================================================================
    
    def save_file(self, parsed_file: ParsedFile) -> bool:
        """
        Save a ParsedFile to disk.
        
        Args:
            parsed_file: The file to save
            
        Returns:
            True if successful
        """
        try:
            # Update lines with current item values
            self._apply_items_to_lines(parsed_file)
            
            # Write to disk
            success = core.save_lines_to_file(
                parsed_file.output_path, 
                parsed_file.lines
            )
            
            if success:
                parsed_file.is_modified = False
                self.file_saved.emit(parsed_file.file_path)
                logger.info(f"Saved file: {parsed_file.filename}")
                return True
            else:
                self.file_error.emit(tr("error_saving_file", path=parsed_file.output_path))
                return False
                
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            self.file_error.emit(str(e))
            return False
    
    def _apply_items_to_lines(self, parsed_file: ParsedFile):
        """Apply item changes back to lines array."""
        for item in parsed_file.items:
            if item.is_modified_session:
                line_idx = item.line_index
                parsed_data = item.parsed_data
                
                # Reconstruct line based on type and mode
                new_line = self._reconstruct_line(item, parsed_file.mode)
                parsed_file.update_line(line_idx, new_line)
    
    def _reconstruct_line(self, item: ParsedItem, mode: FileMode) -> str:
        """Reconstruct a file line from ParsedItem."""
        pd = item.parsed_data
        indent = pd.get('indent', '')
        prefix = pd.get('prefix', '')
        suffix = pd.get('suffix', '')
        
        text = item.current_text
        
        # Basic reconstruction - can be extended for different item types
        return f'{indent}{prefix}"{text}"{suffix}'
    
    # =========================================================================
    # FILE CLOSING
    # =========================================================================
    
    def close_file(self, file_path: str, force: bool = False) -> bool:
        """
        Close a file.
        
        Args:
            file_path: Path of the file to close
            force: If True, close even if modified
            
        Returns:
            True if closed, False if cancelled or error
        """
        parsed_file = self._project.get_file(file_path)
        
        if not parsed_file:
            return True  # Already closed
        
        if parsed_file.is_modified and not force:
            # Caller should handle unsaved changes prompt
            return False
        
        self._project.close_file(file_path)
        self.file_closed.emit(file_path)
        
        return True
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def is_file_modified(self, file_path: str) -> bool:
        """Check if a file has unsaved changes."""
        parsed_file = self._project.get_file(file_path)
        return parsed_file.is_modified if parsed_file else False
    
    def get_modified_files(self) -> List[ParsedFile]:
        """Get all files with unsaved changes."""
        return self._project.modified_files
    
    def __repr__(self) -> str:
        return f"FileController(open_files={self._project.open_file_count})"
