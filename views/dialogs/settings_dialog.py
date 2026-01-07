# -*- coding: utf-8 -*-
"""
RenForge Settings Dialog View

Pure view component for application settings.
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QCheckBox, QPushButton, QGroupBox,
                             QRadioButton, QButtonGroup, QTabWidget, QWidget)
from PyQt6.QtCore import pyqtSignal

from locales import tr
from renforge_logger import get_logger

logger = get_logger("views.dialogs.settings")


class SettingsDialogView(QDialog):
    """
    Dialog for application settings - pure View component.
    
    Signals:
        settings_saved(dict): Emitted with settings dict when saved
    """
    
    settings_saved = pyqtSignal(dict)
    
    def __init__(self, parent=None, current_settings: Optional[Dict[str, Any]] = None,
                 languages: Optional[Dict[str, str]] = None,
                 models: Optional[List[str]] = None):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent widget
            current_settings: Current settings values
            languages: Available languages (code -> name)
            models: Available AI model names
        """
        super().__init__(parent)
        self._current = current_settings or {}
        self._languages = languages or {}
        self._models = models or []
        
        self._setup_ui()
        self._connect_signals()
        self._load_current_values()
        
        logger.debug("SettingsDialogView created")
    
    def _setup_ui(self):
        """Build the UI."""
        self.setWindowTitle(tr("dialog_main_settings"))
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Tab widget for organized settings
        tabs = QTabWidget()
        
        # General tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, tr("settings_defaults"))
        
        # Language tab
        lang_tab = self._create_language_tab()
        tabs.addTab(lang_tab, tr("settings_language"))
        
        # Project tab
        project_tab = self._create_project_tab()
        tabs.addTab(project_tab, tr("settings_project"))
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._save_btn = QPushButton(tr("save"))
        self._save_btn.setDefault(True)
        button_layout.addWidget(self._save_btn)
        
        self._cancel_btn = QPushButton(tr("cancel"))
        button_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Mode selection group
        mode_group = QGroupBox(tr("settings_mode_selection"))
        mode_layout = QVBoxLayout(mode_group)
        
        self._mode_btn_group = QButtonGroup(self)
        
        self._mode_auto = QRadioButton(tr("settings_mode_auto"))
        self._mode_manual = QRadioButton(tr("settings_mode_manual"))
        
        self._mode_btn_group.addButton(self._mode_auto)
        self._mode_btn_group.addButton(self._mode_manual)
        
        mode_layout.addWidget(self._mode_auto)
        mode_layout.addWidget(self._mode_manual)
        
        layout.addWidget(mode_group)
        
        # Default values group
        defaults_group = QGroupBox(tr("settings_defaults"))
        defaults_layout = QVBoxLayout(defaults_group)
        
        # Source language
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel(tr("settings_source_lang")))
        self._source_combo = QComboBox()
        source_layout.addWidget(self._source_combo)
        defaults_layout.addLayout(source_layout)
        
        # Target language
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel(tr("settings_target_lang")))
        self._target_combo = QComboBox()
        target_layout.addWidget(self._target_combo)
        defaults_layout.addLayout(target_layout)
        
        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel(tr("settings_gemini_model")))
        self._model_combo = QComboBox()
        model_layout.addWidget(self._model_combo)
        defaults_layout.addLayout(model_layout)
        
        layout.addWidget(defaults_group)
        layout.addStretch()
        
        return widget
    
    def _create_language_tab(self) -> QWidget:
        """Create the language settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Auto-detect option
        self._use_detected_check = QCheckBox(tr("settings_use_detected_lang"))
        layout.addWidget(self._use_detected_check)
        
        # UI language
        ui_group = QGroupBox(tr("settings_ui_language"))
        ui_layout = QHBoxLayout(ui_group)
        
        ui_layout.addWidget(QLabel(tr("settings_ui_lang_label")))
        self._ui_lang_combo = QComboBox()
        self._ui_lang_combo.addItem("Türkçe", "tr")
        self._ui_lang_combo.addItem("English", "en")
        ui_layout.addWidget(self._ui_lang_combo)
        
        layout.addWidget(ui_group)
        
        restart_label = QLabel(tr("settings_ui_lang_restart"))
        restart_label.setStyleSheet("color: orange; font-size: 10px;")
        layout.addWidget(restart_label)
        
        layout.addStretch()
        
        return widget
    
    def _create_project_tab(self) -> QWidget:
        """Create the project settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self._auto_prepare_check = QCheckBox(tr("settings_auto_prepare"))
        layout.addWidget(self._auto_prepare_check)
        
        layout.addStretch()
        
        return widget
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)
    
    def _load_current_values(self):
        """Load current settings into UI elements."""
        # Populate combos
        for code, name in self._languages.items():
            self._source_combo.addItem(name, code)
            self._target_combo.addItem(name, code)
        
        self._model_combo.addItems(self._models)
        
        # Set current values
        mode = self._current.get("mode_selection_method", "auto")
        if mode == "manual":
            self._mode_manual.setChecked(True)
        else:
            self._mode_auto.setChecked(True)
        
        # Source/target language
        source = self._current.get("default_source_language", "en")
        target = self._current.get("default_target_language", "tr")
        self._set_combo_by_data(self._source_combo, source)
        self._set_combo_by_data(self._target_combo, target)
        
        # Model
        model = self._current.get("default_selected_model", "")
        if model:
            self._model_combo.setCurrentText(model)
        
        # Checkboxes
        self._use_detected_check.setChecked(
            self._current.get("use_detected_target_lang", True))
        self._auto_prepare_check.setChecked(
            self._current.get("auto_prepare_project", True))
        
        # UI language
        ui_lang = self._current.get("ui_language", "tr")
        self._set_combo_by_data(self._ui_lang_combo, ui_lang)
    
    def _set_combo_by_data(self, combo: QComboBox, data: str):
        """Set combo selection by data value."""
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return
    
    def _on_save(self):
        """Handle save button click."""
        settings = self.get_settings()
        self.settings_saved.emit(settings)
        self.accept()
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings from UI."""
        return {
            "mode_selection_method": "manual" if self._mode_manual.isChecked() else "auto",
            "default_source_language": self._source_combo.currentData(),
            "default_target_language": self._target_combo.currentData(),
            "default_selected_model": self._model_combo.currentText(),
            "use_detected_target_lang": self._use_detected_check.isChecked(),
            "auto_prepare_project": self._auto_prepare_check.isChecked(),
            "ui_language": self._ui_lang_combo.currentData(),
        }
