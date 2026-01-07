# -*- coding: utf-8 -*-
"""
RenForge API Key Dialog View

Pure view component for API key configuration.
"""

from typing import Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QDialogButtonBox)
from PyQt6.QtCore import pyqtSignal, Qt

from locales import tr
from renforge_logger import get_logger

logger = get_logger("views.dialogs.api_key")


class ApiKeyDialogView(QDialog):
    """
    Dialog for API key input - pure View component.
    
    Signals:
        save_requested(str): Emitted with new API key when save is clicked
        delete_requested: Emitted when delete button is clicked
    """
    
    save_requested = pyqtSignal(str)
    delete_requested = pyqtSignal()
    
    def __init__(self, parent=None, current_key: Optional[str] = None):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent widget
            current_key: Current API key (masked) for display
        """
        super().__init__(parent)
        self._current_key = current_key
        self._key_visible = False
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("ApiKeyDialogView created")
    
    def _setup_ui(self):
        """Build the UI."""
        self.setWindowTitle(tr("dialog_api_key"))
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(tr("api_key_info"))
        info_label.setWordWrap(True)
        info_label.setOpenExternalLinks(True)
        layout.addWidget(info_label)
        
        # Current key display
        if self._current_key:
            current_label = QLabel(tr("api_key_current", key=self._mask_key(self._current_key)))
        else:
            current_label = QLabel(tr("api_key_not_saved"))
        layout.addWidget(current_label)
        
        # New key input
        layout.addWidget(QLabel(tr("api_key_new")))
        
        input_layout = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText(tr("api_key_placeholder"))
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        input_layout.addWidget(self._key_input)
        
        self._toggle_btn = QPushButton(tr("btn_show_key"))
        self._toggle_btn.setFixedWidth(100)
        input_layout.addWidget(self._toggle_btn)
        
        layout.addLayout(input_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if self._current_key:
            self._delete_btn = QPushButton(tr("delete"))
            button_layout.addWidget(self._delete_btn)
        else:
            self._delete_btn = None
        
        button_layout.addStretch()
        
        self._save_btn = QPushButton(tr("btn_save_close"))
        self._save_btn.setDefault(True)
        button_layout.addWidget(self._save_btn)
        
        self._cancel_btn = QPushButton(tr("cancel"))
        button_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self._toggle_btn.clicked.connect(self._toggle_key_visibility)
        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)
        
        if self._delete_btn:
            self._delete_btn.clicked.connect(self._on_delete)
    
    def _toggle_key_visibility(self):
        """Toggle password visibility."""
        self._key_visible = not self._key_visible
        if self._key_visible:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_btn.setText(tr("btn_hide_key"))
        else:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_btn.setText(tr("btn_show_key"))
    
    def _on_save(self):
        """Handle save button click."""
        key = self._key_input.text().strip()
        self.save_requested.emit(key)
        self.accept()
    
    def _on_delete(self):
        """Handle delete button click."""
        self.delete_requested.emit()
        self.accept()
    
    def _mask_key(self, key: str) -> str:
        """Mask API key for display."""
        if not key or len(key) < 8:
            return "****"
        return key[:4] + "..." + key[-4:]
    
    def get_entered_key(self) -> str:
        """Get the entered API key."""
        return self._key_input.text().strip()
