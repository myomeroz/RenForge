# -*- coding: utf-8 -*-
"""
RenForge Mode Selection Dialog View

Pure view component for file mode selection.
"""

from typing import Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QRadioButton, QPushButton, QButtonGroup, QGroupBox)
from PyQt6.QtCore import pyqtSignal

from locales import tr
from renforge_logger import get_logger

logger = get_logger("views.dialogs.mode")


class ModeSelectionDialogView(QDialog):
    """
    Dialog for selecting file mode (direct/translate) - pure View component.
    
    Signals:
        mode_selected(str): Emitted with 'direct' or 'translate' when OK clicked
    """
    
    mode_selected = pyqtSignal(str)
    
    def __init__(self, parent=None, file_name: str = "", file_path: str = "",
                 detected_mode: Optional[str] = None):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent widget
            file_name: Name of the file being opened
            file_path: Full path to the file
            detected_mode: Auto-detected mode suggestion
        """
        super().__init__(parent)
        self._file_name = file_name
        self._file_path = file_path
        self._detected_mode = detected_mode
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug(f"ModeSelectionDialogView created for {file_name}")
    
    def _setup_ui(self):
        """Build the UI."""
        self.setWindowTitle(tr("dialog_mode_select"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # File info
        layout.addWidget(QLabel(tr("mode_file", name=self._file_name)))
        
        path_label = QLabel(tr("mode_path", path=self._file_path))
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(path_label)
        
        layout.addSpacing(10)
        
        # Mode selection group
        group = QGroupBox(tr("dialog_mode_select"))
        group_layout = QVBoxLayout(group)
        
        self._mode_group = QButtonGroup(self)
        
        # Direct mode
        self._direct_radio = QRadioButton(tr("mode_direct"))
        self._mode_group.addButton(self._direct_radio)
        group_layout.addWidget(self._direct_radio)
        
        direct_desc = QLabel(tr("mode_direct_desc"))
        direct_desc.setStyleSheet("color: gray; margin-left: 20px;")
        group_layout.addWidget(direct_desc)
        
        group_layout.addSpacing(5)
        
        # Translate mode
        self._translate_radio = QRadioButton(tr("mode_translate"))
        self._mode_group.addButton(self._translate_radio)
        group_layout.addWidget(self._translate_radio)
        
        translate_desc = QLabel(tr("mode_translate_desc"))
        translate_desc.setStyleSheet("color: gray; margin-left: 20px;")
        group_layout.addWidget(translate_desc)
        
        layout.addWidget(group)
        
        # Set default based on detection
        if self._detected_mode == "translate":
            self._translate_radio.setChecked(True)
        else:
            self._direct_radio.setChecked(True)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._ok_btn = QPushButton(tr("ok"))
        self._ok_btn.setDefault(True)
        button_layout.addWidget(self._ok_btn)
        
        self._cancel_btn = QPushButton(tr("cancel"))
        button_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._ok_btn.clicked.connect(self._on_ok)
        self._cancel_btn.clicked.connect(self.reject)
    
    def _on_ok(self):
        """Handle OK button click."""
        selected_mode = self.get_selected_mode()
        self.mode_selected.emit(selected_mode)
        self.accept()
    
    def get_selected_mode(self) -> str:
        """Get the currently selected mode."""
        if self._translate_radio.isChecked():
            return "translate"
        return "direct"
