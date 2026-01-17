# -*- coding: utf-8 -*-
"""
RenForge Coming Soon Page

Reusable placeholder page for features under development.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PushButton, CardWidget,
    FluentIcon as FIF, PrimaryPushButton
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.coming_soon")


class ComingSoonPage(QWidget):
    """
    A reusable placeholder page for features not yet implemented.
    
    Shows:
    - Title
    - Description
    - Feature bullet list
    - Optional disabled buttons
    """
    
    def __init__(
        self, 
        title: str, 
        description: str, 
        features: list = None,
        buttons: list = None,
        icon: str = "🚧",
        parent=None
    ):
        """
        Create a coming soon page.
        
        Args:
            title: Page title
            description: Short description
            features: List of feature bullet strings
            buttons: List of (label, icon) tuples for disabled buttons
            icon: Emoji or text icon
            parent: Parent widget
        """
        super().__init__(parent)
        self.setObjectName("ComingSoonPage")
        
        self._title = title
        self._description = description
        self._features = features or []
        self._buttons = buttons or []
        self._icon = icon
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QHBoxLayout()
        title = SubtitleLabel(self._title)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        
        # Centered content card
        layout.addStretch(1)
        
        card = CardWidget()
        card.setMaximumWidth(500)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_label = BodyLabel(self._icon)
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)
        
        # Title
        title_label = SubtitleLabel(self._title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_label)
        
        # Description
        desc_label = BodyLabel(self._description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)
        
        # Features list
        if self._features:
            card_layout.addSpacing(16)
            
            features_label = BodyLabel("Planlanan özellikler:")
            features_label.setStyleSheet("font-weight: bold; color: #0078d4;")
            card_layout.addWidget(features_label)
            
            for feature in self._features:
                bullet = BodyLabel(f"• {feature}")
                bullet.setWordWrap(True)
                card_layout.addWidget(bullet)
        
        # Disabled buttons
        if self._buttons:
            card_layout.addSpacing(20)
            
            btn_layout = QHBoxLayout()
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            for i, (label, icon) in enumerate(self._buttons):
                if i == 0:
                    btn = PrimaryPushButton(label)
                else:
                    btn = PushButton(label)
                
                if icon:
                    btn.setIcon(icon)
                btn.setEnabled(False)
                btn_layout.addWidget(btn)
            
            card_layout.addLayout(btn_layout)
        
        # Coming soon badge
        card_layout.addSpacing(20)
        coming_soon = BodyLabel("🚀 Yakında!")
        coming_soon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        coming_soon.setStyleSheet("color: #888888; font-style: italic;")
        card_layout.addWidget(coming_soon)
        
        # Center the card
        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(card)
        center_layout.addStretch()
        layout.addLayout(center_layout)
        
        layout.addStretch(2)
