# -*- coding: utf-8 -*-
"""
RenForge Project Model

Manages project state including:
- Opened files tracking
- Project folder structure
- Project-level settings
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable
from pathlib import Path
from enum import Enum

from renforge_logger import get_logger

logger = get_logger("models.project")


class ProjectState(Enum):
    """Project lifecycle states."""
    CLOSED = "closed"
    OPEN = "open"
    MODIFIED = "modified"


@dataclass
class ProjectSettings:
    """Project-specific settings."""
    auto_prepare: bool = True
    default_mode: Optional[str] = None  # 'direct', 'translate', or None for auto
    source_language: Optional[str] = None
    target_language: Optional[str] = None


class ProjectModel:
    """
    Represents a project (folder) with its files and state.
    
    Responsibilities:
    - Track opened files (ParsedFile instances)
    - Manage project folder structure
    - Provide project-level operations
    - Observer pattern for state changes
    """
    
    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize a ProjectModel.
        
        Args:
            project_path: Path to the project folder, or None for no project
        """
        self._project_path: Optional[Path] = Path(project_path) if project_path else None
        self._state = ProjectState.OPEN if project_path else ProjectState.CLOSED
        self._settings = ProjectSettings()
        
        # File tracking
        self._open_files: Dict[str, 'ParsedFile'] = {}  # file_path -> ParsedFile
        self._active_file_path: Optional[str] = None
        
        # Observer pattern
        self._observers: Dict[str, List[Callable]] = {
            'file_opened': [],
            'file_closed': [],
            'file_changed': [],
            'active_file_changed': [],
            'project_state_changed': [],
        }
        
        if project_path:
            logger.debug(f"ProjectModel created: {self._project_path.name}")
        else:
            logger.debug("ProjectModel created (no project)")

    # =============================================================================
    # PROPERTIES
    # =============================================================================
    
    @property
    def project_path(self) -> Optional[Path]:
        """Get the project folder path."""
        return self._project_path
    
    @property
    def project_name(self) -> Optional[str]:
        """Get the project folder name."""
        return self._project_path.name if self._project_path else None
    
    @property
    def state(self) -> ProjectState:
        """Get the current project state."""
        return self._state
    
    @property
    def is_open(self) -> bool:
        """Check if a project is open."""
        return self._project_path is not None
    
    @property
    def settings(self) -> ProjectSettings:
        """Get project settings."""
        return self._settings
    
    @property
    def open_files(self) -> Dict[str, 'ParsedFile']:
        """Get all open files."""
        return self._open_files.copy()
    
    @property
    def open_file_count(self) -> int:
        """Get number of open files."""
        return len(self._open_files)
    
    @property
    def active_file_path(self) -> Optional[str]:
        """Get the currently active file path."""
        return self._active_file_path
    
    @property
    def active_file(self) -> Optional['ParsedFile']:
        """Get the currently active ParsedFile."""
        if self._active_file_path:
            return self._open_files.get(self._active_file_path)
        return None
    
    @property
    def has_unsaved_changes(self) -> bool:
        """Check if any open file has unsaved changes."""
        return any(f.is_modified for f in self._open_files.values())
    
    @property
    def modified_files(self) -> List['ParsedFile']:
        """Get list of files with unsaved changes."""
        return [f for f in self._open_files.values() if f.is_modified]

    # =============================================================================
    # OBSERVER PATTERN
    # =============================================================================
    
    def subscribe(self, event: str, callback: Callable):
        """Subscribe to project events."""
        if event in self._observers:
            self._observers[event].append(callback)
    
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
                logger.error(f"Error in project observer callback for '{event}': {e}")

    # =============================================================================
    # PROJECT OPERATIONS
    # =============================================================================
    
    def open_project(self, project_path: str) -> bool:
        """
        Open a project folder.
        
        Args:
            project_path: Path to the project folder
            
        Returns:
            True if successful
        """
        path = Path(project_path)
        if not path.is_dir():
            logger.error(f"Project path is not a directory: {project_path}")
            return False
        
        # Close existing project if any
        if self._project_path:
            self.close_project()
        
        self._project_path = path
        self._state = ProjectState.OPEN
        self._notify('project_state_changed', self._state)
        
        logger.info(f"Project opened: {path.name}")
        return True
    
    def close_project(self) -> bool:
        """
        Close the current project.
        
        Returns:
            True if successful
        """
        if not self._project_path:
            return False
        
        # Close all open files
        for file_path in list(self._open_files.keys()):
            self.close_file(file_path)
        
        old_name = self._project_path.name
        self._project_path = None
        self._state = ProjectState.CLOSED
        self._notify('project_state_changed', self._state)
        
        logger.info(f"Project closed: {old_name}")
        return True

    # =============================================================================
    # FILE OPERATIONS
    # =============================================================================
    
    def add_file(self, parsed_file: 'ParsedFile') -> bool:
        """
        Add an opened file to the project.
        
        Args:
            parsed_file: The ParsedFile to add
            
        Returns:
            True if added successfully
        """
        file_path = parsed_file.file_path
        
        if file_path in self._open_files:
            logger.warning(f"File already open: {parsed_file.filename}")
            return False
        
        self._open_files[file_path] = parsed_file
        
        # Subscribe to file's modified event
        parsed_file.subscribe('modified', lambda m: self._on_file_modified(file_path, m))
        
        self._notify('file_opened', parsed_file)
        logger.debug(f"File added to project: {parsed_file.filename}")
        
        # Set as active if it's the only file
        if len(self._open_files) == 1:
            self.set_active_file(file_path)
        
        return True
    
    def close_file(self, file_path: str) -> bool:
        """
        Close/remove a file from the project.
        
        Args:
            file_path: Path of the file to close
            
        Returns:
            True if closed successfully
        """
        if file_path not in self._open_files:
            return False
        
        parsed_file = self._open_files.pop(file_path)
        self._notify('file_closed', parsed_file)
        
        # Update active file if needed
        if self._active_file_path == file_path:
            if self._open_files:
                # Switch to another open file
                new_active = next(iter(self._open_files.keys()))
                self.set_active_file(new_active)
            else:
                self._active_file_path = None
                self._notify('active_file_changed', None)
        
        logger.debug(f"File closed: {parsed_file.filename}")
        return True
    
    def get_file(self, file_path: str) -> Optional['ParsedFile']:
        """Get an open file by path."""
        return self._open_files.get(file_path)
    
    def is_file_open(self, file_path: str) -> bool:
        """Check if a file is already open."""
        return file_path in self._open_files
    
    def set_active_file(self, file_path: str) -> bool:
        """
        Set the active (currently viewed) file.
        
        Args:
            file_path: Path of the file to activate
            
        Returns:
            True if successful
        """
        if file_path not in self._open_files:
            return False
        
        if self._active_file_path != file_path:
            self._active_file_path = file_path
            self._notify('active_file_changed', self._open_files[file_path])
        
        return True
    
    def _on_file_modified(self, file_path: str, is_modified: bool):
        """Internal handler for file modification events."""
        self._notify('file_changed', file_path, is_modified)
        
        # Update project state
        if self.has_unsaved_changes:
            self._state = ProjectState.MODIFIED
        else:
            self._state = ProjectState.OPEN if self._project_path else ProjectState.CLOSED

    # =============================================================================
    # FILE DISCOVERY
    # =============================================================================
    
    def get_rpy_files(self) -> List[Path]:
        """
        Get all .rpy files in the project folder (recursive).
        
        Returns:
            List of Path objects for all .rpy files
        """
        if not self._project_path:
            return []
        
        try:
            return list(self._project_path.rglob("*.rpy"))
        except Exception as e:
            logger.error(f"Error scanning project for .rpy files: {e}")
            return []
    
    def get_game_folder(self) -> Optional[Path]:
        """Get the 'game' subfolder if it exists."""
        if not self._project_path:
            return None
        
        game_path = self._project_path / "game"
        return game_path if game_path.is_dir() else None

    # =============================================================================
    # UTILITY
    # =============================================================================
    
    def __repr__(self) -> str:
        if self._project_path:
            return f"ProjectModel({self._project_path.name}, files={len(self._open_files)})"
        return "ProjectModel(no project)"
