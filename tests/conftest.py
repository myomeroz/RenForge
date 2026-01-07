# -*- coding: utf-8 -*-
"""
RenForge Test Fixtures

Shared fixtures for all tests.
"""

import pytest
import sys
import os
from pathlib import Path
from typing import Generator

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# MODEL FIXTURES
# =============================================================================

@pytest.fixture
def sample_lines() -> list:
    """Sample Ren'Py file lines for testing."""
    return [
        '# Sample Ren\'Py file',
        'translate turkish start_label:',
        '',
        '    # dialogue line',
        '    old "Hello, world!"',
        '    new "Merhaba, dünya!"',
        '',
        '    old "How are you?"',
        '    new ""',
        '',
    ]


@pytest.fixture
def sample_direct_lines() -> list:
    """Sample direct mode file lines."""
    return [
        'label start:',
        '    "Welcome to the game."',
        '    e "Hello there!"',
        '    menu:',
        '        "Option 1":',
        '            jump option1',
        '        "Option 2":',
        '            jump option2',
    ]


@pytest.fixture
def settings_model():
    """Fresh SettingsModel instance for testing."""
    from models.settings_model import SettingsModel
    SettingsModel.reset_instance()
    return SettingsModel.instance()


@pytest.fixture
def project_model():
    """Fresh ProjectModel instance for testing."""
    from models.project_model import ProjectModel
    return ProjectModel()


@pytest.fixture
def parsed_file(sample_lines):
    """Sample ParsedFile for testing."""
    from models.parsed_file import ParsedFile, ParsedItem
    from renforge_enums import FileMode, ItemType, ContextType
    
    items = [
        ParsedItem(
            line_index=5,
            original_text="Hello, world!",
            current_text="Merhaba, dünya!",
            initial_text="Merhaba, dünya!",
            type=ItemType.DIALOGUE,
            parsed_data={'indent': '    ', 'prefix': 'new '},
        ),
        ParsedItem(
            line_index=8,
            original_text="How are you?",
            current_text="",
            initial_text="",
            type=ItemType.DIALOGUE,
            parsed_data={'indent': '    ', 'prefix': 'new '},
        ),
    ]
    
    return ParsedFile(
        file_path="/test/sample.rpy",
        mode=FileMode.TRANSLATE,
        lines=sample_lines,
        items=items,
    )


# =============================================================================
# CONTROLLER FIXTURES
# =============================================================================

@pytest.fixture
def translation_controller(settings_model):
    """TranslationController instance for testing."""
    from controllers.translation_controller import TranslationController
    return TranslationController(settings_model)


@pytest.fixture
def file_controller(project_model, settings_model):
    """FileController instance for testing."""
    from controllers.file_controller import FileController
    return FileController(project_model, settings_model)


@pytest.fixture
def app_controller():
    """AppController instance for testing."""
    from controllers.app_controller import AppController
    return AppController()


# =============================================================================
# DI FIXTURES
# =============================================================================

@pytest.fixture
def di_container():
    """Fresh DIContainer for testing."""
    from interfaces.di_container import DIContainer
    DIContainer.reset_instance()
    return DIContainer()


# =============================================================================
# TEMP FILE FIXTURES
# =============================================================================

@pytest.fixture
def temp_rpy_file(tmp_path, sample_lines) -> Path:
    """Create a temporary .rpy file for testing."""
    file_path = tmp_path / "test_file.rpy"
    file_path.write_text('\n'.join(sample_lines), encoding='utf-8')
    return file_path


@pytest.fixture
def temp_project_dir(tmp_path) -> Path:
    """Create a temporary project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    game_dir = project_dir / "game"
    game_dir.mkdir()
    
    tl_dir = game_dir / "tl" / "turkish"
    tl_dir.mkdir(parents=True)
    
    # Create a sample file
    sample_file = tl_dir / "dialogue.rpy"
    sample_file.write_text('translate turkish start:\n    old "Test"\n    new ""\n')
    
    return project_dir
